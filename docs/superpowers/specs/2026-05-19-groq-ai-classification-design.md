# Classificação IA de arquivos novos via Groq — Design

**Data:** 2026-05-19
**Autor:** brainstorm afonsorcarvalho + Claude
**Escopo:** monorepo `odoo_engenapp` — submodules `addons/afr_ecm/` (backend) + `ecm_desktop/` (cliente Electron)
**Status:** design aprovado seção a seção; aguarda revisão final do spec antes de plano de implementação

## 1. Objetivo

Reduzir trabalho manual de classificar arquivos no ECM. Após OCR, a IA sugere automaticamente:

1. Pasta destino (`dms.directory`) — top-1 + 2 alternativas
2. Tipo de documento (`afr.ecm.document.type`)
3. Tags (`dms.tag`)
4. Quando nenhuma pasta serve: rascunho de **nova pasta** (nome, pasta pai, manual)

A sugestão aparece como badge no card do arquivo no `ecm_desktop`; usuário abre painel lateral e aceita/edita/rejeita/ignora.

## 2. Decisões consolidadas

| Tópico | Decisão |
|---|---|
| Escopo IA | pasta + tipo + tags + criar nova pasta |
| Sinais | nome arquivo + texto OCR (1ª página + top-K chunks BM25) |
| Timing | após upload+OCR; banner/badge não bloqueia upload |
| Onde roda | servidor Odoo (afr_ecm Python) — API key centralizada |
| Triggers | hook pós-OCR + botão manual "Classificar com IA" no preview/bulk |
| Persistência | novo modelo `afr.ecm.ai.suggestion` (auditável) |
| UX | badge no card + painel lateral |
| Criar nova pasta | apenas usuários com grupo `afr_ecm.group_ai_classifier_admin` |
| Modelo Groq | `llama-3.3-70b-versatile` (default; config) |
| Recuperação contexto | sem embeddings — manuais das pastas inseridos direto no prompt com cap de tokens |
| Fila | `queue_job` (OCA) — hard dep do `afr_ecm`, sempre via `with_delay(channel="root.afr_ecm.ai_classify")`. Sem fallback `ir.cron`. |

## 3. Arquitetura

```
ecm_desktop (Next.js)         Odoo afr_ecm (Python)            Groq API
  ┌──────────────┐              ┌────────────────────┐         ┌──────┐
  │ Badge card   │◀── poll ─────┤ afr.ecm.ai.        │         │      │
  │ Painel lat.  │   /RPC       │   suggestion       │         │ llm  │
  │ Botões ação  │──── RPC ────▶│ ai_classify_now()  │────────▶│      │
  └──────────────┘              │                    │◀────────│      │
                                │ hook post-OCR      │         └──────┘
                                │ enqueue_job        │
                                └────────────────────┘
```

Fluxo end-to-end:

1. Upload via `ecm_desktop` → arquivo gravado em `dms.file`
2. OCR existente preenche `ocr_text` (Tesseract no servidor)
3. No fim de `dms.file._ocr_process` (após `ocr_state='done'` + `ocr_text` gravados) chama `_ai_dispatch_classification()` que enfileira job via `with_delay`. Sem override de `write` genérico.
4. Job: monta contexto (pastas+manuais, texto excerpts) → POST Groq → parse JSON → cria `afr.ecm.ai.suggestion` `state='pending'`
5. `ecm_desktop` poll por suggestions visíveis → badge aparece no card
6. Usuário click badge → painel lateral → ação:
   - **Aceitar:** RPC `ai_apply_suggestion` move doc, aplica tipo, adiciona tags
   - **Editar:** abre wizard pré-preenchido
   - **Criar nova pasta** (admin): cria `dms.directory` e move
   - **Rejeitar/Ignorar:** marca state, sem mudanças no doc

## 4. Modelos Odoo (afr_ecm)

### 4.1 Novo: `afr.ecm.ai.suggestion` (`_inherit = ['mail.thread']`)

| Campo | Tipo | Notas |
|---|---|---|
| `document_id` | Many2one `dms.file` | ondelete cascade, index, required |
| `state` | Selection | `pending` / `accepted` / `rejected` / `ignored` / `failed` |
| `model_used` | Char | ex `llama-3.3-70b-versatile` |
| `tokens_in` / `tokens_out` | Integer | métricas custo |
| `latency_ms` | Integer | tempo Groq |
| `confidence` | Float | 0..1 |
| `reasoning` | Text | explicação resumida do modelo |
| `suggested_directory_id` | Many2one `dms.directory` | top-1 |
| `alt_directory_ids` | One2many `afr.ecm.ai.suggestion.alt` | top-2 / top-3 + scores |
| `suggested_doc_type_id` | Many2one `afr.ecm.document.type` | |
| `suggested_tag_ids` | Many2many `dms.tag` | |
| `propose_new_directory` | Boolean | IA não confia em existentes |
| `new_directory_name` | Char | rascunho |
| `new_directory_parent_id` | Many2one `dms.directory` | pai sugerido |
| `new_directory_manual` | Html | rascunho manual |
| `applied_by_user_id` | Many2one `res.users` | quem aceitou |
| `applied_at` | Datetime | |
| `failure_reason` | Text | quando `state='failed'` |
| `raw_request` | Text | prompt enviado (sem header auth), trunc 16KB |
| `raw_response` | Text | resposta crua Groq, trunc 8KB |

### 4.2 Novo: `afr.ecm.ai.suggestion.alt`

Alternativas ranqueadas para a sugestão de pasta.

| Campo | Tipo | Notas |
|---|---|---|
| `suggestion_id` | Many2one `afr.ecm.ai.suggestion` | cascade, required |
| `directory_id` | Many2one `dms.directory` | required |
| `score` | Float | 0..1 |
| `rationale` | Text | razão curta |

### 4.3 Extensão `dms.file`

| Campo | Tipo | Notas |
|---|---|---|
| `current_suggestion_id` | Many2one `afr.ecm.ai.suggestion` | computed, store=True: último `pending` ou `processing` |
| `ai_state` | Selection (stored, default `none`) | `none` / `pending` / `processing` / `done` / `failed` / `skipped` — single source of truth, espelha pattern `ocr_state`. Dispatch grava `pending`; job grava `processing` → `done`/`failed`. Badge derivado deste + `current_suggestion_id.state` (accepted/rejected). |
| `last_classified_at` | Datetime | debounce reclassificação (>24h pra evitar replay automático) |

### 4.4 Extensão `dms.directory`

- Reaproveita `description` existente como manual da pasta (já em uso).
- Novo campo `ai_excluded` Boolean (default False) — docs nessa pasta nunca enviados ao Groq.

### 4.5 Segurança

- Novo grupo: `afr_ecm.group_ai_classifier_admin` (`implied_ids` inclui `afr_ecm.group_ecm_admin` se existir; caso contrário standalone)
- `ir.model.access.csv`:
  - `afr.ecm.ai.suggestion`: read = users; write/unlink = admin (apply via método sudo controlado)
  - `afr.ecm.ai.suggestion.alt`: idem
- `ir.rule` doc-level: usuário só vê suggestions de documents que pode ler (filter via `document_id.directory_id` access)
- `ai_apply_suggestion` re-checa `document.check_access_rights('write')` antes de mover

### 4.6 Parâmetros (`ir.config_parameter`)

| Chave | Default | Função |
|---|---|---|
| `afr_ecm.groq_api_key` | vazio (segredo) | API key — só sudo lê |
| `afr_ecm.groq_model` | `llama-3.3-70b-versatile` | modelo |
| `afr_ecm.groq_endpoint` | `https://api.groq.com/openai/v1/chat/completions` | endpoint OpenAI-compat |
| `afr_ecm.ai_max_input_tokens` | `8000` | cap prompt total |
| `afr_ecm.ai_min_confidence_for_auto` | `0.85` | futuro auto-apply; hoje só métrica |
| `afr_ecm.ai_allow_external` | `True` | kill-switch global |
| `afr_ecm.ai_max_requests_per_minute` | `60` | rate limit interno |
| `afr_ecm.ai_reclassify_min_hours` | `24` | debounce reclassificação |

## 5. Pipeline de classificação (servidor)

Serviço: `afr.ecm.ai.classifier` (AbstractModel — facilita testar via `env`).

### 5.1 `classify(document_id) -> suggestion_id`

```
1. pre-checks:
   - flag ai_allow_external == True
   - doc.directory_id.ai_excluded == False
   - doc.ocr_text não vazio
   - debounce: last_classified_at antigo o suficiente
   - se já existe suggestion pending → marca antiga 'ignored', cria nova

2. gather_signals(doc):
   - file_name, mimetype, size
   - ocr_text → extract_relevant_chunks:
     · first_page (até 1500 tokens, estimado por tiktoken-free heurística: ~4 chars/token)
     · split restante em parágrafos de ≤500 tokens
     · BM25 com query fixa "tipo documento natureza assunto cliente fornecedor projeto"
       (implementação inline pequena pra evitar nova dependência; se já houver `rank_bm25` no env, usar)
     · top-3 chunks
     · concatena com separador `\n---\n`
     · cap total 3000 tokens

3. gather_taxonomy() (cache LRU 5min, invalidado em create/write de dms.directory/document.type/tag):
   - dms.directory ativos: {id, full_path, manual_summary}
     · manual_summary = primeiros 500 chars de description (strip HTML)
   - afr.ecm.document.type ativos: {id, name}
   - dms.tag: {id, name}
   - Se total > 8000 tokens: trunca manuais por score BM25 (query = file text)

4. build_prompt(signals, taxonomy):
   system: "Você classifica documentos em ECM. Responda APENAS JSON válido conforme schema."
   user: JSON com file + directories + document_types + tags + schema-saída-esperada

5. call_groq(prompt):
   - POST com response_format={"type":"json_object"}
   - timeout 30s
   - retry exponencial 2/4/8s em 429/5xx (max 3)
   - registra tokens_in/out, latency_ms

6. parse_and_validate(response):
   - parse JSON
   - se inválido: 1 reprompt "responda APENAS JSON"; ainda falha → state='failed'
   - valida directory_id existe (search dms.directory)
   - valida document_type_id existe
   - filtra tag_ids inexistentes
   - clamp confidence 0..1
   - se directory_id null + propose_new_directory false → state='failed'

7. create afr.ecm.ai.suggestion:
   - state='pending' (ou 'failed')
   - popula campos
   - registra raw_request truncado / raw_response truncado
   - update doc.last_classified_at
   - doc.ai_state = 'done' (ou 'failed')
```

### 5.2 Concorrência

- `queue_job` é hard dep do `afr_ecm` (já em `__manifest__.depends`). Sempre `rec.with_delay(channel="root.afr_ecm.ai_classify", description="AI classify dms.file id=%s" % rec.id)._ai_process()`. Retry 2× via `@job(retry_pattern={1:60, 2:300})`.
- Lock anti-duplicata: hook `_ai_dispatch_classification` checa `ai_state in ('pending','processing')` antes de enfileirar (skip se já em fila). Não usa boolean separado.
- Rate limit interno via token bucket em `ir.config_parameter` (state em record `ir.model.data` ou simples lock por minute window).
- Padrão espelha [`_ocr_dispatch`](../../addons/afr_ecm/models/dms_file.py) (channel `root.afr_ecm.ocr`).

### 5.3 Custo estimado

~8K tokens in + ~300 out por doc × `$0.59/M in + $0.79/M out` (Groq llama-3.3-70b nov/2025) ≈ **$0.005/doc**.

## 6. Endpoints / RPC (afr_ecm → ecm_desktop)

Métodos públicos em `dms.file`:

| Método | Args | Retorno | Permissão |
|---|---|---|---|
| `ai_classify_now(ids)` | `int[]` | `{queued: int[], suggestion_ids: int[]}` | usuário com read no doc |
| `ai_apply_suggestion(suggestion_id, overrides)` | `int`, `dict?` | `{ok, document_id, new_directory_id?}` | dono / admin |
| `ai_reject_suggestion(suggestion_id, reason)` | `int`, `str` | `{ok}` | dono |
| `ai_ignore_suggestion(suggestion_id)` | `int` | `{ok}` | dono |
| `ai_list_suggestions(document_ids)` | `int[]` | `EcmAiSuggestion[]` (search_read) | filtrado por ACL |

`ai_apply_suggestion` lógica:
1. Carrega suggestion `pending`
2. Aplica `overrides` (user editou directory_id, tag_ids, etc.)
3. Se `propose_new_directory` aceita:
   - `user.has_group('afr_ecm.group_ai_classifier_admin')` ou raise `AccessError`
   - Cria `dms.directory` com (parent, name, description=manual)
4. Move `document.directory_id`
5. Aplica `document_type_id` se não setado (não sobrescreve manual)
6. Adiciona tags via `(4, tag_id)`
7. `state='accepted'`, registra applied_by_user_id, applied_at
8. `mail.thread.message_post` no doc

## 7. Cliente — ecm_desktop (renderer)

### 7.1 API wrapper (`renderer/lib/ecm-api.ts`)

Métodos novos:
```ts
async aiClassifyNow(ids: number[])
async aiApplySuggestion(id: number, overrides?: AiSuggestionOverrides)
async aiRejectSuggestion(id: number, reason: string)
async aiIgnoreSuggestion(id: number)
async listAiSuggestions(documentIds: number[]): Promise<EcmAiSuggestion[]>
```

Types: `EcmAiSuggestion`, `AiSuggestionAlt`, `AiSuggestionOverrides`.

### 7.2 Componentes novos

| Arquivo | Função |
|---|---|
| `components/AiSuggestionBadge.tsx` | Badge no card com cores por state |
| `components/AiSuggestionPanel.tsx` | Painel lateral (sheet à direita) com sugestão completa |
| `components/CreateDirectoryFromAi.tsx` | Sub-modal de criação pré-preenchida (admin) |
| `hooks/useAiSuggestions.ts` | React Query batch + polling enquanto há `pending`/`processing` |

### 7.3 Layout painel

```
┌─ ✨ Sugestão IA ────────────────  [X] ─┐
│ Confiança: ████████░░ 82%             │
│ 📁 PASTA  → Contratos/2026/Clientes   │
│   "Doc parece contrato de prestação…" │
│ [✓ Aceitar]  [Ver alternativas ▾]     │
│ Alternativas (2)                       │
│  · Contratos/Arquivados      (12%)    │
│  · Jurídico/Modelos          (6%)     │
│ 🏷 TIPO: Contrato de Prestação  ✏    │
│ 🔖 TAGS: cliente-novo, SLA      ✏    │
│ [✓ Aceitar tudo]  [Editar no wizard]  │
│ [Rejeitar] [Ignorar]                  │
└────────────────────────────────────────┘
```

Quando `propose_new_directory=true`:
- Bloco "💡 Nenhuma pasta serve. IA propõe nova"
- Nome / pai / manual rascunho
- Botão `[+ Criar e mover]` desabilitado pra não-admin com tooltip

### 7.4 Integrações

- Card de arquivo em `renderer/app/page.tsx`: badge canto sup-direito quando `ai_state in ['pending','processing','failed']`
- Click badge → abre `AiSuggestionPanel`
- `BulkActionBar`: ação "Classificar selecionados com IA" → `aiClassifyNow(ids)` em massa
- `FilePreviewModal`: footer ganha botão "✨ Classificar IA"
- Polling: React Query `['ai-suggestions', currentDirId]` `refetchInterval: 8000` enquanto pendente

### 7.5 Toast / undo

- Aceitar: "Movido pra X • tipo Y • 3 tags aplicadas" + undo (10s) que chama `ai_reject_suggestion` e reverte move
- Rejeitar: "Sugestão rejeitada", sem undo
- Criar pasta: "Pasta X criada e doc movido"

## 8. Segurança / privacidade / erros

### 8.1 Segredos

- API key em `ir.config_parameter`; service lê via `sudo()`. Tela `res.config.settings` aba **ECM > IA** com widget password.
- Validação na hora de salvar: ping `/openai/v1/models` com header Authorization; falha → mensagem clara.
- Nunca logar headers ou key. `raw_request` armazena prompt sem header.

### 8.2 Controle envio externo

- `afr_ecm.ai_allow_external` (default True) — kill switch
- `dms.directory.ai_excluded` — por pasta
- Service checa ambos antes de chamar Groq

### 8.3 Tratamento de erros

| Erro | Tratamento |
|---|---|
| API key vazia | skip silencioso, warning log |
| Timeout >30s | retry 1x; depois state=failed |
| 429 / 5xx | backoff 2/4/8s, 3 tentativas, depois reenfileira no próximo cron |
| JSON inválido | reprompt 1x; depois state=failed |
| directory_id inexistente | state=failed, motivo "modelo alucinou pasta" |
| Doc sem texto OCR | skip, log "sem texto pra classificar" |
| `ai_allow_external=False` | skip silencioso |

### 8.4 Auditoria

- `mail.thread` no doc registra: enfileiramento, sucesso/falha IA, aceitação user
- Métricas via `afr.ecm.ai.suggestion`: count por state, latency média, tokens totais (dashboard futuro)

## 9. Testes

### 9.1 Backend Python (`addons/afr_ecm/tests/test_ai_classifier.py`)

| Teste | Verifica |
|---|---|
| `test_gather_signals_with_ocr` | chunks corretos |
| `test_gather_signals_no_text` | doc sem texto → skip |
| `test_gather_taxonomy_caps_tokens` | trunca manuais em excesso |
| `test_build_prompt_schema` | prompt válido |
| `test_call_groq_mocked` | mock requests retorna JSON; parse ok |
| `test_call_groq_invalid_json_reprompt` | 1ª inválida → 2ª válida → success |
| `test_call_groq_double_invalid_fails` | falha após 2 JSON ruim |
| `test_call_groq_rate_limit_backoff` | 429 dispara retry |
| `test_directory_id_hallucinated` | id inexistente → failed |
| `test_apply_suggestion_moves_doc` | aceitar move + tags + type |
| `test_apply_suggestion_admin_only_for_new_dir` | non-admin + propose_new → AccessError |
| `test_apply_suggestion_creates_directory` | admin + propose_new → cria dir |
| `test_apply_suggestion_tags_appended_not_replaced` | mantém + adiciona |
| `test_reject_suggestion` | state=rejected, reason gravado |
| `test_ignore_supersedes_previous_pending` | nova classify_now marca antiga ignored |
| `test_ai_excluded_directory_skipped` | pasta excluída → skip |
| `test_ai_allow_external_off` | flag off → skip |
| `test_acl_user_sees_own_suggestions_only` | user A não vê suggestions doc user B |

### 9.2 Frontend (manual + smoke)

Smoke: `npm run build` passa.

Manual via dev (`localhost:3000` apontando Odoo dev):
1. Upload doc → após OCR aparece badge amber
2. Click badge → painel mostra sugestão
3. Aceitar → toast + doc move + badge some
4. Rejeitar → toast + badge some
5. Editar no wizard → preenche pré-selecionado
6. Como admin: bloco "criar nova pasta" → cria + move
7. Como user normal: bloco criar disabled com tooltip
8. Bulk: 3 docs → "Classificar IA" → 3 jobs

### 9.3 Fixtures demo

`addons/afr_ecm/demo/ai_suggestions_demo.xml`: 1 pending + 1 accepted + 1 rejected pra screenshots.

### 5.4 Dependências Python adicionais

- `requests` — já em Odoo
- BM25 — implementado inline (~30 linhas) ou opcional `rank_bm25` se já instalado
- Sem nova dependência hard no `__manifest__.py`

## 10. Fora deste escopo (futuro)

- Auto-apply quando confidence > threshold
- Dashboard de métricas IA
- Embeddings locais + RAG (Pacote C do brainstorm)
- Multi-provider (OpenAI / Anthropic fallback)
- Aprendizado por feedback (fine-tune ou re-ranker dos manuais)
- Cron de backfill em massa (mencionado no brainstorm, deixado fora pra MVP focar no fluxo de upload novo)

## 11. Plano de fases sugerido

Pra permitir teste rápido em `localhost:3000`, ordem proposta:

1. **Fase 1 — afr_ecm models + settings:** modelos novos, segurança, settings (sem chamada Groq). Migrável; teste: tela settings aparece.
2. **Fase 2 — service classifier + endpoints:** lógica Python + RPC. Teste via shell Odoo (`env['dms.file'].browse(x).ai_classify_now()`).
3. **Fase 3 — hook pós-OCR + queue_job dispatch:** chamada `_ai_dispatch_classification()` injetada no fim de `_ocr_process`. Teste: upload novo doc → após OCR done → job AI enfileira → suggestion criada.
4. **Fase 4 — renderer badge + panel + actions:** UI. Teste end-to-end via `localhost:3000`.
5. **Fase 5 — bulk + preview + criar nova pasta:** polimento.
6. **Fase 6 — testes Python e fixtures demo:** consolidação.

Cada fase comitada num branch separado em ambos submodules; user testa entre fases.
