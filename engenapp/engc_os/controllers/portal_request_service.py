# -*- coding: utf-8 -*-
"""
Controller do portal para Solicitações de Serviço (engc.request.service).
Permite ao usuário logado criar e listar suas solicitações em /my/request-services.
"""
import json
import logging
from datetime import datetime

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

_logger = logging.getLogger(__name__)


class PortalRequestService(CustomerPortal):
    """Portal: listar e criar Solicitações de Serviço."""

    def _prepare_home_portal_values(self, counters):
        """Inclui o contador de solicitações na home do portal (/my)."""
        values = super()._prepare_home_portal_values(counters)
        if "request_service_count" in counters:
            RequestService = request.env["engc.request.service"]
            if RequestService.check_access_rights("read", raise_exception=False):
                domain = [("requester", "=", request.env.user.name)]
                values["request_service_count"] = RequestService.search_count(domain)
            else:
                values["request_service_count"] = 0
        return values

    def _get_equipments_for_portal(self, company_id, employee=None, department_id=None):
        """
        Retorna equipamentos disponíveis para o formulário do portal, conforme
        o escopo configurado no funcionário (Solicitar Serviço):
        - selection: apenas os equipamentos da lista request_service_equipment_ids
        - department: equipamentos do departamento (e subdepartamentos) do funcionário
        - all: todos os equipamentos da empresa
        Se employee não existir, usa company_id e opcionalmente department_id.
        """
        Equipment = request.env["engc.equipment"].sudo()
        if employee and employee.request_service_scope == "selection":
            return employee.request_service_equipment_ids.mapped("equipment_id").sorted("name")
        domain = [("company_id", "=", company_id)]
        if employee and employee.request_service_scope == "department" and employee.department_id:
            dept = employee.department_id
            child_ids = dept.get_children_department_ids().ids
            dept_ids = [dept.id] + child_ids
            domain.append(("department", "in", [False] + dept_ids))
        elif department_id and (not employee or employee.request_service_scope != "all"):
            dept = request.env["hr.department"].sudo().browse(department_id)
            if dept.exists():
                child_ids = dept.get_children_department_ids().ids
                dept_ids = [department_id] + child_ids
                domain.append(("department", "in", [False] + dept_ids))
        return Equipment.search(domain, order="name")

    @http.route(
        ["/my/request-services", "/my/request-services/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_request_services(
        self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw
    ):
        """Lista as solicitações de serviço do usuário (requester = nome do usuário)."""
        RequestService = request.env["engc.request.service"]
        if not RequestService.check_access_rights("read", raise_exception=False):
            return request.redirect("/my")

        values = self._prepare_portal_layout_values()
        domain = [("requester", "=", request.env.user.name)]

        searchbar_filters = {
            "all": {"label": _("Todas"), "domain": []},
            "new": {"label": _("Nova"), "domain": [("state", "=", "new")]},
            "in_progress": {"label": _("Em andamento"), "domain": [("state", "=", "in_progress")]},
            "done": {"label": _("Concluído"), "domain": [("state", "=", "done")]},
            "cancel": {"label": _("Cancelada"), "domain": [("state", "=", "cancel")]},
        }
        searchbar_sortings = {
            "date": {"label": _("Data"), "order": "request_date desc"},
            "name": {"label": _("Código"), "order": "name desc"},
        }

        if not sortby:
            sortby = "date"
        if not filterby:
            filterby = "all"
        domain += searchbar_filters.get(filterby, searchbar_filters["all"])["domain"]
        order = searchbar_sortings.get(sortby, searchbar_sortings["date"])["order"]

        if date_begin and date_end:
            domain += [
                ("request_date", ">=", date_begin),
                ("request_date", "<=", date_end),
            ]

        total = RequestService.search_count(domain)
        pager = portal_pager(
            url="/my/request-services",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby, "filterby": filterby},
            total=total,
            page=page,
            step=self._items_per_page,
        )
        requests = RequestService.search(domain, order=order, limit=self._items_per_page, offset=pager["offset"])

        values.update(
            {
                "date_begin": date_begin,
                "date_end": date_end,
                "sortby": sortby,
                "filterby": filterby,
                "page_name": "request_service",
                "pager": pager,
                "request_services": requests,
                "searchbar_filters": searchbar_filters,
                "searchbar_sortings": searchbar_sortings,
                "default_url": "/my/request-services",
            }
        )
        return request.render("engc_os.portal_my_request_services", values)

    def _check_requester_can_request(self):
        """
        Verifica se o usuário logado (requisitante) pode realizar uma solicitação de serviço.
        Retorna (True, None) se permitido, ou (False, reason_code) se não permitido.
        reason_code: 'no_employee' = usuário não vinculado a funcionário; 'no_equipment' = sem equipamentos no escopo.
        """
        employee = request.env["hr.employee"].sudo().search(
            [("user_id", "=", request.env.user.id)], limit=1
        )
        if not employee:
            return False, "no_employee"
        company = request.env.company
        department_id = employee.department_id.id if employee.department_id else None
        equipments = self._get_equipments_for_portal(
            company.id, employee=employee, department_id=department_id
        )
        if not equipments:
            return False, "no_equipment"
        return True, None

    def _get_requested_equipment_ids_from_url(self):
        """
        Lê equipment_id ou equipment_ids da query string e retorna lista de IDs (int)
        solicitados na URL, sem validar permissão.
        """
        ids = []
        args = request.httprequest.args
        if args.get("equipment_id"):
            try:
                ids.append(int(args.get("equipment_id")))
            except (TypeError, ValueError):
                pass
        for raw in args.getlist("equipment_ids"):
            for part in str(raw).split(","):
                try:
                    ids.append(int(part.strip()))
                except (TypeError, ValueError):
                    pass
        seen = set()
        return [x for x in ids if not (x in seen or seen.add(x))]

    def _get_preselected_equipment_ids_from_request(self, equipments):
        """
        Lê equipment_id ou equipment_ids da query string e retorna lista de
        {id, name} apenas para equipamentos permitidos (presentes em equipments).
        Permite link direto para nova solicitação com equipamento já selecionado.
        """
        allowed = {e.id: e for e in equipments}
        ids = self._get_requested_equipment_ids_from_url()
        seen = set()
        preselected = []
        for eid in ids:
            if eid not in seen and eid in allowed:
                seen.add(eid)
                preselected.append({"id": allowed[eid].id, "name": allowed[eid].display_name})
        return preselected

    @http.route("/my/request-service/not-allowed", type="http", auth="user", website=True)
    def portal_request_service_not_allowed(self, reason=None, **kw):
        """Página exibida quando o requisitante não pode realizar solicitação de serviço."""
        reasons = {
            "no_employee": {
                "title": _("Solicitação não disponível"),
                "message": _(
                    "Apenas funcionários podem realizar solicitações de serviço pelo portal. "
                    "Seu usuário não está vinculado a um cadastro de Funcionário. "
                    "Entre em contato com o administrador ou com o setor de RH para associar seu usuário a um funcionário."
                ),
            },
            "no_equipment": {
                "title": _("Nenhum equipamento disponível"),
                "message": _(
                    "Não há equipamentos disponíveis para você solicitar no momento. "
                    "Isso pode ocorrer se seu cadastro de Funcionário estiver com a opção "
                    "\"Solicitar Serviço\" em \"Seleção\" e nenhum equipamento tiver sido configurado, "
                    "ou se não houver equipamentos no seu departamento/empresa. "
                    "Entre em contato com o administrador ou com o setor de RH para ajustar o cadastro."
                ),
            },
            "equipment_not_allowed": {
                "title": _("Equipamento não permitido"),
                "message": _(
                    "Você não tem permissão para solicitar serviço para o(s) equipamento(s) indicado(s) no link. "
                    "Cada funcionário só pode solicitar equipamentos do seu departamento, da lista de seleção "
                    "configurada no seu cadastro, ou todos da empresa, conforme a opção \"Solicitar Serviço\". "
                    "Se o link veio de outra área, use o formulário de nova solicitação e escolha um equipamento disponível para você."
                ),
            },
        }
        info = reasons.get(reason) or reasons.get("no_employee")
        values = {
            "page_name": "request_service_not_allowed",
            "reason": reason,
            "title": info["title"],
            "message": info["message"],
        }
        return request.render("engc_os.portal_request_service_not_allowed", values)

    # Este método exibe o formulário de criação de uma nova Solicitação de Serviço pelo portal.
    # 
    # Como funciona:
    # - Ele é acessado pela rota "/my/request-service/new" e exige que o usuário esteja autenticado no portal.
    # - Primeiro, verifica se o usuário possui permissão para criar solicitações.
    # - Em seguida, checa se o requisitante pode de fato realizar solicitações (por exemplo, se está vinculado a um funcionário).
    # - Recupera a empresa atual e o funcionário correspondente ao usuário do portal, além do departamento, se existir.
    # - Busca os equipamentos disponíveis para aquele funcionário (considerando permissões).
    # - Monta listas possíveis para tipos de manutenção e prioridades para serem usadas nos campos do formulário.
    # - Prepara os dados de equipamentos em formato JSON para uso em widgets dinâmicos do formulário.
    # - Preenche um dicionário (`values`) com os dados que serão enviados para o template do formulário (renderização).
    # - Por fim, renderiza o template "engc_os.portal_create_request_service" passando os valores necessários.
    @http.route("/my/request-service/new", type="http", auth="user", website=True)
    def portal_new_request_service(self, **kw):
        RequestService = request.env["engc.request.service"]
        if not RequestService.check_access_rights("create", raise_exception=False):
            return request.redirect("/my")

        can_request, reason = self._check_requester_can_request()
        if not can_request:
            return self.portal_request_service_not_allowed(reason=reason or "no_employee")

        company = request.env.company
        employee = request.env["hr.employee"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)
        department_id = employee.department_id.id if employee and employee.department_id else None
        equipments = self._get_equipments_for_portal(company.id, employee=employee, department_id=department_id)

        # Se a URL pediu equipamento(s) específico(s), todos devem estar na lista permitida
        requested_ids = self._get_requested_equipment_ids_from_url()
        if requested_ids:
            allowed_ids = {e.id for e in equipments}
            if not all(eid in allowed_ids for eid in requested_ids):
                return self.portal_request_service_not_allowed(reason="equipment_not_allowed")

        # JSON para o widget de busca de equipamentos (lista + badges) no portal
        equipments_data = [{"id": e.id, "name": e.display_name} for e in equipments]
        preselected_equipment_ids = self._get_preselected_equipment_ids_from_request(equipments)
        values = {
            "page_name": "request_service_new",
            "requester": request.env.user.name,
            "equipments": equipments,
            "equipments_data_json": json.dumps(equipments_data, ensure_ascii=False),
            "preselected_equipment_ids_json": json.dumps(preselected_equipment_ids, ensure_ascii=False),
            "company": company,
        }
        return request.render("engc_os.portal_create_request_service", values)

    @http.route("/my/request-service/submit", type="http", auth="user", website=True, csrf=True)
    def portal_submit_request_service(self, **post):
        """Cria uma nova Solicitação de Serviço a partir do formulário do portal."""
        RequestService = request.env["engc.request.service"]
        if not RequestService.check_access_rights("create", raise_exception=False):
            return request.redirect("/my")
        can_request, reason = self._check_requester_can_request()
        if not can_request:
            return self.portal_request_service_not_allowed(reason=reason or "no_employee")

        requester = (post.get("requester") or "").strip() or request.env.user.name
        # Resumo a partir das duas perguntas (equipamento em funcionamento? / perigo aos colaboradores?)
        equipment_working = post.get("equipment_working") == "sim"
        defect_danger = post.get("defect_danger") == "sim"
        summary_map = {
            (True, True): "Equipamento em funcionamento mas com problemas, com perigo aos colaboradores.",
            (False, True): "Equipamento parado, com perigo aos colaboradores.",
            (False, False): "Equipamento parado",
            (True, False): "Equipamento em funcionamento mas com problemas"
        }
        summary = summary_map.get((equipment_working, defect_danger))
        desc_text = (post.get("description") or "").strip()
        description = "%s\n\n%s" % (summary, desc_text) if desc_text else summary
        # Form POST: múltiplos equipment_ids vêm do form; request.params é dict, usar form.getlist
        form = getattr(request.httprequest, "form", None) or post
        if hasattr(form, "getlist"):
            equipment_ids = form.getlist("equipment_ids")
        else:
            val = post.get("equipment_ids")
            equipment_ids = val if isinstance(val, list) else ([val] if val else [])

        if not desc_text:
            return request.redirect("/my/request-service/new?error=description")

        company = request.env.company
        equipment_ids = [int(eid) for eid in equipment_ids if eid and str(eid).isdigit()]
        if not equipment_ids:
            return request.redirect("/my/request-service/new?error=equipment")

        # Validar equipamentos (company e, se aplicável, departamento)
        Equipment = request.env["engc.equipment"].sudo()
        valid_equipments = Equipment.search([("id", "in", equipment_ids), ("company_id", "=", company.id)])
        if len(valid_equipments) != len(equipment_ids):
            return request.redirect("/my/request-service/new?error=equipment")

        vals = {
            "company_id": company.id,
            "requester": requester,
            "description": description,
            "maintenance_type": "corrective",
            "priority": "2",
            "equipment_ids": [(6, 0, equipment_ids)],
        }
        # Departamento: preencher se o usuário tiver vínculo com hr.employee
        employee = request.env["hr.employee"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)
        if employee and employee.department_id:
            vals["department"] = employee.department_id.id

        try:
            new_request = RequestService.sudo().create(vals)
            _logger.info(
                "Portal: Solicitação de Serviço criada id=%s name=%s por user_id=%s",
                new_request.id,
                new_request.name,
                request.env.user.id,
            )
        except Exception as e:
            _logger.exception("Portal: falha ao criar Solicitação de Serviço: %s", e)
            return request.redirect("/my/request-service/new?error=create")
        return request.redirect("/my/request-service/success/%s" % new_request.id)

    @http.route("/my/request-service/success/<int:request_service_id>", type="http", auth="user", website=True)
    def portal_request_service_success(self, request_service_id, **kw):
        """Exibe a página de confirmação após abrir uma solicitação (código e equipamento(s))."""
        RequestService = request.env["engc.request.service"]
        try:
            record = RequestService.browse(request_service_id)
            if not record.exists():
                return request.redirect("/my/request-services")
            if record.requester != request.env.user.name:
                return request.redirect("/my/request-services")
            record.check_access_rights("read")
            record.check_access_rule("read")
        except AccessError:
            return request.redirect("/my/request-services")

        values = {
            "page_name": "request_service_success",
            "request_service": record.sudo(),
        }
        return request.render("engc_os.portal_request_service_success", values)

    @http.route("/my/request-service/<int:request_service_id>", type="http", auth="user", website=True)
    def portal_request_service_detail(self, request_service_id, **kw):
        """Exibe o detalhe de uma Solicitação de Serviço (somente se for do usuário)."""
        RequestService = request.env["engc.request.service"]
        try:
            record = RequestService.browse(request_service_id)
            if not record.exists():
                return request.redirect("/my/request-services")
            if record.requester != request.env.user.name:
                return request.redirect("/my/request-services")
            record.check_access_rights("read")
            record.check_access_rule("read")
        except AccessError:
            return request.redirect("/my/request-services")

        values = {
            "page_name": "request_service_detail",
            "request_service": record.sudo(),
        }
        return request.render("engc_os.portal_request_service_detail", values)
