import json
import logging
import re
import urllib.error
import urllib.request

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CEP_URL = "https://brasilapi.com.br/api/cep/v2/{cep}"
CNPJ_URL = "https://open.cnpja.com/office/{cnpj}"
HTTP_TIMEOUT = 5


def _http_get_json(url):
    """GET JSON. Convert HTTP/transport errors em UserError BR-friendly.
    Wrapper isolado para ser mockável nos testes.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "afr_brasil_lookup/16.0"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UserError(_("Não encontrado na base pública (404).")) from e
        if e.code == 429:
            raise UserError(_("Limite de consultas atingido. Tente novamente em alguns minutos.")) from e
        raise UserError(_("Erro HTTP %s ao consultar serviço externo.") % e.code) from e
    except urllib.error.URLError as e:
        raise UserError(_("Falha de rede ao consultar serviço externo: %s") % e.reason) from e


def _cnpj_check_digits(cnpj14):
    """Valida CNPJ pelos 2 dígitos verificadores. Retorna True/False."""
    if len(cnpj14) != 14 or not cnpj14.isdigit():
        return False
    if cnpj14 == cnpj14[0] * 14:
        return False

    def _calc(digits, weights):
        s = sum(int(d) * w for d, w in zip(digits, weights))
        r = s % 11
        return "0" if r < 2 else str(11 - r)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    d1 = _calc(cnpj14[:12], w1)
    d2 = _calc(cnpj14[:12] + d1, w2)
    return cnpj14[-2:] == d1 + d2


def _format_cep(cep8):
    return "{}-{}".format(cep8[:5], cep8[5:]) if len(cep8) == 8 else cep8


def _format_phone_br(area, number):
    n = re.sub(r"\D", "", number or "")
    if len(n) == 8:
        n = "{}-{}".format(n[:4], n[4:])
    elif len(n) == 9:
        n = "{}-{}".format(n[:5], n[5:])
    if area:
        return "+55 {} {}".format(area, n)
    return n


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ---------- campos NF-e (componentes separados, lossless) ----------
    # Um campo por componente do layout NF-e 4.00 (enderEmit/enderDest).
    # Ver docs/NFE_ADDRESS_READINESS.md. street = xLgr, street2 = xCpl.

    afr_trade_name = fields.Char(
        string="Nome Fantasia",
        size=60,
        help="Nome fantasia / nome de fantasia da empresa (NF-e: xFant). "
        "Preenchido pela consulta de CNPJ (campo alias).",
    )
    afr_street_number = fields.Char(
        string="Número",
        size=60,
        help="Número do endereço (NF-e: nro). Separado do logradouro.",
    )
    afr_district = fields.Char(
        string="Bairro",
        size=60,
        help="Bairro/distrito (NF-e: xBairro). Separado do complemento.",
    )
    afr_ibge_code = fields.Char(
        string="Cód. IBGE Município",
        size=7,
        help="Código IBGE do município com 7 dígitos (NF-e: cMun). "
        "Preenchido pela consulta de CNPJ; a consulta de CEP não retorna.",
    )

    # ---------- helpers ----------

    @staticmethod
    def _brl_clean_digits(value):
        return re.sub(r"\D", "", value or "")

    def _brl_state_id_by_uf(self, uf_code):
        if not uf_code:
            return False
        br = self.env.ref("base.br", raise_if_not_found=False)
        if not br:
            return False
        state = self.env["res.country.state"].search(
            [("country_id", "=", br.id), ("code", "=", uf_code.upper())], limit=1
        )
        return state.id if state else False

    # ---------- CEP ----------

    def action_brl_lookup_cep(self):
        self.ensure_one()
        cep = self._brl_clean_digits(self.zip or self.env.context.get("zip"))
        if len(cep) != 8:
            raise UserError(_("CEP inválido. Deve conter 8 dígitos."))

        data = _http_get_json(CEP_URL.format(cep=cep))

        br = self.env.ref("base.br", raise_if_not_found=False)
        vals = {
            "zip": _format_cep(cep),
            "street": data.get("street") or self.street,
            "city": data.get("city") or self.city,
            "country_id": br.id if br else self.country_id.id,
        }
        # neighborhood (bairro) -> afr_district (campo proprio, NF-e xBairro).
        # A API de CEP nao retorna numero nem codigo IBGE do municipio.
        bairro = data.get("neighborhood")
        if bairro:
            vals["afr_district"] = bairro

        state_id = self._brl_state_id_by_uf(data.get("state"))
        if state_id:
            vals["state_id"] = state_id

        # update() em vez de write(): persiste em registro real (botao) e
        # tambem atualiza o cache em registro virtual de onchange (NewId),
        # onde write() nao reflete no formulario.
        self.update(vals)
        return True

    # ---------- CNPJ ----------

    def action_brl_lookup_cnpj(self):
        self.ensure_one()
        cnpj = self._brl_clean_digits(self.vat)
        if not _cnpj_check_digits(cnpj):
            raise UserError(_("CNPJ inválido. Verifique os dígitos."))

        data = _http_get_json(CNPJ_URL.format(cnpj=cnpj))

        company = data.get("company") or {}
        addr = data.get("address") or {}
        phones = data.get("phones") or []
        emails = data.get("emails") or []

        # Endereço lossless: cada componente NF-e em seu proprio campo.
        # street=xLgr (logradouro puro), afr_street_number=nro,
        # street2=xCpl (complemento), afr_district=xBairro, afr_ibge_code=cMun.
        zip_raw = self._brl_clean_digits(addr.get("zip"))
        zip_final = _format_cep(zip_raw) if zip_raw else False

        br = self.env.ref("base.br", raise_if_not_found=False)
        vals = {
            "is_company": True,
            "name": company.get("name") or self.name,
            "vat": "{}.{}.{}/{}-{}".format(
                cnpj[0:2], cnpj[2:5], cnpj[5:8], cnpj[8:12], cnpj[12:14]
            ),
            "country_id": br.id if br else self.country_id.id,
        }
        if data.get("alias"):
            vals["afr_trade_name"] = data["alias"]
        if addr.get("street"):
            vals["street"] = addr["street"]
        if addr.get("number"):
            vals["afr_street_number"] = str(addr["number"])
        if addr.get("details"):
            vals["street2"] = addr["details"]
        if addr.get("district"):
            vals["afr_district"] = addr["district"]
        if addr.get("city"):
            vals["city"] = addr["city"]
        if addr.get("municipality"):
            vals["afr_ibge_code"] = str(addr["municipality"])
        if zip_final:
            vals["zip"] = zip_final

        state_id = self._brl_state_id_by_uf(addr.get("state"))
        if state_id:
            vals["state_id"] = state_id

        if phones:
            p = phones[0]
            vals["phone"] = _format_phone_br(p.get("area"), p.get("number"))
        if emails:
            vals["email"] = (emails[0].get("address") or "").lower() or False

        # update() em vez de write(): ver nota no action_brl_lookup_cep.
        self.update(vals)
        return True

    # ---------- Onchange (opt-in via ICP) ----------

    def _brl_icp_truthy(self, key):
        v = self.env["ir.config_parameter"].sudo().get_param(key, default="")
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @api.onchange("zip")
    def _onchange_zip_brl(self):
        for rec in self:
            if not rec._brl_icp_truthy("afr_brasil_lookup.auto_fill_cep"):
                continue
            if len(rec._brl_clean_digits(rec.zip)) != 8:
                continue
            try:
                rec.action_brl_lookup_cep()
            except UserError as e:
                _logger.info("CEP auto-fill skipped: %s", e)

    @api.onchange("vat")
    def _onchange_vat_brl(self):
        for rec in self:
            if not rec._brl_icp_truthy("afr_brasil_lookup.auto_fill_cnpj"):
                continue
            cnpj = rec._brl_clean_digits(rec.vat)
            if len(cnpj) != 14 or not _cnpj_check_digits(cnpj):
                continue
            try:
                rec.action_brl_lookup_cnpj()
            except UserError as e:
                _logger.info("CNPJ auto-fill skipped: %s", e)
