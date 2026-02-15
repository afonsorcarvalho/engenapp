# -*- coding: utf-8 -*-
"""
Cliente FCM HTTP v1 para envio de mensagens data-only.
Utiliza OAuth2 com Service Account (Google Auth) e requests.
Documentação: https://firebase.google.com/docs/cloud-messaging/send-message
"""
import json
import logging
import os

_logger = logging.getLogger(__name__)

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
    :return: True se enviado com sucesso, False caso contrário (erro logado)
    """
    if not fcm_token or not isinstance(data_dict, dict):
        _logger.debug("send_fcm_data_message: token ou data inválidos.")
        return False

    credentials = _get_credentials(env)
    if credentials is None:
        _logger.warning("FCM não configurado: Service Account ausente. Configure em Configurações > Geral > Push (FCM).")
        return False

    pid = project_id or _get_project_id(env, credentials)
    if not pid:
        _logger.warning("FCM: project_id não definido (configure engc_fcm.project_id ou use JSON com project_id).")
        return False

    token = get_access_token(env)
    if not token:
        _logger.warning("FCM: não foi possível obter access token (verifique o JSON do Service Account).")
        return False

    # Garantir que todos os valores em data são string (requisito FCM)
    data_str = {k: (v if isinstance(v, str) else str(v)) for k, v in data_dict.items()}

    url = FCM_URL_TEMPLATE.format(project_id=pid)
    headers = {
        'Authorization': 'Bearer %s' % token,
        'Content-Type': 'application/json; UTF-8',
    }
    body = {
        'message': {
            'token': fcm_token,
            'data': data_str,
        }
    }

    try:
        import requests
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        if resp.status_code == 200:
            _logger.info(
                "FCM enviado com sucesso (user token prefix: %s...). "
                "Se o dispositivo não exibir: app em primeiro plano pode precisar mostrar notificação local.",
                (fcm_token or '')[:30]
            )
            return True
        _logger.warning(
            "FCM falhou: status=%s, body=%s",
            resp.status_code,
            resp.text[:500] if resp.text else ''
        )
        return False
    except Exception as e:
        _logger.warning("FCM exceção ao enviar: %s", e, exc_info=True)
        return False
