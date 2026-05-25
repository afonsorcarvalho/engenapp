# TODO — odoo_engenapp

## Em curso
- (nada)

## Feito
- 2026-05-24 — F9.1 LabQuali brand layout (afr_labquali_layout 16.0.1.0.0). Novo addon registra tile "LabQuali" no wizard Configure Document Layout (sequence 10). Template QWeb com header (logo + divisor azul), footer (border-top azul + page number), Inter font bundled woff2, selo CONFIDENCIAL opcional via `res.company.lq_confidential_default` (related em `base.document.layout` para preview wizard). Estilo Boxed-base aplicado (tabelas com border 1px cinza, thead UPPERCASE fundo cinza claro + texto azul, total row fundo azul + texto branco). H2 + h2 span em laranja como acento. Paperformat A4 bundled noupdate=1 (margin_top=20 margin_bottom=10 margin_left=5 margin_right=8 header_spacing=20). Header/footer SEM `<table>` (float-based) para evitar bleed de borders de outros reports (invoice/inventory). Stripe lateral laranja REMOVIDO. Stale SCSS asset deletado (estava injetando border laranja no footer via web.report_assets_common). Commits no monorepo: 5a86948, 85adbf1, ccb7556, e842da1, d7b94f9, b2aed7a, 598699e, 7adc289, b83972d.

## Pendente

### afr_qualificacao
- **F4.2 — Timesheet/project + custos extras**: dep `hr_timesheet`. `project_id`/`task_id` auto via produto `service_tracking=task_in_project`. `cost_total` compute de `account.analytic.line`. Wizard "Adicionar custo" (deslocamento/instrumento).
- **F4.4 — Multi-company hardening + testes**: record rules por `company_id`, multi-company support, suite `tests/test_billing.py` adicional.
- **F4.5 (novo)** — Auto-geração `engc.calibration` ao approval de qualif Calib + propagação state bidirecional. Hoje link é manual (Opção A do plan).

### afr_llm_assistant
- **Cache catálogos** (`_installed_models_catalog_text`, `_reports_catalog_for_user_text`, `_whitelist_models_field_catalog`): atualmente rebuild a cada call (~2-5s overhead). Usar `@tools.ormcache` ou cache em memória com invalidação por write em `ir.model` / `ir.actions.report`.
- **Streaming SSE** no chat: substituir RPC bloqueante por stream de tokens (Ollama suporta `stream: true`). Melhora UX (sem "AGUARDE..." parado). Requer adapt no `_lmstudio_chat_*` + frontend OWL consumir EventSource.
- **WebSocket bind error 8072** (`KeyError: 'socket'` polui logs): configurar gevent worker pra `/websocket` OR desabilitar `/websocket` para o chat (usar polling do job, que já funciona).
- **Timeout HTTP configurável**: `urllib.request.urlopen(req, timeout=180)` hardcoded em `_lmstudio_post_json`. Mover pra ICP `afr_llm_assistant.http_timeout`.
- **Tool `odoo_make_link`**: estruturar geração de URLs `/web#…`, `/web/content/<id>`, `/report/pdf/<name>/<ids>` via tool call (substitui `[[ODOO_LINK]]` legacy).
- **Whitelist expansiva por grupo**: ICP atual é global. Permitir por grupo de user via `res.groups` (ex.: gerentes acessam mais modelos).
- **Embeddings + RAG (F1 do roadmap)**: pgvector já no compose; indexar histórico de OS, manuais técnicos, anexos. Usar `nomic-embed-text` ou `qwen2.5:1.5b` pra embeddings.
- **Métricas/observabilidade**: log estruturado tokens in/out, latência, modelo, cache hit. Dashboard simples (kanban ou dashboard ir.ui.view).
- **Histórico múltiplas sessões**: hoje 1 sessão por user. Permitir N com título auto-gerado pelo modelo.
- **Tool calling para Anthropic provider**: implementação atual só lmstudio. Anthropic Claude tem `tools` array nativo similar.

### Outros
- afr_ecm: criar `data/dms_access_group_data.xml` com `dms.access.group` default vinculando `group_ecm_user`, `group_ecm_manager` e `group_ecm_admin` em `group_ids`. Sem isso, novos users ECM não veem diretórios DMS até ajuste manual via UI/SQL. Workaround atual: SQL direto na DB.
- F4.1.3 Electron real: terminar watch folder (já tem useWatchFolder + settingsStore + settings UI). Falta testar fim-a-fim com WSLg/GUI.
- ecm_desktop TOC PDF: aba "Sumário" abrir por default no FilePreviewModal (atualmente só auto-abre se outline existe + multi-pg; mudar pra sempre default quando há entries).
- ecm_desktop TOC PDF: clique em item do sumário deve scrollar até a linha do título dentro da página, não só pular pra página. Usar coords do dest (Y offset) via `pdf.getDestination` + `react-pdf` scroll offset (scrollIntoView do span com coords) ou destacar bbox.
- ecm_desktop Search PDF: resultado de busca scrollar pra linha exata do match (mesma técnica do TOC). Hoje pula só pra página, user tem que rolar manual.
- ecm_desktop Grid pastas: quando pasta atual tiver subpastas, mostrar ícone de pasta clicável no grid (entra na subpasta) junto com os arquivos. Hoje subpastas só aparecem no FolderTree esquerdo.

## Feito
- 2026-05-16 — afr_qualificacao v16.0.2.2.2: PDF cotação refinements — (a) agrupa Sumário Executivo + Descritivo Técnico mesma página; (b) agrupa Resumo Financeiro + Condições Comerciais + Aceite mesma página (classe CSS `qq-section-cont`); (c) esconde `.address` injetado por `external_layout_standard` na capa (eliminava duplicação partner antes do título); (d) duplicação SO preserva metadados qualif (`copy=True` em equipment_id, qualification_type, cycle_type_id, malha_type_id, is_qualificacao_managed; `afr_qualificacao_id` mantém `copy=False`). 43 tests pass.
- 2026-05-16 — afr_qualificacao v16.0.2.2.0: relatório PDF dedicado de cotação (inherit `sale.report_saleorder_document` com fallback condicional via `has_qualif_lines`): capa + sumário executivo + descritivo técnico + escopo por equipamento + normas aplicáveis + resumo financeiro + condições comerciais + aceite. Novo modelo `afr.qualificacao.standard` + M2M em cycle_type/malha_type + 8 normas seed. Section lines por equipamento no form SO + painel HTML `qualif_subtotals_html`. Fonts +30%.
- 2026-05-16 — afr_qualificacao F4.3 v16.0.2.1.0: certificado digital verificável (hash SHA-256 + token UUID4 + QR + controller `/qualificacao/verify/<token>`). Templates QI/QO/QD/QS + inherit engc.calibration + fallback Calib sem `engc.calibration`. Commit `936b444`.
- 2026-05-16 — afr_qualificacao v16.0.2.0.0: fluxo comercial quote-first (sale.order → afr.qualificacao + engc.os). Wizard configurador (matriz equipamento × tipo) + sub-records cycle/malha + integração engc.calibration via FK manual + propagação qty_delivered no approval. 21 tests pass. Commit `655eb09`.
- 2026-05-15 — afr_llm_assistant: GPU NVIDIA passthrough (nvidia-container-toolkit + compose) + modelo custom `llama3.1:8b-ctx8k` (num_ctx=8192) + system prompt refactor anti-SQL/few-shot. CPU 6.5 tok/s → GPU ~100 tok/s.
- 2026-05-15 — afr_llm_assistant: tool calling estruturado (OpenAI tools API) opt-in via ICP `use_tool_calling`. 4 tools (search_read, search_count, read_group, fields_get) + coerção tolerante args + loop multi-turn max 5 iter. Resolve hallucination multi-turn. System prompt enxuto na variante tool-calling (~60% menor).
- 2026-05-12 — Conversão de subtree para git submodules (afr_ecm + ecm_desktop). Backup em tag `pre-submodule-conversion` e branch `backup/pre-submodule-conversion`.
- 2026-05-12 — Sidebar esquerda redimensionável (splitter drag, persist localStorage).
- 2026-05-12 — Drag-drop mover arquivos e pastas no FolderTree (com bloqueio de ciclo).
- 2026-05-12 — Editor de propriedades inline no painel direito (tipo, pasta, confid, OCR, vencimento) com permission_write check.
- 2026-05-12 — `ocr_enabled` per-file no afr_ecm (opt-in override do tipo).
- 2026-05-12 — Ícones por tipo de arquivo + thumbnails para imagens (lib/file-icons + FileIcon).
- 2026-05-12 — Renomear pasta (modal + F2 + dblclick + Pencil hover).
- 2026-05-12 — Delete pasta (Trash hover + Shift+Del + confirm).
- 2026-05-12 — Fix criar pasta raiz com storage_id + group_ids.
- 2026-05-12 — Sort dropdown + Empty state + atalhos Enter/Del.
- 2026-05-12 — Nova pasta + Breadcrumb + Tags (m2m dms.tag).
- 2026-05-12 — Restrição de download por tipo de documento (afr_ecm + ecm_desktop).
