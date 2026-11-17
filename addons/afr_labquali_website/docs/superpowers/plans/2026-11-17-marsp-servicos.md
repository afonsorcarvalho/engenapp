# MARSP Serviços Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar `/marsp/servicos` (8 serviços pós-venda MARSP) e uma faixa-resumo na vitrine `/marsp` linkando a ela.

**Architecture:** Página HTML estática em `static/demos/marsp-servicos/` servida pela rota genérica `/marsp/<slug>` de `controllers/demos.py` (basta adicionar `"servicos"` à tupla `MARSP`). Reusa `_marsp/marsp.css` + padrões de `marsp-vitrine/page.css`. Faixa na vitrine = nova `<section id="servicos">` entre `#parceria` e `#proposta`.

**Tech Stack:** Odoo 16 (HttpCase), HTML/CSS estático, SVG inline.

**Spec:** `docs/superpowers/specs/2026-11-16-marsp-servicos-design.md`

## Global Constraints
- Texto pt-BR; nenhum texto/número copiado de Telstar ou BOCON.
- Sem promessas: proibido no HTML "SLA", "24h", "24 h", "estoque", "laboratório", "peças".
- LabQuali não aparece na página de serviços, exceto o link `/retrofit/eto` e o e-mail de contato existente (`labquali@labquali.com.br`, já usado na vitrine).
- CTA de serviço: texto "Solicitar atendimento técnico", `mailto:labquali@labquali.com.br?subject=Atendimento%20t%C3%A9cnico%20MARSP`.
- Design system MARSP: `/marsp/_marsp/marsp.css`, navy `#0A3D62`, laranja `#FF6B35`; mobile-first, sem scroll horizontal a 360 px.
- Manifest: `16.0.1.24.0` → `16.0.1.25.0` (feat → MINOR).
- Testes: `tests/test_marsp.py`, rodados via agente `test-runner` com `--test-tags /afr_labquali_website` (HttpCase: `--http-port 8999 --workers 0`).

## Review Focus
- Mobile 360 px: 8 blocos empilham sem estouro horizontal → verificação visual via agent-browser (Task 2).
- Âncoras: cada serviço tem `id` estável (`diagnostico`, `manutencao`, `retrofit`, `qualificacao`, `calibracao`, `treinamento`, `suporte-remoto`, `engenharia`) para os links da faixa → teste na Task 1.
- Palavras proibidas vazando no copy → teste na Task 1.
- Faixa da vitrine fora de ordem (antes de `#parceria` ou depois de `#proposta`) → teste na Task 2.
- Link de retrofit quebrado → teste de `href="/retrofit/eto"` na Task 1.

---

### Task 1: Página `/marsp/servicos`

**Files:**
- Create: `static/demos/marsp-servicos/index.html`, `static/demos/marsp-servicos/page.css`
- Modify: `controllers/demos.py:30` (`MARSP = ("autoclave-eto", "servicos")`)
- Test: `tests/test_marsp.py` (nova classe `TestMarspServicos(HttpCase)`)

**Interfaces:**
- Produces: URL `/marsp/servicos`; âncoras `#diagnostico #manutencao #retrofit #qualificacao #calibracao #treinamento #suporte-remoto #engenharia`.

- [ ] **Step 1: Testes que falham** — em `TestMarspServicos`:
  - `test_route_200`: `url_open("/marsp/servicos").status_code == 200`.
  - `test_eight_services_in_order`: as 8 strings `id="<âncora>"` aparecem no HTML na ordem listada acima (índices crescentes).
  - `test_retrofit_link`: `'href="/retrofit/eto"'` no HTML.
  - `test_cta`: `"Solicitar atendimento técnico"` e `"subject=Atendimento%20t%C3%A9cnico%20MARSP"` no HTML.
  - `test_no_promises`: nenhuma das palavras proibidas (Global Constraints) no HTML, case-insensitive.
  - `test_key_content`: contém `"ISO 11135"`, `"RBC"`, `"incerteza"`, `"qualquer marca"`, `"validação de software"`, `"NR-13"`, `"corretiva"`.
  - `test_brand_css`: `"/marsp/_marsp/marsp.css"` no HTML.
- [ ] **Step 2:** rodar → FAIL (404).
- [ ] **Step 3:** adicionar `"servicos"` a `MARSP`; escrever `index.html` (head/topbar/footer copiados da estrutura de `marsp-autoclave-eto/index.html`) com hero curto ("Serviços para autoclaves de óxido de etileno — de qualquer marca"), sumário de âncoras, 8 `<section id=…>` no formato *o que é / inclui / você recebe* com o conteúdo do spec (incluindo enriquecimentos técnicos e validação de software do CLP), CTA final. Ícones: SVG inline simples por serviço. `page.css`: grid 1 col mobile, 2 col ≥ 900 px.
- [ ] **Step 4:** rodar → PASS.
- [ ] **Step 5:** commit `feat(afr_labquali_website): MARSP services page` (via agente de commit, só após OK do user — ver Task 2).

### Task 2: Faixa na vitrine + versão

**Files:**
- Modify: `static/demos/marsp-vitrine/index.html` (nova section entre `#parceria` e `#proposta`), `static/demos/marsp-vitrine/page.css`, `__manifest__.py` (`16.0.1.25.0`)
- Test: `tests/test_marsp.py`

**Interfaces:**
- Consumes: URL e âncoras da Task 1.

- [ ] **Step 1: Testes que falham** em `TestMarspServicos`:
  - `test_vitrine_band_position`: em `/marsp`, `index('id="parceria"') < index('id="servicos"') < index('id="proposta"')`.
  - `test_vitrine_band_links`: `'href="/marsp/servicos"'` presente e os 8 links `/marsp/servicos#<âncora>`.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** `<section id="servicos" class="v-part" aria-labelledby="servicos-titulo">` com `<h2 id="servicos-titulo">Serviços</h2>`, 8 itens (ícone + título curto) linkando às âncoras, botão "Ver todos os serviços" → `/marsp/servicos`. Bump do manifest.
- [ ] **Step 4:** rodar suíte inteira de `test_marsp.py` → PASS (sem regressão).
- [ ] **Step 5:** restart container, validar via agent-browser `/marsp` e `/marsp/servicos` em desktop e 360 px (sem scroll horizontal, links de âncora funcionam). Screenshot ao user.
- [ ] **Step 6:** após OK explícito do user: commit `feat(afr_labquali_website): MARSP services band on showcase` via agente haiku; deploy remoto só com autorização.
