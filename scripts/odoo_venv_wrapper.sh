#!/bin/bash
# Wrapper para o Odoo: usa Python do sistema (módulo odoo) e PYTHONPATH do venv (google-auth, cryptography).
# Copiado para /opt/odoo/venv/bin/odoo pelo Dockerfile.
# Usar /usr/bin/odoo (launcher do .deb); python3 -m odoo falha pois o pacote não tem __main__.
export PYTHONPATH="$(/opt/odoo/venv/bin/python3 -c "import site; print(site.getsitepackages()[0])")"
exec /usr/bin/odoo "$@"
