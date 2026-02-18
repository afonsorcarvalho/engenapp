# -*- coding: utf-8 -*-
"""
Cliente FCM HTTP v1 para envio de mensagens data-only.
Utiliza OAuth2 com Service Account (Google Auth) e requests.
Documentação: https://firebase.google.com/docs/cloud-messaging/send-message
"""
import json
import logging
import os

from odoo import _, fields

_logger = logging.getLogger(__name__)


def format_datetime_for_fcm(record, dt, user=None):
    """
    Converte dt (UTC, armazenado no banco) para o fuso horário do usuário e formata (dd/mm/yyyy HH:MM).
    Usado nas notificações FCM para que cada destinatário veja a data no seu fuso.
    :param record: registro com .env
    :param dt: datetime em UTC (naive) ou None
    :param user: res.users destinatário; se None, usa record.env.user
    :return: string formatada ou ''
    """
    if not dt:
        return ''
    try:
        if user is not None:
            record = record.with_env(record.env(user=user))
        local_dt = fields.Datetime.context_timestamp(record, dt)
        return local_dt.strftime('%d/%m/%Y %H:%M')
    except Exception as e:
        _logger.debug("FCM: fallback format_datetime sem TZ para %s: %s", dt, e)
        return dt.strftime('%d/%m/%Y %H:%M')

# Escopo necessário para FCM (documentação Firebase)
FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
FCM_URL_TEMPLATE = 'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'


def _get_credentials(env):
    """
    Obtém credenciais do Service Account a partir da configuração Odoo ou variável de ambiente.
    Ordem: ir.config_parameter engc_fcm.service_account_json (JSON string),
           engc_fcm.service_account_path (caminho do arquivo),
           variável de ambiente GOOGLE_APPLICATION_CREDENTIALS (caminho).
    """
    try:
        from google.oauth2 import service_account
    except ImportError:
        _logger.warning(
            "google-auth não instalado. Para envio FCM instale: pip install google-auth"
        )
        return None

    IrConfig = env['ir.config_parameter'].sudo()
    # 1) JSON direto no parâmetro
    json_str = IrConfig.get_param('engc_fcm.service_account_json', default='')
    if json_str and json_str.strip():
        try:
            info = json.loads(json_str)
            return service_account.Credentials.from_service_account_info(
                info, scopes=[FCM_SCOPE]
            )
        except (json.JSONDecodeError, ValueError) as e:
            _logger.warning("engc_fcm.service_account_json inválido: %s", e)
            return None

    # 2) Caminho no parâmetro ou em variável de ambiente
    path = IrConfig.get_param('engc_fcm.service_account_path', default='') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
    if path and os.path.isfile(path):
        try:
            return service_account.Credentials.from_service_account_file(
                path, scopes=[FCM_SCOPE]
            )
        except Exception as e:
            _logger.warning("Erro ao carregar Service Account de %s: %s", path, e)
            return None

    _logger.info(
        "FCM: Service Account não encontrado. JSON em ir.config_parameter tem %s caracteres; "
        "caminho configurado: %s; arquivo existe: %s.",
        len(json_str or ''),
        bool(path),
        os.path.isfile(path) if path else False,
    )
    return None


def _get_project_id(env, credentials):
    """Obtém project_id do JSON do Service Account ou do parâmetro engc_fcm.project_id."""
    if credentials is None:
        return None
    # Credentials from service account info/file têm project_id
    project_id = getattr(credentials, 'project_id', None)
    if project_id:
        return project_id
    return env['ir.config_parameter'].sudo().get_param('engc_fcm.project_id', default='')


def get_access_token(env):
    """
    Obtém access token OAuth2 para FCM.
    :return: token string ou None se não configurado/falha
    """
    credentials = _get_credentials(env)
    if credentials is None:
        return None
    try:
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        _logger.warning("Falha ao obter access token FCM: %s", e)
        return None


def send_fcm_data_message(env, fcm_token, data_dict, project_id=None):
    """
    Envia uma mensagem FCM data-only (HTTP v1).
    Todos os valores em data_dict devem ser strings (exigência da API FCM).

    :param env: ambiente Odoo (env)
    :param fcm_token: token do dispositivo FCM
    :param data_dict: dict com chaves/valores string (ex.: type, request_service_id, title, body)
    :param project_id: opcional; se não informado, usa credenciais ou ir.config_parameter
    :return: tupla (sucesso: bool, detalhe: str | None). Em falha, detalhe traz status e corpo da resposta para exibir ao usuário.
    """
    if not fcm_token or not isinstance(data_dict, dict):
        _logger.debug("send_fcm_data_message: token ou data inválidos.")
        return False, _("Token ou payload inválidos.")

    credentials = _get_credentials(env)
    if credentials is None:
        msg = _("Service Account não configurado. Configure em Configurações > Geral > Push (FCM).")
        _logger.warning("FCM: %s", msg)
        return False, msg

    pid = project_id or _get_project_id(env, credentials)
    if not pid:
        msg = _("Project ID não definido. Preencha no Push (FCM) ou use um JSON com project_id.")
        _logger.warning("FCM: %s", msg)
        return False, msg

    token = get_access_token(env)
    if not token:
        msg = _("Não foi possível obter access token. Verifique o JSON do Service Account (chave privada e client_email).")
        _logger.warning("FCM: %s", msg)
        return False, msg

    _logger.info("FCM: [OAUTH] access token obtido (Bearer ...%s)", (token or '')[-8:] if token else '')

    # Garantir que todos os valores em data são string (requisito FCM)
    data_str = {k: (v if isinstance(v, str) else str(v)) for k, v in data_dict.items()}

    url = FCM_URL_TEMPLATE.format(project_id=pid)
    headers = {
        'Authorization': 'Bearer %s' % token,
        'Content-Type': 'application/json; UTF-8',
    }
    # Incluir "notification" para o sistema exibir a notificação quando o app está em segundo plano ou fechado.
    # Mantemos "data" para o app usar (type, request_service_id, etc.).
    message_payload = {
        'token': fcm_token,
        'data': data_str,
        'fcm_options': {'analytics_label': 'odoo_engc'},
    }
    notif_title = data_str.get('title') or ''
    notif_body = data_str.get('body') or ''
    if notif_title or notif_body:
        message_payload['notification'] = {
            'title': notif_title[:100],
            'body': (notif_body[:200]) if notif_body else notif_title[:200],
        }
    body = {'message': message_payload}

    body_json = json.dumps(body)

    # Log completo da comunicação com o Firebase (token mascarado no log)
    body_log = {'message': {'token': (fcm_token or '')[:30] + '...[MASKED]' if fcm_token and len(fcm_token) > 30 else (fcm_token or ''), 'data': data_str, 'fcm_options': message_payload['fcm_options']}}
    if 'notification' in message_payload:
        body_log['message']['notification'] = message_payload['notification']
    _logger.info(
        "FCM: [REQUEST] POST %s",
        url,
    )
    _logger.info(
        "FCM: [REQUEST HEADERS] Content-Type=application/json; UTF-8, Authorization=Bearer ***",
    )
    _logger.info(
        "FCM: [REQUEST BODY] %s",
        json.dumps(body_log, ensure_ascii=False),
    )

    try:
        import requests
        resp = requests.post(url, headers=headers, data=body_json, timeout=10)

        _logger.info(
            "FCM: [RESPONSE] status=%s | url=%s",
            resp.status_code,
            url,
        )
        _logger.info(
            "FCM: [RESPONSE BODY] %s",
            (resp.text or '(vazio)')[:1000],
        )

        if resp.status_code == 200:
            _logger.info(
                "FCM: mensagem aceita pelo Firebase (HTTP 200). token_prefix=%s... "
                "Se não aparecer no celular: app em primeiro plano precisa tratar onMessage e exibir notificação local.",
                (fcm_token or '')[:24],
            )
            return True, None

        # Montar detalhe para o usuário (ex.: 401 = credenciais; 403 = SENDER_ID_MISMATCH)
        body_preview = (resp.text or '')[:400]
        _logger.warning(
            "FCM: envio falhou | status=%s | body=%s",
            resp.status_code,
            resp.text[:500] if resp.text else '',
        )
        try:
            err_json = resp.json()
            err_msg = err_json.get('error', {}).get('message', body_preview)
            details = err_json.get('error', {}).get('details', [])
            if details and isinstance(details[0], dict):
                err_code = details[0].get('errorCode', '')
                if err_code:
                    err_msg = '%s (%s)' % (err_msg, err_code)
        except Exception:
            err_msg = body_preview or 'HTTP %s' % resp.status_code
        detail = _("FCM retornou %(status)s: %(message)s") % {'status': resp.status_code, 'message': err_msg}
        return False, detail
    except Exception as e:
        _logger.warning("FCM exceção ao enviar: %s", e, exc_info=True)
        return False, str(e)
