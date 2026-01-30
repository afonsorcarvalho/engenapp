#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para procurar caracteres inválidos em XML no módulo engc_os.

Em XML, caracteres de controle (exceto tab 0x09, newline 0x0a, carriage return 0x0d)
são inválidos em PCDATA. O erro "PCDATA invalid Char value 12" indica o form feed (0x0c).

Uso no servidor (a partir do diretório engc_os ou do repositório):
  python3 check_xml_invalid_chars.py
  python3 engc_os/check_xml_invalid_chars.py
"""

import os
import sys

# Caracteres de controle inválidos em XML (exceto 0x09 tab, 0x0a NL, 0x0d CR)
INVALID_CONTROL_CODES = frozenset(
    range(0x00, 0x09)  # 0x00-0x08
) | frozenset((0x0B, 0x0C)) | frozenset(
    range(0x0E, 0x20)  # 0x0e-0x1f
)

# Nomes conhecidos para exibição
CHAR_NAMES = {
    0x00: "NUL",
    0x01: "SOH",
    0x02: "STX",
    0x03: "ETX",
    0x04: "EOT",
    0x05: "ENQ",
    0x06: "ACK",
    0x07: "BEL",
    0x08: "BS",
    0x0B: "VT (vertical tab)",
    0x0C: "FF (form feed) <- valor 12 do erro",
    0x0E: "SO",
    0x0F: "SI",
    0x1A: "SUB",
    0x1B: "ESC",
}


def line_col_for_offset(data: bytes, offset: int):
    """Retorna (linha, coluna) 1-based para o byte em offset."""
    line, col = 1, 1
    for i in range(offset):
        if data[i] == 0x0A:
            line += 1
            col = 1
        else:
            col += 1
    return line, col


def scan_file(filepath: str):
    """
    Retorna lista de (offset, byte_value, line, col, context_end).
    context_end = offset + 1 para exibir 1 byte de contexto.
    """
    results = []
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except OSError as e:
        return [(-1, -1, -1, -1, -1)]  # sinal de erro de leitura

    for i, b in enumerate(data):
        if b in INVALID_CONTROL_CODES:
            line, col = line_col_for_offset(data, i)
            name = CHAR_NAMES.get(b, f"char {b}")
            results.append((i, b, line, col, 1))
    return results


def main():
    # Diretório do script = raiz do módulo engc_os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    total_issues = 0
    files_with_issues = []

    for root, _dirs, files in os.walk("."):
        for name in files:
            if not name.endswith(".xml"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            if path.startswith("./"):
                path = path[2:]
            issues = scan_file(path)
            if not issues:
                continue
            if issues[0][0] == -1:
                print(f"[ERRO leitura] {path}", file=sys.stderr)
                continue
            total_issues += len(issues)
            files_with_issues.append((path, issues))

    if not files_with_issues:
        print("Nenhum caractere de controle inválido encontrado nos XML do engc_os.")
        return 0

    print("Caracteres de controle inválidos em XML (PCDATA invalid):\n")
    for path, issues in files_with_issues:
        print(f"  Arquivo: {path}")
        for offset, b, line, col, _ in issues:
            name = CHAR_NAMES.get(b, f"char {b}")
            print(f"    -> byte {offset}, linha {line}, coluna {col}: 0x{b:02X} ({name})")
        print()
    print(f"Total: {total_issues} ocorrência(s) em {len(files_with_issues)} arquivo(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
