#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica se a view da OS (engc.os form) no BANCO tem caracteres inválidos (ex: 0x0c).

O erro "PCDATA invalid Char value 12" pode vir da cópia da view em ir.ui.view,
não dos arquivos XML. Use este script dentro do Odoo shell no servidor.

Uso no servidor (com Odoo no PATH e variável de ambiente da base):
  odoo shell -d NOME_DA_BASE -c /caminho/odoo.conf

  Depois, no shell:
  >>> exec(open('engc_os/check_view_in_db.py').read())

  Ou rodar o conteúdo manualmente (ver trecho abaixo).
"""

# --- Cole isto no Odoo shell (ou exec(open('...').read())) ---

INVALID_CONTROL = set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20))

# Buscar a view do formulário engc.os (xml_id engc_os.form)
View = env["ir.ui.view"]
view = env.ref("engc_os.form", raise_if_not_found=False)
if not view:
    print("View engc_os.form não encontrada.")
else:
    # Odoo usa arch ou arch_db conforme versão
    arch_content = getattr(view, "arch_db", None) or getattr(view, "arch", None) or ""
    if isinstance(arch_content, bytes):
        data = arch_content
    else:
        data = arch_content.encode("utf-8") if arch_content else b""
    issues = []
    for i, b in enumerate(data):
        if b in INVALID_CONTROL:
            # Calcular linha/coluna aproximada
            line = data[:i].count(b"\n") + 1
            last_nl = data[:i].rfind(b"\n")
            col = (i - last_nl) if last_nl >= 0 else i + 1
            issues.append((i, b, line, col))
    if issues:
        print(f"View id={view.id} ({view.name}): {len(issues)} caractere(s) inválido(s)")
        for pos, b, line, col in issues[:20]:
            print(f"  -> byte {pos}, linha ~{line}, col ~{col}: 0x{b:02X} (char {b})")
        if len(issues) > 20:
            print(f"  ... e mais {len(issues) - 20}")
    else:
        print("Nenhum caractere inválido na view engc_os.form no banco.")
