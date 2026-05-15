# -*- coding: utf-8 -*-
"""
Sessão de chat com LLM local (LM Studio).

A resposta do modelo pode incluir:

* ``[[ODOO_QUERY]]...[[/ODOO_QUERY]]`` — leitura (``search_read``, contagens, etc.).
* ``[[ODOO_LINK]]...[[/ODOO_LINK]]`` — pedido de URLs relativas (formulário, anexo,
  relatório, menu, ação), resolvidas no servidor com as permissões do usuário.
"""

import ast
import json
import logging
import os
import re
import urllib.error
import urllib.request
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# IPv4 para ODOO_LMSTUDIO_HOST_LAN (evita placeholder tipo 192.168.0.x).
_LAN_IPV4_RE = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)

# Tamanho máximo do texto injetado no system prompt (contexto do LLM). Ajustável por env.
_MODEL_CATALOG_MAX_CHARS = int(os.environ.get('ODOO_LM_CATALOG_MODELS_CHARS', '10000'))
_WHITELIST_FIELDS_MAX_CHARS = int(os.environ.get('ODOO_LM_CATALOG_FIELDS_CHARS', '12000'))
# Catálogo de ir.actions.report (relatórios QWeb) visíveis ao usuário.
_REPORTS_CATALOG_MAX_CHARS = int(os.environ.get('ODOO_LM_CATALOG_REPORTS_CHARS', '12000'))
# Texto de ``fields.Field.help`` (tooltip / documentação do campo no Odoo) por campo no catálogo.
_FIELD_HELP_MAX_CHARS = int(os.environ.get('ODOO_LM_FIELD_HELP_MAX_CHARS', '360'))

# Marcadores na resposta do LLM para solicitar dados ao Odoo.
_ODOO_QUERY_START = '[[ODOO_QUERY]]'
_ODOO_QUERY_END = '[[/ODOO_QUERY]]'

# Tool-calling: iteração máxima do loop assistant↔tool dentro de uma única resposta ao user.
_TOOL_CALLING_MAX_ITER = int(os.environ.get('ODOO_LM_TOOL_CALL_MAX_ITER', '5'))

# Marcadores para URLs relativas (/web#, /web/content/, /report/...).
_ODOO_LINK_START = '[[ODOO_LINK]]'
_ODOO_LINK_END = '[[/ODOO_LINK]]'

# Nome técnico de relatório QWeb (módulo.nome_xml).
_REPORT_TECHNICAL_NAME_RE = re.compile(
    r'^[a-z][a-z0-9_]*\.[a-zA-Z][a-zA-Z0-9_.]+$'
)

# Operadores de domínio considerados seguros para uso via assistente.
_SAFE_DOMAIN_OPS = frozenset({
    '=', '!=', '?=', '=like', '=ilike', 'like', 'not like', 'ilike', 'not ilike',
    'in', 'not in', '>', '<', '>=', '<=', 'child_of', 'parent_of',
})

# Agregações permitidas em read_group (suffixo campo:agregação).
_SAFE_READ_GROUP_AGG = frozenset({'sum', 'avg', 'min', 'max', 'count'})

# Atributos permitidos em fields_get (evita payload excessivo / ruído).
_SAFE_FIELDS_GET_ATTRS = frozenset({
    'string', 'type', 'required', 'readonly', 'selection', 'relation', 'help',
})


class AfrLlmChatSession(models.Model):
    _name = 'afr.llm.chat.session'
    _description = 'Sessão de chat com assistente LLM'
    _order = 'write_date desc'

    name = fields.Char(string='Título', default='Assistente')
    user_id = fields.Many2one(
        'res.users',
        string='Usuário',
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
    )
    message_ids = fields.One2many(
        'afr.llm.chat.message',
        'session_id',
        string='Mensagens',
    )
    active = fields.Boolean(default=True)

    # -------------------------------------------------------------------------
    # API pública (chamada pelo JS e por automações)
    # -------------------------------------------------------------------------

    @api.model
    def get_or_create_my_session(self):
        """Retorna o id da sessão mais recente do usuário ou cria uma nova."""
        self.env['afr.llm.chat.session'].check_access_rights('read')
        self.env['afr.llm.chat.session'].check_access_rights('create')
        session = self.search(
            [('user_id', '=', self.env.uid), ('active', '=', True)],
            order='write_date desc',
            limit=1,
        )
        if not session:
            session = self.create({'name': _('Assistente LLM')})
        return session.id

    def _append_user_message(self, text):
        """Grava mensagem do usuário (texto já validado)."""
        self.ensure_one()
        self.env['afr.llm.chat.message'].create({
            'session_id': self.id,
            'role': 'user',
            'body': text,
        })

    def action_send_message(self, text):
        """
        Registra a mensagem do usuário, chama o LM Studio e grava a resposta (um único RPC longo).

        :param str text: texto enviado pelo usuário
        :returns: conteúdo textual da resposta do assistente
        """
        self.ensure_one()
        if self.user_id.id != self.env.user.id:
            raise AccessError(_('Esta sessão de chat pertence a outro usuário.'))
        stripped = (text or '').strip()
        if not stripped:
            raise UserError(_('Digite uma mensagem antes de enviar.'))
        self._append_user_message(stripped)
        final_text = self._compose_llm_response_text()
        self.env['afr.llm.chat.message'].create({
            'session_id': self.id,
            'role': 'assistant',
            'body': final_text,
        })
        return final_text

    def action_queue_message(self, text):
        """
        Grava a mensagem do usuário e cria um job pendente. O cliente deve chamar
        ``afr.llm.chat.job`` / ``action_process`` (recomenda-se ``orm.silent`` no RPC longo).
        """
        self.ensure_one()
        if self.user_id.id != self.env.user.id:
            raise AccessError(_('Esta sessão de chat pertence a outro usuário.'))
        stripped = (text or '').strip()
        if not stripped:
            raise UserError(_('Digite uma mensagem antes de enviar.'))
        self._append_user_message(stripped)
        Job = self.env['afr.llm.chat.job']
        Job.search([
            ('session_id', '=', self.id),
            ('state', 'in', ('pending', 'processing')),
        ]).unlink()
        job = Job.create({'session_id': self.id, 'state': 'pending'})
        return {'job_id': job.id}

    def _compose_llm_response_text(self):
        """
        Executa provedor LLM (LM Studio OpenAI-compat ou Anthropic Claude) + ODOO_QUERY
        até o texto final (sem gravar mensagem do assistente).
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        provider = (icp.get_param('afr_llm_assistant.provider') or 'lmstudio').strip().lower()
        # Ordem: ODOO_LMSTUDIO_API_BASE (várias URLs separadas por vírgula), ICP, ou padrões bridge/host.
        api_bases = self._iter_lmstudio_api_bases(icp)
        model_name = (icp.get_param('afr_llm_assistant.model') or '').strip()
        if not model_name:
            model_name = 'claude-sonnet-4-6' if provider == 'anthropic' else 'google/gemma-4-e4b'
        api_key = (icp.get_param('afr_llm_assistant.api_key') or '').strip()
        anth_cfg = self._anthropic_config(icp) if provider == 'anthropic' else None

        # Dispatcher: tool-calling estruturado (Ollama/OpenAI-compat) vs fluxo legacy ODOO_QUERY/ODOO_LINK.
        # Habilita por ICP `afr_llm_assistant.use_tool_calling` (qualquer truthy: 1/true/on/yes).
        use_tools_raw = (icp.get_param('afr_llm_assistant.use_tool_calling') or '').strip().lower()
        if provider == 'lmstudio' and use_tools_raw in ('1', 'true', 'on', 'yes'):
            return self._compose_via_tool_calling(api_bases, model_name, api_key)

        messages = self._build_openai_messages()
        first, api_used = self._llm_chat(
            provider, api_bases, model_name, api_key, messages, anth_cfg,
        )
        final_text = first

        block = self._extract_odoo_query_block(first)
        if block is not None:
            assistant_so_far = first
            attempt = 0
            try:
                while attempt < 3:
                    inner = self._extract_odoo_query_block(assistant_so_far)
                    if not inner:
                        raise UserError(_('Resposta do modelo sem bloco ODOO_QUERY válido.'))
                    try:
                        payload = json.loads(inner)
                    except json.JSONDecodeError as err:
                        raise UserError(_('JSON inválido no bloco ODOO_QUERY: %s') % err) from err
                    try:
                        rows = self._safe_execute_odoo_operation(payload)
                    except UserError as err:
                        if attempt >= 2:
                            raise
                        repair = (
                            messages
                            + [{'role': 'assistant', 'content': assistant_so_far}]
                            + [{'role': 'user', 'content': _(
                                'A consulta ODOO_QUERY falhou no servidor Odoo:\n%(msg)s\n\n'
                                'Corrija usando **apenas** nomes de campos que aparecem na secção '
                                '### do modelo no prompt de sistema (copie literalmente; não invente '
                                'nomes nem reutilize campos de outros modelos). Reenvie um bloco '
                                '[[ODOO_QUERY]]...[[/ODOO_QUERY]] corrigido ou responda sem dados.'
                            ) % {'msg': err.args[0]}}]
                        )
                        assistant_so_far, api_used = self._llm_chat(
                            provider, [api_used], model_name, api_key, repair, anth_cfg,
                        )
                        attempt += 1
                        if not self._extract_odoo_query_block(assistant_so_far):
                            final_text = assistant_so_far
                            break
                        continue

                    data_json = self._llm_build_followup_query_json(payload, rows)
                    followup = (
                        messages
                        + [{'role': 'assistant', 'content': assistant_so_far}]
                        + [{'role': 'user', 'content': _(
                            'Segue o resultado da consulta ao Odoo (respeite as permissões '
                            'do usuário). Responda de forma objetiva em português, com base '
                            'apenas nestes dados. Se existir a chave _record_form_links, siga '
                            'a "instruction" para listar cada registo com link clicável no formato '
                            'Markdown indicado.\n%s'
                        ) % data_json}]
                    )
                    final_text, _api2 = self._llm_chat(
                        provider, [api_used], model_name, api_key, followup, anth_cfg,
                    )
                    break
            except Exception as err:
                if isinstance(err, UserError):
                    raise
                _logger.exception('Falha ao processar ODOO_QUERY')
                raise UserError(
                    _('Não foi possível executar a consulta sugerida pelo modelo: %s') % err
                ) from err

        # --- ODOO_LINK: caminhos relativos clicáveis (/web#, /web/content/, /report/...) ---
        link_block = self._extract_odoo_link_block(final_text)
        if link_block is not None:
            assistant_links = final_text
            attempt_l = 0
            try:
                while attempt_l < 3:
                    inner_l = self._extract_odoo_link_block(assistant_links)
                    if not inner_l:
                        raise UserError(_('Resposta do modelo sem bloco ODOO_LINK válido.'))
                    try:
                        link_payload = json.loads(inner_l)
                    except json.JSONDecodeError as err:
                        raise UserError(_('JSON inválido no bloco ODOO_LINK: %s') % err) from err
                    try:
                        resolved_links = self._safe_resolve_odoo_links(link_payload)
                    except UserError as err:
                        if attempt_l >= 2:
                            raise
                        repair_l = (
                            messages
                            + [{'role': 'assistant', 'content': assistant_links}]
                            + [{'role': 'user', 'content': _(
                                'O bloco ODOO_LINK falhou no servidor Odoo:\n%(msg)s\n\n'
                                'Corrija o JSON: "links" como lista de objetos com "type" em '
                                '(form, attachment, report, menu, action) e campos exigidos por tipo '
                                '(veja instruções de sistema). Reenvie [[ODOO_LINK]]...[[/ODOO_LINK]] '
                                'corrigido ou responda sem pedir links.'
                            ) % {'msg': err.args[0]}}]
                        )
                        assistant_links, api_used = self._llm_chat(
                            provider, [api_used], model_name, api_key, repair_l, anth_cfg,
                        )
                        attempt_l += 1
                        if not self._extract_odoo_link_block(assistant_links):
                            final_text = assistant_links
                            break
                        continue

                    link_json = json.dumps(resolved_links, ensure_ascii=False, default=str)
                    if len(link_json) > 12000:
                        link_json = link_json[:12000] + '\n… (truncado)'
                    followup_l = (
                        messages
                        + [{'role': 'assistant', 'content': assistant_links}]
                        + [{'role': 'user', 'content': _(
                            'Segue o JSON com links gerados pelo servidor. Cada item tem "path" '
                            '(URL **relativa** ao site Odoo, começando por /), "label", "type" e '
                            '"ok". Na resposta final ao usuário: (1) use Markdown '
                            '`[label](path)` **somente** com os paths devolvidos onde ok=true; '
                            '(2) não invente URLs; (3) não mostre o bloco bruto [[ODOO_LINK]] ao '
                            'usuário; (4) **nunca** coloque `[[ODOO_LINK]]...[[/ODOO_LINK]]` '
                            'dentro de parênteses de Markdown `[texto](...)` — isso quebra o link.\n'
                            '%s'
                        ) % link_json}]
                    )
                    final_text, _api3 = self._llm_chat(
                        provider, [api_used], model_name, api_key, followup_l, anth_cfg,
                    )
                    break
            except Exception as err:
                if isinstance(err, UserError):
                    raise
                _logger.exception('Falha ao processar ODOO_LINK')
                raise UserError(
                    _('Não foi possível resolver os links sugeridos pelo modelo: %s') % err
                ) from err

        return final_text

    def _extract_marker_block(self, text, start_marker, end_marker):
        """Retorna o trecho entre marcadores (case-insensitive no início/fim) ou None."""
        if not text:
            return None
        start = text.find(start_marker)
        if start == -1:
            start = text.lower().find(start_marker.lower())
        if start == -1:
            return None
        slice_from = start + len(start_marker)
        end = text.find(end_marker, slice_from)
        if end == -1:
            end = text.lower().find(end_marker.lower(), slice_from)
        if end == -1:
            return None
        return text[slice_from:end].strip()

    def _extract_odoo_query_block(self, text):
        """Retorna o trecho JSON entre os marcadores ODOO_QUERY ou None."""
        return self._extract_marker_block(text, _ODOO_QUERY_START, _ODOO_QUERY_END)

    def _extract_odoo_link_block(self, text):
        """Retorna o trecho JSON entre os marcadores ODOO_LINK ou None."""
        return self._extract_marker_block(text, _ODOO_LINK_START, _ODOO_LINK_END)

    # -------------------------------------------------------------------------
    # Tool calling estruturado (Ollama / OpenAI tools API)
    # -------------------------------------------------------------------------

    def _tools_schema(self):
        """
        Esquema OpenAI ``tools=[...]`` exposto ao LLM.

        Cada função reflete uma operação ORM de leitura permitida pelo whitelist do servidor.
        O modelo invoca via ``tool_calls`` (em vez de ``[[ODOO_QUERY]]`` em texto), o que
        elimina parsing por regex e reduz hallucination de formato.
        """
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'odoo_search_read',
                    'description': (
                        'Lê registros do Odoo via ORM (Model.search_read). '
                        'Use para listar registros, pegar último, primeiro, filtrados por domínio. '
                        'Modelo deve estar na whitelist; campos devem existir no modelo.'
                    ),
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {
                                'type': 'string',
                                'description': 'Nome técnico (ex.: engc.os, res.partner)',
                            },
                            'domain': {
                                'type': 'array',
                                'description': (
                                    'Lista de triplas [campo, operador, valor]. AND implícito. '
                                    'Use [] para sem filtro. NÃO use expressões Python (datetime.now()).'
                                ),
                                'items': {},
                            },
                            'fields': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Campos a ler (sempre inclua "id").',
                            },
                            'order': {
                                'type': 'string',
                                'description': 'ORDER BY (ex.: "create_date desc"). Padrão: "id desc".',
                            },
                            'limit': {
                                'type': 'integer',
                                'description': 'Máximo de linhas (1-50, padrão 20).',
                            },
                        },
                        'required': ['model', 'fields'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'odoo_search_count',
                    'description': 'Conta registros do modelo que satisfazem o domínio.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {'type': 'string'},
                            'domain': {'type': 'array', 'items': {}},
                        },
                        'required': ['model'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'odoo_read_group',
                    'description': (
                        'Agrupa registros (Model.read_group). Use pra estatísticas por categoria.'
                    ),
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {'type': 'string'},
                            'domain': {'type': 'array', 'items': {}},
                            'fields': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Ex.: ["__count"] ou ["amount:sum"].',
                            },
                            'groupby': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Campos para agrupar (devem ser stored).',
                            },
                            'limit': {'type': 'integer'},
                        },
                        'required': ['model', 'fields', 'groupby'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'odoo_fields_get',
                    'description': 'Lista metadados de campos do modelo (tipo, label, selection).',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {'type': 'string'},
                            'fields': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Nomes de campos (máx 80).',
                            },
                        },
                        'required': ['model', 'fields'],
                    },
                },
            },
        ]

    def _coerce_tool_arg(self, value):
        """
        Tolera modelos pequenos que devolvem listas/dicts como string JSON ou repr-Python.

        Exemplos vistos com llama3.1:8b:
        - ``"['id', 'name']"`` → ``['id', 'name']``
        - ``"[['create_date', '<=', 'datetime.now()']]"`` → lista (sem ``datetime.now()``).
        - ``"1"`` para ``limit`` → ``1``.
        """
        if not isinstance(value, str):
            return value
        s = value.strip()
        if not s:
            return value
        # 1) Tenta JSON puro
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        # 2) Fallback: Python literal (aceita aspas simples). Usa ast.literal_eval (seguro).
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            pass
        return value

    def _normalize_tool_args(self, raw_args):
        """
        Converte ``arguments`` (string JSON gerado pelo LLM) num dict com tipos coercidos.

        Modelos pequenos costumam embutir listas/ints como string — coerimos campo a campo
        antes de delegar a ``_safe_execute_odoo_operation``.
        """
        if isinstance(raw_args, dict):
            data = dict(raw_args)
        elif isinstance(raw_args, str):
            try:
                data = json.loads(raw_args)
            except json.JSONDecodeError:
                # Última tentativa: literal Python.
                try:
                    data = ast.literal_eval(raw_args)
                except (ValueError, SyntaxError) as err:
                    raise UserError(_('Argumentos da ferramenta não são JSON válido: %s') % err)
                if not isinstance(data, dict):
                    raise UserError(_('Argumentos da ferramenta devem ser objeto JSON.'))
        else:
            raise UserError(_('Argumentos da ferramenta em formato inesperado: %s') % type(raw_args))

        # Coerção por campo conhecido.
        if 'model' in data and isinstance(data['model'], str):
            # Normaliza model name: case insensitive lookup na whitelist.
            mname = data['model'].strip()
            allowed = self._llm_whitelisted_model_names_set()
            if mname not in allowed:
                for m in allowed:
                    if m.lower() == mname.lower():
                        mname = m
                        break
            data['model'] = mname
        for k in ('domain', 'fields', 'groupby'):
            if k in data:
                data[k] = self._coerce_tool_arg(data[k])
        for k in ('limit', 'offset'):
            if k in data and isinstance(data[k], str):
                try:
                    data[k] = int(data[k])
                except ValueError:
                    pass
        return data

    def _execute_tool_call(self, name, raw_args):
        """
        Roteia ``tool_calls`` da resposta do modelo para as ops ORM permitidas.

        Retorna um dict ``{'ok': bool, ...}``. Sucesso → ``data``; falha → ``error`` (mensagem
        objetiva pra reentrar como contexto na próxima chamada ao modelo).
        """
        try:
            args = self._normalize_tool_args(raw_args)
        except UserError as err:
            return {'ok': False, 'error': str(err.args[0] if err.args else err)}

        op_map = {
            'odoo_search_read': 'search_read',
            'odoo_search_count': 'search_count',
            'odoo_read_group': 'read_group',
            'odoo_fields_get': 'fields_get',
        }
        op = op_map.get(name)
        if op is None:
            return {'ok': False, 'error': _('Ferramenta desconhecida: %s') % name}

        payload = dict(args)
        payload['operation'] = op
        try:
            data = self._safe_execute_odoo_operation(payload)
        except UserError as err:
            return {'ok': False, 'error': str(err.args[0] if err.args else err)}
        except Exception as err:  # noqa: BLE001
            _logger.exception('Tool call %s falhou', name)
            return {'ok': False, 'error': str(err)}

        # Pós-processamento: anexa _record_form_links para search_read (igual fluxo legacy).
        if op == 'search_read' and isinstance(data, list) and data:
            try:
                links = self._llm_build_record_form_links(payload.get('model'), data)
            except Exception:  # noqa: BLE001
                links = None
            if links:
                return {'ok': True, 'data': data, '_record_form_links': links}
        return {'ok': True, 'data': data}

    def _lmstudio_chat_with_tools(self, api_bases, model_name, api_key, messages, tools):
        """
        Igual a ``_lmstudio_chat_multi`` mas envia ``tools=[...]`` e retorna mensagem completa
        (com ``content`` e ``tool_calls``) — não só o texto.
        """
        if isinstance(api_bases, str):
            api_bases = [api_bases]
        if not api_bases:
            api_bases = ['http://host.docker.internal:1234/v1']
        payload = {
            'model': model_name,
            'messages': messages,
            'temperature': 0.2,
            'stream': False,
            'tools': tools,
        }
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = 'Bearer %s' % api_key
        url_errors = []
        for api_base in api_bases:
            url = '%s/chat/completions' % api_base
            try:
                body = self._lmstudio_post_json(url, payload, headers)
            except urllib.error.HTTPError as err:
                detail = err.read().decode('utf-8', errors='replace')
                _logger.warning('LM Studio HTTP %s: %s', err.code, detail)
                raise UserError(_('Erro HTTP ao falar com o LLM (%(code)s): %(msg)s') % {
                    'code': err.code, 'msg': detail or err.reason,
                }) from err
            except urllib.error.URLError as err:
                _logger.warning('LLM URL error em %s: %s', url, err)
                url_errors.append('%s → %s' % (url, err.reason or err))
                continue
            try:
                msg = body['choices'][0]['message']
            except (KeyError, IndexError, TypeError) as err:
                _logger.warning('Resposta inesperada do LLM: %s', body)
                raise UserError(_('Resposta inválida do LLM (sem choices[0].message).')) from err
            return msg, api_base
        raise UserError(_('Não foi possível conectar ao LLM: %s') % ('\n'.join(url_errors) or '(nenhuma URL)'))

    def _compose_via_tool_calling(self, api_bases, model_name, api_key):
        """
        Loop assistant↔tool até obter resposta final em texto puro (sem ``tool_calls``).

        Limite ``_TOOL_CALLING_MAX_ITER`` evita loops infinitos. A cada iteração:
        1. POST /chat/completions com ``tools=[...]``.
        2. Se ``finish_reason='tool_calls'``, executa cada call e anexa mensagens ``role=tool``.
        3. Senão, retorna ``content`` como resposta final.
        """
        tools = self._tools_schema()
        messages = self._build_openai_messages()
        api_used = api_bases[0] if api_bases else None

        for iteration in range(_TOOL_CALLING_MAX_ITER):
            msg, api_used = self._lmstudio_chat_with_tools(
                [api_used] if api_used else api_bases, model_name, api_key, messages, tools,
            )
            tool_calls = msg.get('tool_calls') or []
            if not tool_calls:
                return (msg.get('content') or '').strip()

            # Anexa a mensagem do assistente com tool_calls (formato OpenAI).
            messages.append({
                'role': 'assistant',
                'content': msg.get('content') or '',
                'tool_calls': tool_calls,
            })
            # Executa cada tool call e anexa resultado.
            for tc in tool_calls:
                fn = tc.get('function') or {}
                fname = fn.get('name') or ''
                fargs = fn.get('arguments') or '{}'
                result = self._execute_tool_call(fname, fargs)
                content = json.dumps(result, ensure_ascii=False, default=str)
                if len(content) > 16000:
                    content = content[:16000] + '\n… (truncado)'
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tc.get('id') or '',
                    'content': content,
                })

        # Excedeu iterações: pede ao modelo uma resposta final sem chamar mais ferramentas.
        messages.append({
            'role': 'user',
            'content': _(
                'Limite de chamadas de ferramentas atingido. Responda agora com texto puro '
                'baseado nos resultados já obtidos, sem novas tool calls.'
            ),
        })
        msg, _api = self._lmstudio_chat_with_tools(
            [api_used] if api_used else api_bases, model_name, api_key, messages, tools=[],
        )
        return (msg.get('content') or '').strip()

    def _llm_build_record_form_links(self, model_name, rows):
        """Helper: gera lista de paths /web#... para rows com 'id' (search_read pós-processamento)."""
        if not model_name or not rows:
            return []
        out = []
        for row in rows:
            if not isinstance(row, dict) or 'id' not in row:
                continue
            label = self._llm_pick_record_label(row)
            out.append({
                'id': row['id'],
                'label': label,
                'path': '/web#id=%s&model=%s&view_type=form' % (row['id'], model_name),
            })
        return out

    def _llm_pick_record_label(self, row):
        """
        Escolhe texto curto para o rótulo de um link Markdown a partir de um dict ``search_read``.
        """
        if not isinstance(row, dict):
            return '?'
        preferred_keys = (
            'display_name',
            'name',
            'complete_name',
            'ref',
            'numero_os',
            'os_num',
            'default_code',
            'codigo',
            'codigo_os',
            'x_name',
        )
        for key in preferred_keys:
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:200]
            if val is not None and not isinstance(val, (list, tuple, dict, bytes)):
                s = str(val).strip()
                if s:
                    return s[:200]
        rid = row.get('id')
        return '#%s' % rid if rid is not None else '?'

    def _llm_form_links_for_query_rows(self, model_name, rows):
        """Gera ``{id, label, path}`` por linha de ``search_read`` (modelo na whitelist)."""
        if model_name not in self._llm_whitelisted_model_names_set():
            return []
        if not isinstance(rows, list):
            return []
        out = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            rid = row.get('id')
            try:
                rid = int(rid)
            except (TypeError, ValueError):
                continue
            if rid < 1:
                continue
            label = self._llm_pick_record_label(row)
            path = '/web#id=%s&model=%s&view_type=form' % (rid, model_name)
            out.append({'id': rid, 'label': label, 'path': path})
        return out

    def _llm_form_links_for_search_ids(self, model_name, id_list):
        """Gera links de formulário quando ``operation`` é ``search`` (lista de ids inteiros)."""
        if model_name not in self._llm_whitelisted_model_names_set():
            return []
        if not isinstance(id_list, list):
            return []
        out = []
        for rid in id_list:
            try:
                rid = int(rid)
            except (TypeError, ValueError):
                continue
            if rid < 1:
                continue
            path = '/web#id=%s&model=%s&view_type=form' % (rid, model_name)
            out.append({'id': rid, 'label': '#%s' % rid, 'path': path})
        return out

    def _llm_build_followup_query_json(self, payload, rows):
        """
        Serializa o resultado do ODOO_QUERY; em ``search_read`` ou ``search`` inclui
        ``_record_form_links`` para o modelo listar cada registo com ``* [rótulo](path)``.
        """
        operation = (payload.get('operation') or 'search_read').strip().lower()
        model_nm = (payload.get('model') or '').strip()
        form_links = []
        if model_nm:
            if operation == 'search_read' and isinstance(rows, list):
                form_links = self._llm_form_links_for_query_rows(model_nm, rows)
            elif operation == 'search' and isinstance(rows, list):
                form_links = self._llm_form_links_for_search_ids(model_nm, rows)

        if not form_links:
            data_json = json.dumps(rows, ensure_ascii=False, default=str)
            if len(data_json) > 12000:
                data_json = data_json[:12000] + '\n… (truncado)'
            return data_json

        instruction = _(
            'Ao listar estes registos em bullet points para o usuário, use **uma linha por '
            'registo** no formato Markdown exato: `* [label](path)` — copie **label** e **path** '
            'de cada objeto em _record_form_links (não invente paths nem altere ids). '
            'Inclua todos os itens em _record_form_links na lista com link.'
        )
        if operation == 'search':
            envelope = {
                '_record_form_links': list(form_links),
                'record_ids': [l['id'] for l in form_links],
                'instruction': instruction,
            }
        else:
            by_id = {
                r['id']: r
                for r in rows
                if isinstance(r, dict) and r.get('id') is not None
            }
            synced_records = [by_id[i] for i in (x['id'] for x in form_links) if i in by_id]
            envelope = {
                '_record_form_links': list(form_links),
                'records': synced_records,
                'instruction': instruction,
            }

        def _dump(env):
            return json.dumps(env, ensure_ascii=False, default=str)

        serialized = _dump(envelope)
        while len(serialized) > 12000 and len(envelope['_record_form_links']) > 3:
            envelope['_record_form_links'].pop()
            if operation == 'search':
                envelope['record_ids'].pop()
            else:
                envelope['records'].pop()
            serialized = _dump(envelope)
        if len(serialized) > 12000:
            serialized = serialized[:12000] + '\n… (truncado)'
        return serialized

    def action_clear_messages(self):
        """Remove todas as mensagens da sessão (mantém a sessão)."""
        for rec in self:
            if rec.user_id.id != self.env.user.id:
                raise AccessError(_('Esta sessão de chat pertence a outro usuário.'))
            rec.message_ids.unlink()
        return True

    # -------------------------------------------------------------------------
    # Montagem de mensagens e prompt de sistema
    # -------------------------------------------------------------------------

    def _build_openai_messages(self):
        """Monta a lista de mensagens para a API (histórico recente + sistema)."""
        self.ensure_one()
        sys_content = self._system_prompt()
        out = [{'role': 'system', 'content': sys_content}]
        msgs = self.message_ids.sorted(key=lambda m: (m.create_date, m.id))
        # Limite de histórico para não estourar contexto do modelo local
        for m in msgs[-40:]:
            if m.role == 'system':
                continue
            out.append({'role': m.role, 'content': m.body})
        return out

    def _system_prompt(self):
        """
        Instruções fixas: papel, catálogos (modelos, relatórios QWeb), campos whitelist,
        ODOO_QUERY, ODOO_LINK e formato de URLs de relatório (documentação Odoo 16).
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        raw = icp.get_param('afr_llm_assistant.whitelisted_models') or ''
        allowed = [x.strip() for x in raw.split(',') if x.strip()]
        if not allowed:
            allowed = ['afr.supervisorio.ciclos']

        allowed_csv = ', '.join(allowed)
        missing = [m for m in allowed if m not in self.env]
        missing_txt = (
            _('\nModelos na whitelist mas não carregados (módulo ausente): %s') % ', '.join(missing)
            if missing else ''
        )

        catalog_models = self._installed_models_catalog_text(max_chars=_MODEL_CATALOG_MAX_CHARS)
        catalog_reports = self._reports_catalog_for_user_text(max_chars=_REPORTS_CATALOG_MAX_CHARS)
        whitelist_fields = self._whitelist_models_field_catalog(
            allowed, max_total_chars=_WHITELIST_FIELDS_MAX_CHARS
        )

        now_txt = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()
        ).strftime('%Y-%m-%d %H:%M:%S %Z')

        return _(
            'Você é um assistente do Odoo 16 ligado a esta base. Responda em português do Brasil, '
            'com clareza e precisão.\n'
            'Data/hora de referência do usuário: %(now)s\n\n'
            '### REGRAS CRÍTICAS (nunca quebre) ###\n'
            '1. **NUNCA** escreva SQL, nem comandos de banco (SELECT, UPDATE, ir_actuate_record, etc.). '
            'Você não tem acesso direto ao banco — só pelo bloco [[ODOO_QUERY]] (JSON ORM Odoo).\n'
            '2. **NUNCA** invente nomes de tabela/coluna SQL. Use **apenas** nomes de modelo e campo '
            'que aparecem na whitelist abaixo (secção "###").\n'
            '3. Para qualquer pergunta sobre dados reais ("qual a última OS", "quantos clientes", '
            '"liste os equipamentos"…) você **DEVE** emitir um bloco [[ODOO_QUERY]] JSON. Não responda '
            'com instruções de como o usuário deve fazer — o sistema executa a consulta automaticamente '
            'e devolve o resultado em uma segunda chamada.\n'
            '4. Após receber resultado em "data" do servidor, formate a resposta usando **somente** '
            'esses dados, com links Markdown `* [label](path)` se houver `_record_form_links`.\n\n'
            '### EXEMPLOS (siga o formato literalmente) ###\n'
            'Pergunta: "Qual a última OS criada?"\n'
            'Resposta correta (primeira passagem):\n'
            '[[ODOO_QUERY]]\n'
            '{"operation": "search_read", "model": "engc.os", "domain": [], '
            '"fields": ["id", "name", "create_date", "state"], '
            '"order": "create_date desc", "limit": 1}\n'
            '[[/ODOO_QUERY]]\n\n'
            'Pergunta: "Quantas OS estão em aberto?"\n'
            'Resposta correta:\n'
            '[[ODOO_QUERY]]\n'
            '{"operation": "search_count", "model": "engc.os", '
            '"domain": [["state", "not in", ["done", "cancel"]]]}\n'
            '[[/ODOO_QUERY]]\n\n'
            'Pergunta: "Liste as 5 últimas OS do técnico João"\n'
            'Resposta correta:\n'
            '[[ODOO_QUERY]]\n'
            '{"operation": "search_read", "model": "engc.os", '
            '"domain": [["tecnico_id.name", "ilike", "João"]], '
            '"fields": ["id", "name", "create_date", "state", "tecnico_id"], '
            '"order": "create_date desc", "limit": 5}\n'
            '[[/ODOO_QUERY]]\n\n'
            '⚠️ Resposta **errada** (NUNCA faça): "Para obter a última OS use `SELECT ... FROM ...`" '
            '— isso não funciona, o usuário não tem acesso SQL.\n\n'
            '--- Catálogo de modelos instalados (ir.model / registry) ---\n'
            'Formato por linha: nome_tecnico | nome amigável. Use para interpretar perguntas e '
            'saber o que existe na instância. O catálogo pode estar truncado por limite de contexto.\n'
            '%(catalog)s\n'
            '%(missing)s\n\n'
            '--- Catálogo de relatórios QWeb (ir.actions.report visíveis ao seu usuário) ---\n'
            'Cada linha: report_name | título | model | converter (valor a usar em ODOO_LINK).\n'
            'Use **report_name** exatamente como na primeira coluna para links de impressão.\n'
            'URLs HTTP no Odoo 16 (usuário autenticado), conforme documentação oficial: '
            '``/report/pdf/<report_name>/<ids>``, ``/report/html/<report_name>/<ids>`` ou '
            '``/report/text/<report_name>/<ids>`` — ``ids`` são inteiros separados por vírgula '
            '(ex.: ``/report/pdf/sale.report_saleorder/38``).\n'
            '%(catalog_reports)s\n\n'
            '--- Modelos permitidos para ODOO_QUERY (leitura validada no servidor) ---\n'
            'Só pode usar [[ODOO_QUERY]] com estes nomes técnicos: %(allowed_csv)s\n'
            'Fluxo obrigatório: (1) identifique o modelo na whitelist; (2) localize a secção "### " '
            'desse modelo; (3) copie **literalmente** os nomes de campo dessa lista para '
            '"domain", "fields", "groupby", etc. — nunca invente nomes. Em cada linha de campo, '
            'o sufixo ``| help: …`` reproduz o texto de ajuda definido no Odoo (tooltip/documentação); '
            'use-o para interpretar o significado do campo.\n'
            'Preferência: use domínio só como lista plana de triplas (AND implícito), sem & | !, '
            'para evitar erros de precedência.\n\n'
            '%(whitelist_fields)s\n\n'
            'Chave "operation" (opcional; padrão search_read). Exemplos de bloco JSON:\n'
            '• Contagem: {"operation": "search_count", "model": "res.partner", '
            '"domain": [["is_company", "=", true], ["cnpj_cpf", "!=", false]]}\n'
            '• Só ids: {"operation": "search", "model": "res.partner", "domain": [], "limit": 100, '
            '"order": "id desc"}\n'
            '• Linhas: {"operation": "search_read", "model": "...", "domain": [], '
            '"fields": ["id", "name", "display_name"], "order": "id desc", "limit": 20}\n'
            '  (inclua sempre "id" e o campo que o usuário reconhece — ex.: "name" para '
            'número da OS — para o servidor gerar _record_form_links com rótulos corretos.)\n'
            '• Agrupado: {"operation": "read_group", "model": "...", "domain": [], '
            '"fields": ["__count"], "groupby": ["campo_armazenado"], "limit": 80}\n'
            '• Metadados: {"operation": "fields_get", "model": "...", '
            '"fields": ["id", "name"], "attributes": ["string", "type", "selection"]}\n\n'
            'Quando precisar de dados reais, inclua exatamente um bloco:\n'
            '[[ODOO_QUERY]]\n'
            '{ ... JSON conforme um dos exemplos ... }\n'
            '[[/ODOO_QUERY]]\n\n'
            'Regras: search_read com limit 1–50; search/search_count/read_group com limit até 200; '
            'em search_read use apenas campos search_read_ok (ou "id"). O servidor descarta campos '
            'inválidos, mas evite erros copiando da lista. Se a pergunta não exigir dados, responda '
            'sem o bloco.\n'
            'Após um search_read/search bem-sucedido, o servidor pode incluir ``_record_form_links`` '
            '(id, label, path) com URLs de formulário ``/web#id=…&model=…&view_type=form``. Quando '
            'apresentar uma lista de registos, use **obrigatoriamente** esses paths em bullets '
            '``* [label](path)`` conforme a instrução no JSON.\n\n'
            '--- Links clicáveis (ODOO_LINK) ---\n'
            'Para atalhos (formulário, anexo, relatório PDF/HTML/texto, menu ou ação de janela), '
            'inclua um bloco **isolado** (várias linhas), **nunca** dentro de Markdown '
            '``[rótulo](...)`` — ou seja, não escreva ``[texto]([[ODOO_LINK]]{...})``.\n'
            '[[ODOO_LINK]]\n'
            '{"links": [\n'
            '  {"type": "form", "model": "nome_na_whitelist", "id": 10, "label": "opcional"},\n'
            '  {"type": "attachment", "id": 99, "label": "opcional"},\n'
            '  {"type": "report", "report_name": "copie_da_primeira_coluna_do_catalogo_acima", '
            '"ids": [5694], "converter": "pdf", "label": "opcional"},\n'
            '  {"type": "menu", "menu_id": 123, "label": "opcional"},\n'
            '  {"type": "action", "action_id": 456, "model": "opcional se id", "id": 10, "label": "opcional"}\n'
            ']}\n'
            '[[/ODOO_LINK]]\n'
            'Depois que o servidor devolver JSON com "path", na resposta ao usuário use Markdown '
            '``[texto](path)`` só com esses paths (onde ok=true). Formulários: modelos na whitelist '
            'do ODOO_QUERY. Relatórios: **report_name** obrigatoriamente copiado do catálogo de '
            'relatórios (não invente); "converter" deve coincidir com a coluna converter '
            '(pdf/html/text). Os ids são do modelo indicado na coluna model do relatório.'
        ) % {
            'now': now_txt,
            'catalog': catalog_models,
            'missing': missing_txt,
            'catalog_reports': catalog_reports,
            'allowed_csv': allowed_csv,
            'whitelist_fields': whitelist_fields,
        }

    def _installed_models_catalog_text(self, max_chars):
        """
        Lista compacta de modelos registados no ``ir.model`` que existem no ``Environment``
        (módulos carregados). Ordenado por nome técnico; truncado em ``max_chars`` caracteres.
        """
        IrModel = self.env['ir.model'].sudo()
        rows = IrModel.search_read([], ['model', 'name'], order='model')
        lines = [_('nome_tecnico | nome_amigavel')]
        used = len(lines[0]) + 1
        truncated = False
        for row in rows:
            mname = row['model']
            if mname not in self.env:
                continue
            label = (row.get('name') or '').replace('|', '/').replace('\n', ' ').strip()[:200]
            line = '%s | %s' % (mname, label)
            add = len(line) + 1
            if used + add > max_chars:
                truncated = True
                break
            lines.append(line)
            used += add
        out = '\n'.join(lines)
        if truncated:
            out += '\n' + _('… (catálogo truncado; aumente ODOO_LM_CATALOG_MODELS_CHARS se o modelo procurado não aparecer)')
        return out

    def _report_type_to_converter_hint(self, report_type):
        """
        Mapeia ``ir.actions.report.report_type`` para o ``converter`` da rota HTTP
        ``/report/<converter>/<report_name>/<docids>`` (documentação Odoo 16).
        """
        return {
            'qweb-pdf': 'pdf',
            'qweb-html': 'html',
            'qweb-text': 'text',
        }.get(report_type or '', '?')

    def _reports_catalog_for_user_text(self, max_chars):
        """
        Lista ``ir.actions.report`` que o usuário atual pode ler (sem ``sudo``).

        Formato por linha: ``report_name | título | model | converter``.
        O ``report_name`` é o identificador do template QWeb usado na URL e em ODOO_LINK.
        """
        self.ensure_one()
        Report = self.env['ir.actions.report']
        rows = Report.search_read(
            [],
            ['report_name', 'name', 'model', 'report_type'],
            order='report_name',
        )
        lines = [_('report_name | titulo | model | converter')]
        used = len(lines[0]) + 1
        truncated = False
        for row in rows:
            rn = (row.get('report_name') or '').strip()
            if not rn:
                continue
            title = (row.get('name') or '').replace('|', '/').replace('\n', ' ').strip()[:180]
            model = (row.get('model') or '').replace('|', '/').strip()[:120]
            conv = self._report_type_to_converter_hint(row.get('report_type'))
            line = '%s | %s | %s | %s' % (rn, title, model, conv)
            add = len(line) + 1
            if used + add > max_chars:
                truncated = True
                break
            lines.append(line)
            used += add
        out = '\n'.join(lines)
        if truncated:
            out += '\n' + _(
                '… (catálogo de relatórios truncado; aumente ODOO_LM_CATALOG_REPORTS_CHARS se faltar algum)'
            )
        elif len(lines) <= 1:
            out += '\n' + _('(nenhum relatório QWeb visível para este usuário)')
        return out

    def _whitelist_models_field_catalog(self, allowed_names, max_total_chars):
        """
        Para cada modelo permitido, descreve **todos** os campos públicos (nome, tipo, label,
        texto ``help`` do Odoo quando existir, relação, se entra em search_read).
        """
        chunks = []
        used = 0
        valid = [m for m in allowed_names if m in self.env]
        per_model = max(800, max_total_chars // max(1, len(valid) or 1))

        for mname in allowed_names:
            if mname not in self.env:
                block = '### %s\n%s\n' % (mname, _('(não instalado — remova da whitelist ou instale o módulo)'))
            else:
                Model = self.env[mname]
                desc = (getattr(Model, '_description', None) or '') or ''
                header = '### %s\n%s\n' % (mname, desc)
                body = self._describe_model_fields_text(Model, max_chars=per_model)
                block = header + body + '\n'
            if used + len(block) > max_total_chars:
                chunks.append(_('… (detalhe de mais modelos da whitelist omitido pelo limite de contexto)\n'))
                break
            chunks.append(block)
            used += len(block)
        return ''.join(chunks) if chunks else _('(nenhum modelo permitido)')

    def _describe_model_fields_text(self, Model, max_chars):
        """
        Lista campos do modelo ordenados por nome: tipo, etiqueta, ``help`` (quando definido no
        Odoo), se pode ir em ``search_read``, comodel para relações, amostra de ``selection``.
        """
        bits = []
        used = 0

        def _field_help_excerpt(field):
            """Extrai e sanitiza ``field.help`` (string traduzível do Odoo) para o contexto do LLM."""
            raw = getattr(field, 'help', None)
            if not raw:
                return ''
            try:
                txt = str(raw)
            except Exception:
                return ''
            txt = txt.replace('\n', ' ').replace('\r', ' ').replace('|', '/').strip()
            if not txt:
                return ''
            if len(txt) > _FIELD_HELP_MAX_CHARS:
                txt = txt[: _FIELD_HELP_MAX_CHARS - 1] + '…'
            return txt

        def _search_read_ok(fname, field):
            if fname == 'id':
                return True
            if field.compute and not field.store:
                return False
            return True

        def _selection_preview(field):
            if field.type != 'selection':
                return ''
            sel = field.selection
            if isinstance(sel, str):
                return ' | sel=dinâmica'
            if callable(sel):
                return ' | sel=callable'
            if not sel:
                return ''
            try:
                pairs = list(sel)
            except TypeError:
                return ''
            keys = [k for k, _lbl in pairs[:14]]
            if not keys:
                return ''
            extra = '…' if len(pairs) > 14 else ''
            return ' | valores: %s%s' % (','.join(str(k) for k in keys), extra)

        for fname in sorted(Model._fields):
            if fname.startswith('_'):
                continue
            field = Model._fields[fname]
            tipo = field.type
            label = (field.string or '').replace('\n', ' ').strip()[:120]
            sr = 'search_read_ok' if _search_read_ok(fname, field) else 'só_domínio'
            tags = [sr]
            if field.readonly:
                tags.append('ro')
            if field.required:
                tags.append('req')
            rel = getattr(field, 'comodel_name', None) or ''
            rel_part = (' | → %s' % rel) if rel else ''
            sel_part = _selection_preview(field)
            help_excerpt = _field_help_excerpt(field)
            help_part = (' | help: %s' % help_excerpt) if help_excerpt else ''
            line = '  - %s | tipo=%s | "%s" | [%s]%s%s%s\n' % (
                fname, tipo, label, ','.join(tags), rel_part, sel_part, help_part,
            )
            if used + len(line) > max_chars:
                bits.append('  - … (%s)\n' % _('mais campos omitidos'))
                break
            bits.append(line)
            used += len(line)
        return ''.join(bits)

    # -------------------------------------------------------------------------
    # Cliente HTTP (API OpenAI-compatible do LM Studio)
    # -------------------------------------------------------------------------

    def _iter_lmstudio_api_bases(self, icp):
        """
        Lista de URLs base (sem barra final), na ordem de tentativa.

        * ``ODOO_LMSTUDIO_HOST_LAN`` (opcional): IPv4 do host onde roda o LM Studio; monta
          ``http://IP:PORTA/v1`` e tenta **primeiro** (útil quando ``host.docker.internal``
          falha de dentro do container mas o IP LAN responde).
        * ``ODOO_LMSTUDIO_API_BASE``: uma ou várias URLs separadas por vírgula.
        * Caso contrário, parâmetro Odoo ``afr_llm_assistant.api_base_url`` (também pode ser lista vírgula).
        * Caso contrário, padrões ``host.docker.internal`` e ``172.17.0.1``.
        """
        env_raw = (os.environ.get('ODOO_LMSTUDIO_API_BASE') or '').strip()
        bases = []
        if env_raw:
            for part in env_raw.split(','):
                p = part.strip().rstrip('/')
                if p and p not in bases:
                    bases.append(p)
        else:
            icp_raw = (icp.get_param('afr_llm_assistant.api_base_url') or '').strip()
            if icp_raw:
                for part in icp_raw.split(','):
                    p = part.strip().rstrip('/')
                    if p and p not in bases:
                        bases.append(p)
            else:
                for d in ('http://host.docker.internal:1234/v1', 'http://172.17.0.1:1234/v1'):
                    if d not in bases:
                        bases.append(d)
        return self._prepend_lmstudio_lan_url(bases)

    def _prepend_lmstudio_lan_url(self, bases):
        """Coloca ``http://<LAN>:<porta>/v1`` no início se ``ODOO_LMSTUDIO_HOST_LAN`` for um IPv4 válido."""
        lan = (os.environ.get('ODOO_LMSTUDIO_HOST_LAN') or '').strip()
        if not lan:
            return bases
        if not _LAN_IPV4_RE.match(lan):
            _logger.warning(
                'ODOO_LMSTUDIO_HOST_LAN ignorado (não é um IPv4 válido): %r. '
                'Use só números, ex. 192.168.0.188 — não use a letra "x" como placeholder.',
                lan,
            )
            return bases
        port = (os.environ.get('ODOO_LMSTUDIO_HOST_PORT') or '1234').strip()
        if not port.isdigit():
            port = '1234'
        url = 'http://%s:%s/v1' % (lan, port)
        out = []
        if url not in out:
            out.append(url)
        for b in bases:
            if b != url and b not in out:
                out.append(b)
        return out

    def _lmstudio_chat_multi(self, api_bases, model_name, api_key, messages):
        """
        Tenta POST /chat/completions em cada URL base até obter resposta.

        :returns: tupla (texto do assistente, url_base que funcionou)
        """
        if isinstance(api_bases, str):
            api_bases = [api_bases]
        if not api_bases:
            api_bases = ['http://host.docker.internal:1234/v1']

        payload = {
            'model': model_name,
            'messages': messages,
            'temperature': 0.2,
            'stream': False,
        }
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = 'Bearer %s' % api_key

        url_errors = []
        for api_base in api_bases:
            url = '%s/chat/completions' % api_base
            try:
                body = self._lmstudio_post_json(url, payload, headers)
            except urllib.error.HTTPError as err:
                detail = err.read().decode('utf-8', errors='replace')
                _logger.warning('LM Studio HTTP %s: %s', err.code, detail)
                raise UserError(
                    _('Erro HTTP ao falar com o LM Studio (%(code)s): %(msg)s') % {
                        'code': err.code,
                        'msg': detail or err.reason,
                    }
                ) from err
            except urllib.error.URLError as err:
                _logger.warning('LM Studio URL error em %s: %s', url, err)
                url_errors.append('%s → %s' % (url, err.reason or err))
                continue
            try:
                text = body['choices'][0]['message']['content'].strip()
            except (KeyError, IndexError, TypeError, AttributeError) as err:
                _logger.warning('Resposta inesperada do LM Studio: %s', body)
                raise UserError(
                    _('Resposta inválida do LM Studio (esperado choices[0].message.content).')
                ) from err
            return text, api_base

        raise UserError(
            _('Não foi possível conectar ao LM Studio em nenhuma URL tentada:\n%(urls)s\n\n'
              'No computador onde o LM Studio roda, o servidor precisa aceitar conexões vindas '
              'do Docker (não apenas localhost):\n'
              '• Na interface: ative a opção equivalente a “Servir na rede local” / bind em 0.0.0.0.\n'
              '• Na CLI: ``lms server start --bind 0.0.0.0`` ou variável ``LMS_SERVER_HOST=0.0.0.0``.\n'
              '• Confirme a porta (ex.: 1234) e teste no host: ``curl -sS http://127.0.0.1:1234/v1/models``.\n'
              '• No compose: ``ODOO_LMSTUDIO_HOST_LAN`` com o IPv4 do host (ex.: onde '
              '``host.docker.internal`` resolve no curl) ou ``ODOO_LMSTUDIO_API_BASE`` com URLs '
              'separadas por vírgula; ou ``network_mode: host`` no serviço Odoo (Linux).') % {
                'urls': '\n'.join(url_errors) or _('(nenhuma URL)'),
            }
        )

    def _lmstudio_post_json(self, url, payload, headers):
        """POST JSON e retorna o corpo decodificado ou levanta URLError/HTTPError."""
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode('utf-8'))

    # -------------------------------------------------------------------------
    # Dispatcher de provedor + cliente Anthropic (API nativa /v1/messages)
    # -------------------------------------------------------------------------

    def _llm_chat(self, provider, api_bases, model_name, api_key, messages, anth_cfg):
        """
        Despacha a chamada para o provedor configurado.

        :param str provider: ``lmstudio`` (OpenAI-compat) ou ``anthropic`` (Claude /v1/messages).
        :param list api_bases: URLs base do LM Studio (ignorado em anthropic).
        :param str model_name: id do modelo.
        :param str api_key: bearer (lmstudio, opcional) ou x-api-key (anthropic, obrigatório).
        :param list messages: lista no formato OpenAI (role/content). Em anthropic, mensagens
            com role=system são extraídas e enviadas como parâmetro ``system`` separado.
        :param dict anth_cfg: configs específicas Anthropic (``url``, ``version``, ``max_tokens``).
        :returns: tupla ``(texto_assistente, identificador_da_url_que_respondeu)``.
        """
        if provider == 'anthropic':
            return self._anthropic_chat(model_name, api_key, messages, anth_cfg)
        return self._lmstudio_chat_multi(api_bases, model_name, api_key, messages)

    def _anthropic_config(self, icp):
        """Lê parâmetros do provedor Anthropic do ``ir.config_parameter`` (com defaults seguros)."""
        url = (os.environ.get('ODOO_ANTHROPIC_API_URL') or '').strip().rstrip('/')
        if not url:
            url = (icp.get_param('afr_llm_assistant.anthropic_api_url') or '').strip().rstrip('/')
        if not url:
            url = 'https://api.anthropic.com/v1/messages'
        version = (icp.get_param('afr_llm_assistant.anthropic_version') or '').strip()
        if not version:
            version = '2023-06-01'
        raw_max = (icp.get_param('afr_llm_assistant.anthropic_max_tokens') or '').strip()
        try:
            max_tokens = int(raw_max) if raw_max else 4096
        except ValueError:
            max_tokens = 4096
        if max_tokens < 1:
            max_tokens = 4096
        return {'url': url, 'version': version, 'max_tokens': max_tokens}

    def _anthropic_split_system(self, messages):
        """
        Separa mensagens estilo OpenAI no formato Anthropic.

        A API ``/v1/messages`` não aceita ``role=system`` dentro da lista — o conteúdo deve ir
        no parâmetro ``system`` de topo. Mensagens consecutivas com a mesma role são preservadas
        (a API exige alternância user/assistant; mantemos a ordem original — se o consumidor
        gerou pares válidos, segue).
        """
        system_parts = []
        out = []
        for m in messages or []:
            if not isinstance(m, dict):
                continue
            role = (m.get('role') or '').strip().lower()
            content = m.get('content')
            if content is None:
                continue
            if role == 'system':
                if isinstance(content, str) and content.strip():
                    system_parts.append(content)
                continue
            if role not in ('user', 'assistant'):
                # Anthropic só aceita user/assistant; tratamos qualquer outro como user.
                role = 'user'
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, default=str)
            out.append({'role': role, 'content': content})
        system_text = '\n\n'.join(system_parts) if system_parts else ''
        # Anthropic exige a lista não-vazia começando com 'user'.
        if not out:
            out = [{'role': 'user', 'content': '...'}]
        elif out[0]['role'] != 'user':
            out.insert(0, {'role': 'user', 'content': '...'})
        return system_text, out

    def _anthropic_chat(self, model_name, api_key, messages, anth_cfg):
        """
        POST ``/v1/messages`` na API Anthropic.

        :returns: tupla ``(texto, url_usada)`` para manter contrato de ``_lmstudio_chat_multi``.
        """
        if not api_key:
            raise UserError(_(
                'Provedor Anthropic precisa de "Chave API" (sk-ant-...) nas configurações.'
            ))
        anth_cfg = anth_cfg or self._anthropic_config(self.env['ir.config_parameter'].sudo())
        url = anth_cfg['url']
        system_text, conv = self._anthropic_split_system(messages)
        payload = {
            'model': model_name,
            'max_tokens': anth_cfg['max_tokens'],
            'messages': conv,
        }
        if system_text:
            payload['system'] = system_text
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': anth_cfg['version'],
        }
        try:
            body = self._lmstudio_post_json(url, payload, headers)
        except urllib.error.HTTPError as err:
            detail = err.read().decode('utf-8', errors='replace')
            _logger.warning('Anthropic HTTP %s: %s', err.code, detail)
            raise UserError(
                _('Erro HTTP ao falar com a API Anthropic (%(code)s): %(msg)s') % {
                    'code': err.code,
                    'msg': detail or err.reason,
                }
            ) from err
        except urllib.error.URLError as err:
            _logger.warning('Anthropic URL error em %s: %s', url, err)
            raise UserError(
                _('Não foi possível conectar à API Anthropic em %(url)s: %(err)s') % {
                    'url': url,
                    'err': err.reason or err,
                }
            ) from err
        try:
            blocks = body['content']
            text_parts = []
            for blk in blocks:
                if isinstance(blk, dict) and blk.get('type') == 'text':
                    t = blk.get('text')
                    if isinstance(t, str):
                        text_parts.append(t)
            text = ''.join(text_parts).strip()
            if not text:
                raise KeyError('content[].text vazio')
        except (KeyError, IndexError, TypeError, AttributeError) as err:
            _logger.warning('Resposta inesperada da API Anthropic: %s', body)
            raise UserError(
                _('Resposta inválida da API Anthropic (esperado content[].text).')
            ) from err
        return text, url

    # -------------------------------------------------------------------------
    # Execução segura de consultas sugeridas pelo LLM
    # -------------------------------------------------------------------------

    def _sanitize_llm_domain_and_order(self, Model, payload):
        """
        Normaliza ``domain`` e ``order`` no payload (listas planas de triplas no domínio).
        """
        domain = payload.get('domain') or []
        if self._domain_is_flat_triplets_only(domain):
            payload['domain'] = self._strip_invalid_domain_leaves(Model, domain)
        else:
            payload['domain'] = list(domain) if isinstance(domain, (list, tuple)) else []
        raw_order = payload.get('order')
        payload['order'] = self._normalize_search_read_order(
            Model, raw_order if isinstance(raw_order, str) else 'id desc'
        )

    def _sanitize_odoo_query_payload(self, Model, payload):
        """
        Corrige ``fields``, ``domain`` (só listas planas de triplas) e ``order`` para nomes
        que existem no modelo, evitando erros por campos inventados ou de outro modelo.
        """
        payload['fields'] = self._normalize_search_read_fields_list(Model, payload.get('fields'))
        self._sanitize_llm_domain_and_order(Model, payload)

    def _domain_is_flat_triplets_only(self, domain):
        """True se o domínio for só triplas (AND implícito), sem operadores & | !."""
        if not isinstance(domain, (list, tuple)) or not domain:
            return True
        return all(
            isinstance(x, (list, tuple)) and len(x) == 3 for x in domain
        )

    def _strip_invalid_domain_leaves(self, Model, domain):
        """Remove folhas com campo inexistente ou operador não permitido."""
        out = []
        for leaf in domain:
            if not (isinstance(leaf, (list, tuple)) and len(leaf) == 3):
                continue
            fname, op, val = leaf
            if fname not in Model._fields:
                _logger.warning(
                    'ODOO_QUERY: removida folha de domínio (campo inexistente em %s): %s',
                    Model._name, fname,
                )
                continue
            if op not in _SAFE_DOMAIN_OPS:
                _logger.warning(
                    'ODOO_QUERY: removida folha de domínio (operador não permitido): %s', op
                )
                continue
            out.append((fname, op, val))
        if not out:
            _logger.warning(
                'ODOO_QUERY: todas as folhas do domínio eram inválidas para %s; domínio vazio (todos)',
                Model._name,
            )
            return []
        return out

    def _normalize_search_read_fields_list(self, Model, fields_list):
        """Filtra ``fields`` para nomes existentes e armazenados (search_read)."""
        if not fields_list:
            fields_list = ['display_name']
        if not isinstance(fields_list, (list, tuple)):
            return ['id', 'display_name']
        ok = []
        for fname in fields_list:
            if fname not in Model._fields:
                _logger.warning(
                    'ODOO_QUERY: ignorado em "fields" (inexistente em %s): %s', Model._name, fname
                )
                continue
            field = Model._fields[fname]
            if field.compute and not field.store:
                _logger.warning(
                    'ODOO_QUERY: ignorado em "fields" (não armazenado em %s): %s', Model._name, fname
                )
                continue
            ok.append(fname)
        if not ok:
            return ['id', 'display_name']
        return ok

    def _normalize_search_read_order(self, Model, order):
        """Mantém apenas fragmentos ``campo asc|desc`` com campo existente no modelo."""
        if not order or not isinstance(order, str):
            return 'id desc'
        parts = []
        for fragment in order.split(','):
            frag = fragment.strip()
            if not frag:
                continue
            bits = frag.split()
            fname = bits[0]
            direction = bits[1].lower() if len(bits) > 1 else 'asc'
            if fname not in Model._fields:
                _logger.warning(
                    'ODOO_QUERY: ignorado fragmento de order (campo inexistente em %s): %s',
                    Model._name, fname,
                )
                continue
            if direction not in ('asc', 'desc'):
                direction = 'asc'
            parts.append('%s %s' % (fname, direction))
        joined = ', '.join(parts)
        if not joined or len(joined) > 120 or not re.match(r'^[\w\s\.,]+$', joined):
            return 'id desc'
        return joined

    def _llm_whitelisted_model_names_set(self):
        """Nomes técnicos permitidos em ODOO_QUERY e em links tipo ``form``."""
        icp = self.env['ir.config_parameter'].sudo()
        raw = icp.get_param('afr_llm_assistant.whitelisted_models') or ''
        allowed = {x.strip() for x in raw.split(',') if x.strip()}
        if not allowed:
            allowed = {'afr.supervisorio.ciclos'}
        return allowed

    def _llm_get_whitelisted_model(self, model_name):
        """Retorna o modelo do registry se estiver na whitelist de configuração."""
        model_name = (model_name or '').strip()
        if not model_name:
            raise UserError(_('ODOO_QUERY: campo "model" é obrigatório.'))
        allowed = self._llm_whitelisted_model_names_set()
        if model_name not in allowed:
            raise UserError(
                _('Modelo "%s" não está na lista de modelos permitidos nas configurações.') % model_name
            )
        if model_name not in self.env:
            raise UserError(_('Modelo "%s" não existe nesta base.') % model_name)
        return self.env[model_name]

    def _normalize_read_group_fields(self, Model, fields_list):
        """Campos permitidos em ``read_group``: ``__count``, nome armazenado ou ``campo:agregação``."""
        if not fields_list:
            return ['__count']
        if not isinstance(fields_list, (list, tuple)):
            raise UserError(_('ODOO_QUERY read_group: "fields" deve ser uma lista.'))
        out = []
        for item in fields_list[:15]:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if item == '__count':
                out.append('__count')
                continue
            if ':' in item:
                fname, agg = item.split(':', 1)
                fname, agg = fname.strip(), agg.strip().lower()
                if agg not in _SAFE_READ_GROUP_AGG or fname not in Model._fields:
                    continue
                fld = Model._fields[fname]
                if not fld.store and fname != 'id':
                    continue
                out.append('%s:%s' % (fname, agg))
            elif item in Model._fields:
                fld = Model._fields[item]
                if fld.store or item == 'id':
                    out.append(item)
        return out or ['__count']

    def _normalize_read_group_groupby(self, Model, groupby):
        """Até 5 campos armazenados existentes no modelo."""
        if not groupby:
            raise UserError(_('ODOO_QUERY read_group: "groupby" (lista de campos) é obrigatório.'))
        if not isinstance(groupby, (list, tuple)):
            raise UserError(_('ODOO_QUERY read_group: "groupby" deve ser uma lista.'))
        out = []
        for g in groupby[:5]:
            if not isinstance(g, str):
                continue
            g = g.strip()
            if not g or g not in Model._fields:
                _logger.warning('read_group: ignorado groupby inexistente em %s: %s', Model._name, g)
                continue
            fld = Model._fields[g]
            if not getattr(fld, 'store', False):
                _logger.warning('read_group: ignorado groupby não armazenado em %s: %s', Model._name, g)
                continue
            out.append(g)
        if not out:
            raise UserError(_('ODOO_QUERY read_group: nenhum campo em "groupby" é válido.'))
        return out

    def _safe_execute_odoo_operation(self, payload):
        """
        Executa operações de leitura permitidas (whitelist + validação de domínio).

        ``operation`` (opcional, padrão ``search_read``): ``search_read``,
        ``search_count``, ``search`` (retorna só ids), ``read_group``, ``fields_get``.
        """
        if not isinstance(payload, dict):
            raise UserError(_('O bloco ODOO_QUERY deve ser um objeto JSON.'))
        operation = (payload.get('operation') or 'search_read').strip().lower()
        Model = self._llm_get_whitelisted_model(payload.get('model'))

        try:
            if operation == 'search_read':
                self._sanitize_odoo_query_payload(Model, payload)
                domain = payload.get('domain') or []
                self._validate_domain_structure(Model._name, domain)
                limit = int(payload.get('limit') or 20)
                if limit < 1 or limit > 50:
                    raise UserError(_('ODOO_QUERY: "limit" deve estar entre 1 e 50.'))
                fields_list = payload.get('fields') or ['id', 'display_name']
                if not isinstance(fields_list, (list, tuple)):
                    raise UserError(_('ODOO_QUERY: "fields" deve ser uma lista de nomes de campos.'))
                order = payload.get('order') or 'id desc'
                if not isinstance(order, str):
                    raise UserError(_('ODOO_QUERY: "order" deve ser uma string.'))
                if len(order) > 120 or not re.match(r'^[\w\s\.,]+$', order):
                    raise UserError(_('ODOO_QUERY: "order" contém caracteres não permitidos.'))
                return Model.search_read(domain, fields=fields_list, limit=limit, order=order)

            if operation == 'search_count':
                work = dict(payload)
                self._sanitize_llm_domain_and_order(Model, work)
                domain = work.get('domain') or []
                self._validate_domain_structure(Model._name, domain)
                return Model.search_count(domain)

            if operation == 'search':
                work = dict(payload)
                self._sanitize_llm_domain_and_order(Model, work)
                domain = work.get('domain') or []
                self._validate_domain_structure(Model._name, domain)
                limit = int(payload.get('limit') or 80)
                if limit < 1 or limit > 200:
                    raise UserError(_('ODOO_QUERY search: "limit" deve estar entre 1 e 200.'))
                order = work.get('order') or 'id desc'
                if not isinstance(order, str):
                    raise UserError(_('ODOO_QUERY: "order" deve ser uma string.'))
                if len(order) > 120 or not re.match(r'^[\w\s\.,]+$', order):
                    raise UserError(_('ODOO_QUERY: "order" contém caracteres não permitidos.'))
                return Model.search(domain, limit=limit, order=order).ids

            if operation == 'read_group':
                work = dict(payload)
                self._sanitize_llm_domain_and_order(Model, work)
                domain = work.get('domain') or []
                self._validate_domain_structure(Model._name, domain)
                fields_rg = self._normalize_read_group_fields(Model, payload.get('fields'))
                groupby_list = self._normalize_read_group_groupby(Model, payload.get('groupby'))
                limit = int(payload.get('limit') or 80)
                if limit < 1 or limit > 200:
                    raise UserError(_('ODOO_QUERY read_group: "limit" deve estar entre 1 e 200.'))
                offset = int(payload.get('offset') or 0)
                if offset < 0 or offset > 10000:
                    raise UserError(_('ODOO_QUERY read_group: "offset" inválido (0–10000).'))
                orderby = payload.get('orderby', payload.get('order'))
                if orderby in (None, False, ''):
                    orderby = False
                elif isinstance(orderby, str):
                    if len(orderby) > 160 or not re.match(r'^[\w\s\.,]+$', orderby):
                        raise UserError(
                            _('ODOO_QUERY read_group: "orderby" contém caracteres não permitidos.')
                        )
                else:
                    raise UserError(_('ODOO_QUERY read_group: "orderby" deve ser string ou omitido.'))
                lazy = payload.get('lazy', True)
                if not isinstance(lazy, bool):
                    lazy = bool(lazy)
                return Model.read_group(
                    domain, fields_rg, groupby_list,
                    offset=offset, limit=limit, orderby=orderby, lazy=lazy,
                )

            if operation == 'fields_get':
                allfields = payload.get('fields')
                if not allfields or not isinstance(allfields, (list, tuple)):
                    raise UserError(_('ODOO_QUERY fields_get: "fields" (lista de nomes) é obrigatório.'))
                if len(allfields) > 80:
                    raise UserError(_('ODOO_QUERY fields_get: no máximo 80 campos.'))
                ok = [f for f in allfields if isinstance(f, str) and f in Model._fields]
                if not ok:
                    raise UserError(_('ODOO_QUERY fields_get: nenhum nome de campo válido.'))
                attributes = payload.get('attributes')
                if attributes is None:
                    attrs = ['string', 'type', 'required', 'readonly']
                elif isinstance(attributes, list):
                    attrs = [a for a in attributes if isinstance(a, str) and a in _SAFE_FIELDS_GET_ATTRS]
                    if not attrs:
                        attrs = ['string', 'type']
                else:
                    raise UserError(_('ODOO_QUERY fields_get: "attributes" deve ser uma lista ou omitida.'))
                return Model.fields_get(ok, attributes=attrs)

            raise UserError(
                _('ODOO_QUERY: "operation" inválida "%s". Use: fields_get, read_group, search, '
                  'search_count, search_read.') % operation
            )
        except UserError:
            raise
        except Exception as err:
            _logger.warning('ODOO_QUERY %s falhou em %s: %s', operation, Model._name, err)
            raise UserError(
                _('Consulta ao Odoo inválida ou não permitida: %s') % err
            ) from err

    def _safe_resolve_odoo_links(self, payload):
        """
        Resolve uma lista de pedidos de link com as permissões do usuário atual.

        O JSON deve ser ``{"links": [ {...}, ... ]}`` (máx. 15 itens). Cada objeto leva
        ``type``: ``form``, ``attachment``, ``report``, ``menu`` ou ``action``.
        Devolve lista de dicts com ``ok``, ``path`` (URL relativa), ``label``, ``type``.
        """
        if not isinstance(payload, dict):
            raise UserError(_('ODOO_LINK: o payload deve ser um objeto JSON.'))
        links = payload.get('links')
        if not isinstance(links, (list, tuple)) or not links:
            raise UserError(_('ODOO_LINK: chave "links" (lista não vazia) é obrigatória.'))
        if len(links) > 15:
            raise UserError(_('ODOO_LINK: no máximo 15 itens por bloco.'))
        allowed_models = self._llm_whitelisted_model_names_set()
        out = []
        for raw in links:
            if not isinstance(raw, dict):
                out.append({'ok': False, 'error': _('Item de link inválido (objeto esperado).')})
                continue
            try:
                out.append(self._resolve_odoo_link_one(raw, allowed_models))
            except (UserError, AccessError) as err:
                out.append({
                    'ok': False,
                    'error': err.args[0] if getattr(err, 'args', None) else str(err),
                    'type': raw.get('type'),
                })
            except Exception as err:
                _logger.warning('ODOO_LINK item: %s', err)
                out.append({'ok': False, 'error': str(err), 'type': raw.get('type')})
        return out

    def _resolve_odoo_link_one(self, item, allowed_models):
        """Resolve um único pedido de link; levanta UserError se inválido ou sem acesso."""
        ltype = (item.get('type') or '').strip().lower()
        if ltype == 'form':
            mname = (item.get('model') or '').strip()
            if mname not in allowed_models:
                raise UserError(_('LINK form: modelo "%s" não está na whitelist.') % mname)
            if mname not in self.env:
                raise UserError(_('Modelo inexistente: %s') % mname)
            rid = int(item.get('id') or 0)
            if rid < 1:
                raise UserError(_('LINK form: "id" inteiro positivo é obrigatório.'))
            rec = self.env[mname].browse(rid)
            if not rec.exists():
                raise UserError(_('Registo não encontrado.'))
            rec.check_access_rule('read')
            data = rec.read(['display_name'])
            label = (item.get('label') or '').strip() or (data[0].get('display_name') if data else '') or '#%s' % rid
            path = '/web#id=%s&model=%s&view_type=form' % (rid, mname)
            return {'ok': True, 'type': 'form', 'label': label, 'path': path}

        if ltype == 'attachment':
            aid = int(item.get('id') or 0)
            if aid < 1:
                raise UserError(_('LINK attachment: "id" do anexo é obrigatório.'))
            att = self.env['ir.attachment'].browse(aid)
            if not att.exists():
                raise UserError(_('Anexo não encontrado.'))
            att.check_access_rule('read')
            label = (item.get('label') or '').strip() or att.name or _('Anexo #%s') % aid
            path = '/web/content/%s?download=true' % aid
            return {'ok': True, 'type': 'attachment', 'label': label, 'path': path}

        if ltype == 'report':
            report_name = (item.get('report_name') or '').strip()
            if not report_name or not _REPORT_TECHNICAL_NAME_RE.match(report_name):
                raise UserError(
                    _('LINK report: "report_name" inválido (esperado formato módulo.nome_relatorio).')
                )
            ids_val = item.get('ids') or []
            if isinstance(ids_val, str):
                ids_list = [int(x) for x in ids_val.split(',') if x.strip().isdigit()]
            elif isinstance(ids_val, (list, tuple)):
                ids_list = []
                for x in ids_val[:50]:
                    try:
                        xi = int(x)
                        if xi > 0:
                            ids_list.append(xi)
                    except (TypeError, ValueError):
                        continue
            else:
                raise UserError(_('LINK report: "ids" deve ser lista de inteiros ou string "1,2,3".'))
            if not ids_list:
                raise UserError(_('LINK report: "ids" não pode ser vazio.'))
            report = self.env['ir.actions.report'].search(
                [('report_name', '=', report_name)], limit=1
            )
            if not report:
                raise UserError(_('Relatório "%s" não encontrado ou sem acesso.') % report_name)
            # O ``report_type`` do registo define que rotas existem (documentação Odoo 16).
            forced_conv = self._report_type_to_converter_hint(report.report_type)
            if forced_conv != '?':
                conv = forced_conv
            else:
                conv = (item.get('converter') or 'pdf').strip().lower()
                if conv not in ('pdf', 'html', 'text'):
                    conv = 'pdf'
            rmodel = report.model
            if rmodel not in self.env:
                raise UserError(_('Modelo do relatório inválido.'))
            R = self.env[rmodel].browse(ids_list)
            for r in R:
                if not r.exists():
                    raise UserError(_('Id %s inexistente no modelo do relatório.') % r.id)
            R.check_access_rule('read')
            docids = ','.join(str(i) for i in ids_list)
            path = '/report/%s/%s/%s' % (conv, report_name, docids)
            label = (item.get('label') or '').strip() or report.name or report_name
            return {'ok': True, 'type': 'report', 'label': label, 'path': path}

        if ltype == 'menu':
            mid = int(item.get('menu_id') or 0)
            if mid < 1:
                raise UserError(_('LINK menu: "menu_id" inteiro positivo é obrigatório.'))
            menu = self.env['ir.ui.menu'].search([('id', '=', mid)], limit=1)
            if not menu:
                raise UserError(_('Menu não encontrado ou invisível para o seu usuário.'))
            menu.check_access_rule('read')
            parts = ['menu_id=%s' % menu.id]
            if menu.action:
                parts.append('action=%s' % menu.action.id)
            path = '/web#%s' % '&'.join(parts)
            label = (item.get('label') or '').strip() or menu.name or _('Menu #%s') % mid
            return {'ok': True, 'type': 'menu', 'label': label, 'path': path}

        if ltype == 'action':
            act_id = int(item.get('action_id') or 0)
            if act_id < 1:
                raise UserError(_('LINK action: "action_id" é obrigatório.'))
            act = self.env['ir.actions.act_window'].search([('id', '=', act_id)], limit=1)
            if not act:
                raise UserError(_('Ação janela não encontrada ou sem acesso.'))
            act.check_access_rule('read')
            parts = ['action=%s' % act.id]
            res_model = (item.get('model') or '').strip() or None
            res_id_raw = item.get('id')
            if res_id_raw is not None:
                res_id = int(res_id_raw)
                if res_id < 1:
                    raise UserError(_('LINK action: "id" do registo inválido.'))
                m_use = res_model or act.res_model
                if not m_use:
                    raise UserError(_('LINK action: indique "model" ou use uma ação com res_model.'))
                if act.res_model and m_use != act.res_model:
                    raise UserError(_('LINK action: modelo não coincide com a ação.'))
                if m_use not in self.env:
                    raise UserError(_('Modelo inexistente.'))
                rec = self.env[m_use].browse(res_id)
                if not rec.exists():
                    raise UserError(_('Registo não encontrado.'))
                rec.check_access_rule('read')
                parts.append('model=%s' % m_use)
                parts.append('view_type=form')
                parts.append('id=%s' % res_id)
            path = '/web#%s' % '&'.join(parts)
            label = (item.get('label') or '').strip() or act.name or _('Ação #%s') % act_id
            return {'ok': True, 'type': 'action', 'label': label, 'path': path}

        raise UserError(
            _('LINK: "type" inválido "%s". Use: action, attachment, form, menu, report.') % (ltype or '?')
        )

    def _validate_domain_structure(self, model_name, domain):
        """Garante que o domínio é uma lista e que cada folha é uma tripla segura."""
        if not isinstance(domain, (list, tuple)):
            raise UserError(_('ODOO_QUERY: "domain" deve ser uma lista.'))
        Model = self.env[model_name]
        for item in domain:
            if isinstance(item, str) and item in ('&', '|', '!'):
                continue
            if isinstance(item, (list, tuple)) and len(item) == 3:
                fname, op, _val = item
                if fname not in Model._fields:
                    raise UserError(_('Domínio: campo "%s" inválido para o modelo "%s".') % (fname, model_name))
                if op not in _SAFE_DOMAIN_OPS:
                    raise UserError(_('Domínio: operador "%s" não é permitido.') % op)
                continue
            raise UserError(_('Domínio: elemento inválido: %r') % (item,))
