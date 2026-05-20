#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch para Odoo 16: evita AttributeError quando não há request HTTP
( ex.: ao carregar o registry na subida do servidor ).
Arquivo: addons/website/models/ir_module_module.py
Bug: request.context acessado quando request._get_current_object() é None.
"""
import os
import sys

# Caminhos possíveis do arquivo (venv ou sistema; Debian/Ubuntu)
BASE_PATHS = [
    "/usr/lib/python3/dist-packages/odoo/addons/website/models",
    "/opt/odoo/venv/lib/python3.9/site-packages/odoo/addons/website/models",
    "/opt/odoo/venv/lib/python3.10/site-packages/odoo/addons/website/models",
    "/usr/local/lib/python3.9/dist-packages/odoo/addons/website/models",
]

FILENAME = "ir_module_module.py"

# Bloco problemático: "if" + linha do corpo (self = self.with_context...)
# Incluímos o corpo no replace para manter indentação correta.
OLD_VARIANTS = [
    # 4 espaços no if, 8 no body
    ("    if request and request.db and request.context.get('apply_new_theme'):\n        self = self.with_context(apply_new_theme=True)", "4"),
    # 1 espaço no if, 1 no body (formato Debian/Odoo em /usr/lib)
    (" if request and request.db and request.context.get('apply_new_theme'):\n self = self.with_context(apply_new_theme=True)", "1"),
    # 8 espaços
    ("        if request and request.db and request.context.get('apply_new_theme'):\n            self = self.with_context(apply_new_theme=True)", "8"),
]

# Blocos corrigidos: try/except/if + body com mesma indentação do método
NEW_BLOCK_4 = """    try:
        _req = request._get_current_object() if hasattr(request, '_get_current_object') else request
    except Exception:
        _req = None
    if _req is not None and getattr(_req, 'db', None) and getattr(_req, 'context', None) and _req.context.get('apply_new_theme'):
        self = self.with_context(apply_new_theme=True)"""

NEW_BLOCK_1 = """ try:
        _req = request._get_current_object() if hasattr(request, '_get_current_object') else request
    except Exception:
        _req = None
    if _req is not None and getattr(_req, 'db', None) and getattr(_req, 'context', None) and _req.context.get('apply_new_theme'):
        self = self.with_context(apply_new_theme=True)"""

NEW_BLOCK_8 = """        try:
            _req = request._get_current_object() if hasattr(request, '_get_current_object') else request
        except Exception:
            _req = None
        if _req is not None and getattr(_req, 'db', None) and getattr(_req, 'context', None) and _req.context.get('apply_new_theme'):
            self = self.with_context(apply_new_theme=True)"""


def main():
    path = None
    for base in BASE_PATHS:
        p = os.path.join(base, FILENAME)
        if os.path.isfile(p):
            path = p
            break
    if not path:
        print("patch_website_request: arquivo ir_module_module.py não encontrado.", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Patch já aplicado corretamente (corpo do if com indentação correta)
    if "_req = request._get_current_object()" in content and "apply_new_theme=True)" in content and "\n        self = self.with_context" in content:
        print("patch_website_request: patch já aplicado.")
        sys.exit(0)

    # Corrige patch anterior que deixou " self = self..." com indentação errada
    BROKEN_PATCH = """    if _req is not None and getattr(_req, 'db', None) and getattr(_req, 'context', None) and _req.context.get('apply_new_theme'):
 self = self.with_context(apply_new_theme=True)"""
    FIXED_TAIL = """    if _req is not None and getattr(_req, 'db', None) and getattr(_req, 'context', None) and _req.context.get('apply_new_theme'):
        self = self.with_context(apply_new_theme=True)"""
    if BROKEN_PATCH in content:
        content = content.replace(BROKEN_PATCH, FIXED_TAIL, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("patch_website_request: indentação do corpo do if corrigida.")
        sys.exit(0)

    blocks = {"1": NEW_BLOCK_1, "4": NEW_BLOCK_4, "8": NEW_BLOCK_8}
    changed = False
    for old, indent_key in OLD_VARIANTS:
        if old in content:
            content = content.replace(old, blocks[indent_key], 1)
            changed = True
            break

    if not changed:
        print("patch_website_request: padrão não encontrado; linha pode ter mudado.", file=sys.stderr)
        sys.exit(2)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("patch_website_request: aplicado com sucesso em", path)
    sys.exit(0)


if __name__ == "__main__":
    main()
