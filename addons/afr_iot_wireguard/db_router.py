"""Patch Odoo HTTP layer to resolve target DB from the X-Odoo-Db header.

Multi-DB deployments without a dbfilter would otherwise 404 on auth='none'
routes because Odoo cannot infer the DB from a cookieless IoT request.
This module is loaded via `server_wide_modules` so the patch is in place
before any request is dispatched.
"""

import logging

from odoo import http

_logger = logging.getLogger(__name__)

_original_get_session_and_dbname = http.Request._get_session_and_dbname


def _get_session_and_dbname_with_header(self):
    session, dbname = _original_get_session_and_dbname(self)
    if dbname:
        return session, dbname

    requested = self.httprequest.headers.get('X-Odoo-Db')
    if not requested:
        return session, dbname

    host = self.httprequest.environ.get('HTTP_HOST', '')
    try:
        available = http.db_list(force=True, host=host)
    except Exception:
        available = []

    if requested in available:
        session.db = requested
        return session, requested

    _logger.warning("X-Odoo-Db header %r not in available DBs (%s)", requested, available)
    return session, dbname


http.Request._get_session_and_dbname = _get_session_and_dbname_with_header
_logger.info("afr_iot_wireguard: X-Odoo-Db header routing enabled")
