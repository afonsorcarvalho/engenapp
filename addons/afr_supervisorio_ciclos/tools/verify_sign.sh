#!/bin/bash
# FITADIGITAL
# Autor: Afonso Carvalho
# Versão: 1.2
#
# Script para verificar assinaturas digitais usando OpenSSL
# Uso: ./verify_sign.sh arquivo.txt chave_publica.pem

# Verifica se os argumentos foram fornecidos
if [ $# -ne 2 ]; then
    echo "Uso: $0 arquivo.txt chave_publica.pem"
    exit 1
fi

ARQUIVO="$1"
CHAVE_PUBLICA="$2"

# Verifica se o arquivo existe
if [ ! -f "$ARQUIVO" ]; then
    echo "Erro: Arquivo '$ARQUIVO' não encontrado"
    exit 1
fi

# Verifica se a chave pública existe
if [ ! -f "$CHAVE_PUBLICA" ]; then
    echo "Erro: Chave pública '$CHAVE_PUBLICA' não encontrada"
    exit 1
fi

# Cria arquivos temporários
TEMP_CONTENT_RAW=$(mktemp) # Conteúdo bruto extraído
TEMP_CONTENT_NORMALIZED=$(mktemp) # Conteúdo normalizado para verificação
TEMP_SIG=$(mktemp)
TEMP_SIG_BIN=$(mktemp)

# Extrai o conteúdo e a assinatura
awk -v content="$TEMP_CONTENT_RAW" -v sig="$TEMP_SIG" '
    BEGIN { in_sign = 0; }
    /^-----BEGIN SIGN-----$/ { in_sign = 1; next; }
    /^-----END SIGN-----$/ { in_sign = 0; next; }
    { if (!in_sign) print > content; else print > sig; }
' "$ARQUIVO"

# Normaliza o conteúdo extraído da mesma forma que no script de assinatura
cat "$TEMP_CONTENT_RAW" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}' > "$TEMP_CONTENT_NORMALIZED"
rm "$TEMP_CONTENT_RAW"

# Debug: Mostra o conteúdo extraído e normalizado
echo "Conteúdo extraído e normalizado para verificação:"
cat "$TEMP_CONTENT_NORMALIZED"
echo "---"

# Debug: Mostra a assinatura extraída
echo "Assinatura extraída:"
cat "$TEMP_SIG"
echo "---"

# Verifica se a assinatura foi encontrada
if [ ! -s "$TEMP_SIG" ]; then
    echo "Erro: Assinatura não encontrada no arquivo"
    rm "$TEMP_CONTENT_NORMALIZED" "$TEMP_SIG" "$TEMP_SIG_BIN"
    exit 1
fi

# Remove quebras de linha da assinatura base64
tr -d '\n' < "$TEMP_SIG" > "${TEMP_SIG}.tmp"
mv "${TEMP_SIG}.tmp" "$TEMP_SIG"

# Decodifica a assinatura base64
base64 -d "$TEMP_SIG" > "$TEMP_SIG_BIN"

# Debug: Mostra o tamanho da assinatura decodificada
#echo "Tamanho da assinatura decodificada: $(wc -c < "$TEMP_SIG_BIN") bytes"

# Debug: Mostra a assinatura em hexadecimal
#echo "Assinatura em hexadecimal:"
#xxd -p "$TEMP_SIG_BIN"#
#echo "---"

# Verifica a assinatura usando o conteúdo normalizado
if openssl dgst -sha256 -verify "$CHAVE_PUBLICA" -signature "$TEMP_SIG_BIN" "$TEMP_CONTENT_NORMALIZED"; then
    echo "Assinatura válida!"
    rm "$TEMP_CONTENT_NORMALIZED" "$TEMP_SIG" "$TEMP_SIG_BIN"
    exit 0
else
    echo "Assinatura inválida!"
    echo "Detalhes do erro:"
    openssl dgst -sha256 -verify "$CHAVE_PUBLICA" -signature "$TEMP_SIG_BIN" "$TEMP_CONTENT_NORMALIZED" 2>&1
    rm "$TEMP_CONTENT_NORMALIZED" "$TEMP_SIG" "$TEMP_SIG_BIN"
    exit 1
fi 