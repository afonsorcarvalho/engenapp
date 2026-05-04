"""Wizard para seleção de materiais para impressão do laudo e assinatura."""
import base64
import re
import logging
from markupsafe import Markup
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class WizardPrintLaudo(models.TransientModel):
    """Wizard para selecionar materiais e assinatura do laudo."""

    _name = 'wizard.print.laudo'
    _description = 'Wizard de Impressão do Laudo de Liberação'

    # --- Ciclo e materiais ---
    ciclo_id = fields.Many2one(
        'afr.supervisorio.ciclos',
        string='Ciclo',
        required=True,
        readonly=True,
    )
    material_line_ids = fields.Many2many(
        'afr.supervisorio.cycle.materials.lines',
        string='Materiais do Ciclo',
        domain="[('ciclo_id','=',ciclo_id)]",
        help='Selecione os materiais que deseja incluir no laudo',
    )
    material_count = fields.Integer(
        string='Materiais Selecionados',
        compute='_compute_material_count',
    )

    # --- Assinatura ---
    signature_type = fields.Selection(
        [
            ('auto', 'Automática (padrão da empresa)'),
            ('upload', 'Enviar imagem (PNG)'),
            ('draw', 'Assinar digitalmente (desenho)'),
        ],
        string='Tipo de assinatura',
        default='auto',
        required=True,
        help='Automática: usa a assinatura configurada na empresa. '
             'Enviar imagem: faça upload de um PNG. '
             'Assinar digitalmente: use o quadro de assinatura e depois envie a imagem.',
    )
    signature_image = fields.Binary(
        string='Imagem da assinatura',
        attachment=False,
        help='PNG da assinatura (upload ou gerado pelo quadro de assinatura).',
    )
    signer_name = fields.Char(
        string='Nome de quem assina',
        help='Nome do responsável pela garantia de qualidade (exibido no laudo).',
    )
    signer_title = fields.Char(
        string='Cargo / Função',
        default='Garantia de qualidade',
        help='Cargo ou função exibido no laudo (ex.: Garantia de qualidade, Responsável técnico).',
    )
    signature_date = fields.Date(
        string='Data da assinatura',
        default=fields.Date.context_today,
        required=True,
    )
    data_liberacao = fields.Date(
        string='Data de liberação',
        required=True,
        help='Data de liberação impressa no laudo. Default: data da assinatura do responsável pelo ciclo.',
    )
    data_emissao = fields.Date(
        string='Data de emissão do laudo',
        default=fields.Date.context_today,
        required=True,
        help='Data de emissão impressa no laudo.',
    )

    # --- Envio por email ---
    send_email_fabricante = fields.Boolean(
        string='Enviar email ao Fabricante',
        default=False,
        help='Se marcado e o ciclo estiver assinado, envia o laudo ao email do fabricante principal dos materiais.',
    )
    email_avulsos = fields.Char(
        string='Outros emails',
        help='Emails adicionais separados por vírgula. Ex.: fulano@empresa.com, ciclano@lab.com',
    )

    # --- Campos computados de suporte (uso na view e lógica) ---
    ciclo_is_signed = fields.Boolean(
        related='ciclo_id.is_signed',
        string='Ciclo Assinado',
        readonly=True,
    )
    fabricante_id = fields.Many2one(
        'res.partner',
        string='Fabricante principal',
        compute='_compute_fabricante_info',
        store=False,
    )
    has_multiple_fabricantes = fields.Boolean(
        string='Múltiplos fabricantes',
        compute='_compute_fabricante_info',
        store=False,
    )

    # --- Computes ---

    @api.depends('material_line_ids')
    def _compute_material_count(self):
        for wizard in self:
            wizard.material_count = len(wizard.material_line_ids)

    @api.depends('material_line_ids', 'material_line_ids.fabricante_id')
    def _compute_fabricante_info(self):
        for wizard in self:
            lines_with_fab = wizard.material_line_ids.filtered('fabricante_id')
            if not lines_with_fab:
                wizard.fabricante_id = False
                wizard.has_multiple_fabricantes = False
            else:
                unique_fabs = lines_with_fab.mapped('fabricante_id')
                wizard.fabricante_id = unique_fabs[0]
                wizard.has_multiple_fabricantes = len(unique_fabs) > 1

    # --- Defaults ---

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ciclo_id = self.env.context.get('active_id')
        if ciclo_id:
            res['ciclo_id'] = ciclo_id
            if 'data_liberacao' in fields_list and not res.get('data_liberacao'):
                ciclo = self.env['afr.supervisorio.ciclos'].browse(ciclo_id)
                sig_date = ciclo.signature_date
                if sig_date:
                    res['data_liberacao'] = fields.Date.to_date(sig_date)
                else:
                    res['data_liberacao'] = fields.Date.context_today(self)
        company = self.env.company
        if company:
            if 'signer_name' in fields_list and not res.get('signer_name'):
                res['signer_name'] = company.laudo_signer_name_default or ''
            if 'signer_title' in fields_list and not res.get('signer_title'):
                res['signer_title'] = company.laudo_signer_title_default or 'Garantia de qualidade'
        return res

    # --- Helpers ---

    def _build_email_context(self, recipients):
        """
        Prepara variáveis para o mail.template QWeb do Odoo 16.
        body_html usa render_engine='qweb': usa t-out, t-if, t-foreach.
        Logo (data URI) é pré-renderizado aqui e passado como Markup.
        """
        self.ensure_one()
        fmt = lambda d: d.strftime('%d/%m/%Y') if d else '—'
        ciclo = self.ciclo_id
        company = self.env.company

        # Logo como data URI — Markup para t-out não escapar
        logo_html = Markup('')
        if company.logo:
            b64 = company.logo.decode() if isinstance(company.logo, bytes) else company.logo
            logo_html = Markup(
                '<img src="data:image/png;base64,{b64}" alt="{name}" '
                'style="max-height:55px; max-width:180px; display:block;"/>'
            ).format(b64=b64, name=Markup.escape(company.name or ''))

        # Rodapé da empresa — Markup para preservar &nbsp;
        company_footer = Markup(' &nbsp;|&nbsp; ').join(
            Markup.escape(v) for v in filter(None, [
                company.name, company.street, company.city,
                company.phone, company.email,
            ])
        )

        return {
            'logo_html': logo_html,
            'material_lines': self.material_line_ids,
            'recipients': recipients,
            'data_lib': fmt(self.data_liberacao),
            'data_emi': fmt(self.data_emissao),
            'equip': ciclo.equipment_nickname or (ciclo.equipment_id.name if ciclo.equipment_id else '—'),
            'batch': ciclo.batch_number or '—',
            'company_footer': company_footer,
        }

    def _render_email_body(self, recipients):
        """Renderiza body_html do mail.template com contexto pré-calculado."""
        self.ensure_one()
        template = self.env.ref(
            'afr_supervisorio_ciclos_extras.mail_template_laudo_liberacao'
        )
        ctx = self._build_email_context(recipients)
        rendered = template._render_field(
            'body_html',
            [self.ciclo_id.id],
            add_context=ctx,
        )
        return rendered[self.ciclo_id.id]

    def _render_email_subject(self):
        """Renderiza assunto do mail.template."""
        self.ensure_one()
        template = self.env.ref(
            'afr_supervisorio_ciclos_extras.mail_template_laudo_liberacao'
        )
        rendered = template._render_field('subject', [self.ciclo_id.id])
        return rendered[self.ciclo_id.id]

    def _get_signature_data_for_report(self):
        """Monta dict de dados de assinatura para passar ao relatório."""
        self.ensure_one()
        signer_name = (self.signer_name or '').strip()
        signer_title = (self.signer_title or 'Garantia de qualidade').strip()
        signature_date = self.signature_date

        signature_image_b64 = None
        if self.signature_type == 'auto':
            img = self.env.company.laudo_signature_default
            if img:
                signature_image_b64 = base64.b64encode(img).decode('utf-8') if isinstance(img, bytes) else img
            if not signer_name and self.env.company.laudo_signer_name_default:
                signer_name = (self.env.company.laudo_signer_name_default or '').strip()
            if not signer_title and self.env.company.laudo_signer_title_default:
                signer_title = (self.env.company.laudo_signer_title_default or 'Garantia de qualidade').strip()
        elif self.signature_image:
            img = self.signature_image
            signature_image_b64 = base64.b64encode(img).decode('utf-8') if isinstance(img, bytes) else img

        return {
            'signature_type': self.signature_type,
            'signature_image_b64': signature_image_b64,
            'signer_name': signer_name,
            'signer_title': signer_title,
            'signature_date': signature_date,
            'data_emissao': self.data_emissao,
            'data_liberacao': self.data_liberacao,
        }

    def _parse_extra_emails(self):
        """Valida e retorna lista de emails de email_avulsos."""
        if not self.email_avulsos:
            return []
        emails = [e.strip() for e in self.email_avulsos.split(',') if e.strip()]
        invalid = [e for e in emails if not _EMAIL_RE.match(e)]
        if invalid:
            raise UserError('Emails inválidos: ' + ', '.join(invalid))
        return emails

    def _collect_recipients(self):
        """
        Monta lista de destinatários para envio do laudo.
        Fabricante: somente se ciclo assinado, checkbox marcado e fabricante único.
        email_avulsos: sempre incluídos (se válidos).
        """
        self.ensure_one()
        recipients = []

        if self.send_email_fabricante and self.ciclo_id.is_signed and not self.has_multiple_fabricantes:
            fab = self.fabricante_id
            if fab and fab.email:
                recipients.append(fab.email)

        for email in self._parse_extra_emails():
            if email not in recipients:
                recipients.append(email)

        return recipients

    # --- Ações ---

    def action_print_laudo(self):
        """Gera o laudo com os materiais selecionados, envia por email se configurado."""
        self.ensure_one()
        if not self.material_line_ids:
            raise UserError('Selecione pelo menos um material para gerar o laudo!')

        material_ids = self.material_line_ids.ids
        report = self.env.ref('afr_supervisorio_ciclos_extras.report_laudo_liberacao_action')
        data = {
            'material_line_ids': material_ids,
            **self._get_signature_data_for_report(),
        }

        recipients = self._collect_recipients()
        if recipients:
            pdf_content, _ = report._render_qweb_pdf(
                'afr_supervisorio_ciclos_extras.report_laudo_liberacao_action',
                self.ciclo_id.ids,
                data=data,
            )
            filename = 'Laudo_Liberacao_{}.pdf'.format(self.ciclo_id.name)

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content).decode(),
                'res_model': self.ciclo_id._name,
                'res_id': self.ciclo_id.id,
                'mimetype': 'application/pdf',
            })

            self.ciclo_id.message_post(
                body=Markup(
                    '<p>Laudo de Liberação enviado por email para: <strong>{}</strong></p>'
                ).format(', '.join(recipients)),
                attachment_ids=[attachment.id],
                subtype_xmlid='mail.mt_comment',
            )

            self.env['mail.mail'].sudo().create({
                'subject': self._render_email_subject(),
                'body_html': self._render_email_body(recipients),
                'email_to': ','.join(recipients),
                'email_from': self.env.company.email or self.env.user.email or '',
                'attachment_ids': [(4, attachment.id)],
            }).send()

        return report.report_action(self.ciclo_id.ids, data=data)
