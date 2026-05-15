#!/usr/bin/env bash
# Baixa modelos LLM no container ollama.
#
# Modelos escolhidos para VPS CPU <16GB RAM:
#   - qwen2.5:3b-instruct-q4_K_M   ~2GB, melhor PT-BR no porte 3B
#
# Opcionais (descomentar conforme RAM disponível):
#   - llama3.2:3b-instruct-q4_K_M  ~2GB, alternativa
#   - qwen2.5:7b-instruct-q4_K_M   ~4.5GB, melhor qualidade, mais lento
set -euo pipefail

CONTAINER="${OLLAMA_CONTAINER:-ollama}"

echo ">> Aguardando ollama responder..."
for i in $(seq 1 30); do
    if docker exec "$CONTAINER" ollama list >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo ">> Pull qwen2.5:3b-instruct-q4_K_M"
docker exec "$CONTAINER" ollama pull qwen2.5:3b-instruct-q4_K_M

# docker exec "$CONTAINER" ollama pull llama3.2:3b-instruct-q4_K_M
# docker exec "$CONTAINER" ollama pull qwen2.5:7b-instruct-q4_K_M

echo ">> Modelos disponíveis:"
docker exec "$CONTAINER" ollama list

echo ">> Smoke test (chat completion):"
curl -s http://127.0.0.1:11434/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen2.5:3b-instruct-q4_K_M",
        "messages": [{"role": "user", "content": "Diga olá em uma frase curta."}],
        "max_tokens": 32
    }' | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r["choices"][0]["message"]["content"])'
