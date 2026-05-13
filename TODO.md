# TODO — odoo_engenapp

## Em curso
- (nada — sessão pausada após conversão submodule)

## Pendente
- afr_ecm: criar `data/dms_access_group_data.xml` com `dms.access.group` default vinculando `group_ecm_user`, `group_ecm_manager` e `group_ecm_admin` em `group_ids`. Sem isso, novos users ECM não veem diretórios DMS até ajuste manual via UI/SQL. Workaround atual: SQL direto na DB.
- F4.1.3 Electron real: terminar watch folder (já tem useWatchFolder + settingsStore + settings UI). Falta testar fim-a-fim com WSLg/GUI.
- ecm_desktop TOC PDF: aba "Sumário" abrir por default no FilePreviewModal (atualmente só auto-abre se outline existe + multi-pg; mudar pra sempre default quando há entries).
- ecm_desktop TOC PDF: clique em item do sumário deve scrollar até a linha do título dentro da página, não só pular pra página. Usar coords do dest (Y offset) via `pdf.getDestination` + `react-pdf` scroll offset (scrollIntoView do span com coords) ou destacar bbox.
- ecm_desktop Search PDF: resultado de busca scrollar pra linha exata do match (mesma técnica do TOC). Hoje pula só pra página, user tem que rolar manual.

## Feito
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
