FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
# torch CPU-only primeiro (wheel ~190MB vs ~800MB do default CUDA) —
# evita timeout de download em conexões lentas. Serviço roda só em CPU.
RUN pip install --no-cache-dir --timeout 300 --retries 10 \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --timeout 300 --retries 10 -r requirements.txt

# Pré-baixa o modelo de embedding na imagem (camada cacheada)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY app ./app

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
