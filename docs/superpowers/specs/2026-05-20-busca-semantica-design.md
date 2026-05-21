# Busca Semântica — Design (v1)

Data: 2026-05-20
Status: aprovado (brainstorming)

## Contexto

ECM para empresa brasileira. afr_ecm (Odoo 16) já faz OCR (`dms.file.ocr_text`),
keywords YAKE (`dms.file.keywords`), entidades spaCy (`dms.file.entities`) e
classificação Groq (`afr.ecm.ai.suggestion`). ecm_desktop (Electron + Next.js)
consome o Odoo via JSON-RPC.

Nova feature: busca em linguagem natural — usuário digita
*"notas fiscais de compra do mês 03 de 2025"* e recebe documentos rankeados por
similaridade semântica.

## Escopo v1

- Microserviço dedicado de indexação + busca semântica.
- Indexação automática por pull (cron) dos documentos com OCR concluído.
- Extração de mês/ano do conteúdo OCR (regex pt-BR).
- Busca semântica padrão (similaridade pura) + modo "Busca com IA" (Groq parseia
  a query em filtros estruturados).
- UI de busca no ecm_desktop.

### Não-escopo (futuro)

- RAG / responder perguntas sobre o conteúdo (v2).
- OCR e extração de keywords (já existem no afr_ecm).
- Campo `subtipo` (compra/venda/serviço): afr_ecm não tem; tratado como keyword
  no embedding, não como filtro rígido.
- Watch via `bus.bus` do Odoo: avaliado e descartado (exigiria mudança no
  afr_ecm e consumidor longpolling frágil; cron pull é suficiente).

## Arquitetura

Novo container `ecm-search` no `docker-compose.yml`. Containers atuais:
`web`, `ocr_worker`, `db` (postgres12), `pgadmin`.

```
                  ┌─────────────────────────────────────────┐
                  │  ecm-search (container, sem porta pública)│
   cron pull ◄────┤  FastAPI + APScheduler                   │
   JSON-RPC       │  ChromaDB persistente (volume)            │
       │          │  sentence-transformers (multilingual)     │
       │          │  cliente Groq                             │
       ▼          └───────────────▲──────────────────────────┘
   ┌────────┐                     │ HTTP /search (token)
   │ Odoo   │                     │
   │ web    │◄──── controller afr_ecm /afr_ecm/semantic_search │
   └────────┘            (auth='user', proxy + ACL)           │
       ▲                          ▲
       │ JSON-RPC                  │ HTTP via ecm-api.ts
       │                  ┌────────┴────────┐
       └──────────────────┤  ecm_desktop UI │
                          └─────────────────┘
```

### Fluxo de indexação (cron pull)

1. APScheduler dispara a cada `SYNC_INTERVAL_MIN` minutos.
2. JSON-RPC ao Odoo (conta de serviço): `search_read` em `dms.file` com
   `ocr_state='done'` e `write_date > checkpoint`.
3. Por documento, lê: `ocr_text`, `keywords`, `entities`, `document_type_id`,
   `directory_id`, `ocr_content_hash`, `name`, `write_date`.
4. Extrai mês/ano do `ocr_text` via regex pt-BR.
5. Monta texto de embedding, gera vetor (sentence-transformers), `upsert` no
   ChromaDB. `ocr_content_hash` evita re-embeddar documento inalterado.
6. A cada `RECONCILE_EVERY` ciclos: puxa todos os ids ativos do Odoo e remove do
   ChromaDB ids ausentes (documentos apagados / na lixeira).
7. Atualiza checkpoint = maior `write_date` processado.

### Fluxo de busca

1. ecm_desktop → `POST /afr_ecm/semantic_search` `{query, ai_mode}`.
2. Controller afr_ecm valida sessão Odoo, repassa `POST /search` ao microserviço
   com header de token.
3. Microserviço:
   - Sempre: roda a query pelo mesmo extrator regex de data → filtro mês/ano.
   - Se `ai_mode`: chama Groq para parsear a query → `tipo_documento`,
     `entidades`, `keywords_adicionais`. `mes`/`ano` do Groq sobrescrevem o
     regex; `tipo_documento`/`keywords_adicionais`/`entidades` são anexados ao
     texto da query antes do embedding (sinal soft, não filtro rígido — o slug
     do Groq não casa com os nomes livres de `document_type_id`).
   - Monta where-clause ChromaDB só com `mes`/`ano` (`$and` se ambos presentes).
   - Gera embedding da query, `collection.query` com filtros + cosine.
   - Retorna `[{dms_file_id, score, tipo, mes, ano, arquivo}]`.
4. Controller afr_ecm: `dms.file.browse(ids)` no env do usuário → descarta sem
   permissão (ACL), enriquece com nome/pasta/mimetype vivos.
5. ecm_desktop renderiza resultados rankeados; clique abre `FilePreviewModal`.

## Componente 1 — microserviço `ecm-search`

Diretório novo no monorepo: `ecm_search/`.

```
ecm_search/
├── Dockerfile
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, rotas /search /healthz, startup
│   ├── config.py        # leitura de env vars
│   ├── odoo_client.py   # JSON-RPC ao Odoo (login + call_kw)
│   ├── embedder.py      # wrapper sentence-transformers
│   ├── store.py         # wrapper ChromaDB (upsert, query, delete, ids)
│   ├── state.py         # checkpoint + contador reconcile (SQLite)
│   ├── date_extract.py  # regex pt-BR mês/ano
│   ├── indexer.py       # monta texto de embedding + indexa doc
│   ├── sync.py          # job de pull + reconcile (APScheduler)
│   ├── groq_parser.py   # parse opcional da query via Groq
│   └── search.py        # lógica de busca (filtros + query Chroma)
└── tests/
    ├── test_date_extract.py
    ├── test_indexer.py
    ├── test_search.py
    └── test_groq_parser.py
```

### Config (env vars)

| Var | Default | Descrição |
|---|---|---|
| `ODOO_URL` | `http://web:8069` | URL interna do Odoo |
| `ODOO_DB` | — | nome do banco |
| `ODOO_USER` | — | login da conta de serviço |
| `ODOO_PASSWORD` | — | senha da conta de serviço |
| `GROQ_API_KEY` | — | chave Groq |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | modelo de parse |
| `SEARCH_TOKEN` | — | token compartilhado p/ `/search` |
| `SYNC_INTERVAL_MIN` | `5` | intervalo do pull |
| `RECONCILE_EVERY` | `12` | reconcile a cada N ciclos |
| `EMBED_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | modelo de embedding |
| `CHROMA_PATH` | `/data/chroma` | volume persistente |
| `TOP_K` | `10` | resultados por busca |

### Extração de data (`date_extract.py`)

Regex pt-BR sobre o texto OCR. Padrões:
- `dd/mm/aaaa`, `dd-mm-aaaa`, `dd.mm.aaaa`
- `mm/aaaa`
- nomes de mês: `janeiro|fevereiro|...|dezembro` seguido de `de? aaaa`
- abreviações: `jan|fev|mar|...|dez`

Coleta todos os matches `(mes, ano)`. Resultado = moda (par mais frequente);
empate → primeiro encontrado. Sem match → `mes=0, ano=0` (sem filtro).
A mesma função é aplicada à query de busca para o filtro mês/ano.

### Texto de embedding (`indexer.py`)

Concatenação: `document_type` + `directory` (nome da pasta) + `keywords` +
`entities` (valores) + `"mês {mes} ano {ano}"`. String única, `.strip()`.

### Schema ChromaDB

Collection `documentos`, `metadata={"hnsw:space": "cosine"}`.

| Campo metadata | Tipo | Origem |
|---|---|---|
| `dms_file_id` | int | id do `dms.file` |
| `tipo_documento` | str | `document_type_id` (nome, slug) |
| `mes` | int | regex (0 = desconhecido) |
| `ano` | int | regex (0 = desconhecido) |
| `arquivo` | str | `name` |
| `directory` | str | `directory_id` (nome) |
| `content_hash` | str | `ocr_content_hash` |

ChromaDB metadata só aceita escalares — entidades entram apenas no `document`
(texto embeddado), não como metadata filtrável na v1. Filtros rígidos (where-
clause) usam apenas `mes`/`ano`; `tipo_documento` fica como metadata informativa
e sinal soft no embedding, não filtro `$eq`.

`id` do Chroma = `str(dms_file_id)`.

### State (`state.db` — SQLite no volume)

Tabela `sync_state`: `checkpoint` (write_date ISO), `cycle_count` (int).

### API

- `POST /search` — header `X-Search-Token`. Body `{query: str, ai_mode: bool,
  top_k?: int}`. Retorna `{results: [{dms_file_id, score, tipo, mes, ano,
  arquivo, directory}], filters_applied: {...}}`.
- `GET /healthz` — status + tamanho da collection.

Tratamento de erro: collection vazia → `results: []`. JSON do Groq inválido →
fallback sem filtros estruturados (mantém busca semântica pura).

## Componente 2 — controller afr_ecm

Arquivo novo: `addons/afr_ecm/controllers/semantic_search.py`.

- Rota `POST /afr_ecm/semantic_search`, `auth='user'`, `type='json'`.
- Lê config params `afr_ecm.search.url` e `afr_ecm.search.token`.
- Repassa `{query, ai_mode}` ao microserviço com header de token.
- Recebe ids + scores. `request.env['dms.file'].browse(ids).exists()` filtra por
  ACL (registros sem permissão somem). Reordena pelo score original.
- Enriquece: `name`, `directory_id.name`, `mimetype`, `id`.
- Retorna lista ao ecm_desktop.
- Config params adicionados em `data/` (registro `ir.config_parameter`).

## Componente 3 — UI ecm_desktop

- Barra/tela de busca. Atalho global (avaliar Ctrl+K) ou tela dedicada.
- Toggle/botão **"Busca com IA"** → envia `ai_mode: true`.
- Wrapper em `renderer/lib/ecm-api.ts`: `semanticSearch(query, aiMode)`.
- Resultados: nome, pasta, tipo, mês/ano, score (%). Clique → abre
  `FilePreviewModal` existente.
- Estados: carregando, vazio ("nenhum resultado"), erro.

## Docker

Serviço novo em `docker-compose.yml`:

```yaml
  ecm-search:
    build: ./ecm_search
    environment:
      ODOO_URL: http://web:8069
      ODOO_DB: <db>
      # demais via .env
    env_file: ./ecm_search/.env
    depends_on: [web, db]
    volumes:
      - ./data/chroma:/data/chroma
    restart: always
```

Sem `ports:` — acesso só pela rede docker interna. Dockerfile: base
`python:3.11-slim`, instala `requirements.txt`, baixa o modelo de embedding no
build (camada cacheada) para não baixar em runtime.

`requirements.txt`: `fastapi`, `uvicorn`, `chromadb`, `sentence-transformers`,
`groq`, `apscheduler`, `requests`, `python-dotenv`.

## Segurança

- Microserviço sem porta pública; só rede docker.
- `/search` exige `X-Search-Token`; token em `ir.config_parameter` no Odoo.
- Controller `auth='user'` — só usuário Odoo logado.
- ACL aplicada no controller via `browse().exists()` no env do usuário.
- Conta de serviço Odoo: read-only em `dms.file`.
- Segredos (`GROQ_API_KEY`, senha, token) via `.env` não versionado;
  `.env.example` versionado.

## Testes

- **Microserviço (pytest)**: `date_extract` (vários formatos pt-BR + moda +
  empate + sem match), `indexer` (composição do texto de embedding),
  `search` (builder where-clause, collection vazia), `groq_parser` (parse OK +
  fallback JSON inválido, Groq mockado).
- **afr_ecm**: teste do controller — proxy + filtragem ACL (usuário sem
  permissão não vê o documento).
- **Integração manual**: `docker-compose up`, indexar amostra, queries variadas
  em linguagem natural (com e sem "Busca com IA").

## Sequência de build (fases)

1. Esqueleto `ecm_search/`: config, Dockerfile, requirements, FastAPI `/healthz`.
2. `odoo_client.py` — JSON-RPC login + call_kw.
3. `date_extract.py` + testes.
4. `embedder.py` + `store.py` (ChromaDB).
5. `indexer.py` + `state.py` — indexar 1 doc.
6. `sync.py` — pull cron + reconcile, APScheduler.
7. `groq_parser.py` + `search.py` + rota `/search`.
8. Container no `docker-compose.yml`; subir e validar indexação.
9. Controller proxy no afr_ecm + config params.
10. UI no ecm_desktop + wrapper `ecm-api.ts`.
11. Testes automatizados + integração manual.

## Checklist de entrega

- [ ] Microserviço indexa documentos com OCR concluído (pull cron).
- [ ] Reconcile remove do índice documentos apagados.
- [ ] Extração regex de mês/ano do conteúdo.
- [ ] `/search` com modo padrão e modo "Busca com IA" (Groq).
- [ ] Controller proxy no afr_ecm com ACL.
- [ ] UI de busca no ecm_desktop.
- [ ] Tratamento de coleção vazia e fallback de JSON do Groq.
- [ ] Testes automatizados (microserviço + controller).
- [ ] Validação manual com queries variadas.
