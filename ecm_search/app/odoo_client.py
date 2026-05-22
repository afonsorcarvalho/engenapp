import requests


class OdooClient:
    """Minimal Odoo JSON-RPC client (login + execute_kw)."""

    def __init__(self, url, db, user, password):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid = None

    def _call(self, service, method, args):
        resp = requests.post(
            f"{self.url}/jsonrpc",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"service": service, "method": method, "args": args},
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data["result"]

    def login(self):
        self.uid = self._call("common", "login", [self.db, self.user, self.password])
        if not self.uid:
            raise RuntimeError("Odoo login failed")
        return self.uid

    def execute_kw(self, model, method, args, kwargs=None):
        if self.uid is None:
            self.login()
        return self._call(
            "object",
            "execute_kw",
            [self.db, self.uid, self.password, model, method, args, kwargs or {}],
        )

    def search_read(self, model, domain, fields, **kwargs):
        return self.execute_kw(model, "search_read", [domain, fields], kwargs)

    def search(self, model, domain, **kwargs):
        return self.execute_kw(model, "search", [domain], kwargs)

    def get_config_param(self, key, default=None):
        """Read an ir.config_parameter; returns `default` if unset/unreachable."""
        try:
            value = self.execute_kw("ir.config_parameter", "get_param", [key])
        except Exception:
            return default
        return value if value not in (False, None, "") else default
