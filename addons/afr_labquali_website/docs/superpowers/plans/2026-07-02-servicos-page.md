# Página de Serviços (/our-services) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Rebrandar `/our-services` para as specs de DESIGN.md usando snippets nativos Odoo, com SCSS de marca versionado e um preview semeado no DB.

**Architecture:** Abordagem A — snippets nativos + SCSS scoped em `.lq-servicos` (git, deployável). Conteúdo no builder (não-git); preview semeado no arch_db da view `website.servicos`.

**Tech Stack:** Odoo 16 website snippets, SCSS (libsass), QWeb.

## Global Constraints

- Odoo 16.0; container `odoo_engenapp-web-1`; DB `odoo-labquali`; entrypoint intercepta `-*` (usar `/entrypoint.sh -u ... --stop-after-init --no-http`).
- DESIGN.md: North Star "Certified Blueprint"; tokens `--lq-*`; Calibration Point (laranja ≤ acentos/CTA); Flat-By-Default (sombra só hover, tingida navy); Cold-Warm (navy domina).
- **Bump obrigatório** de `version` no `__manifest__.py` a cada mudança (senão `-u` remoto não reprocessa assets). fix/style → PATCH.
- Commits via agente haiku, staging só de paths do módulo.
- Browser bloqueado: validar SCSS via libsass + `-u` exit 0; render visual é o usuário.

---

### Task 1: SCSS de marca + registro no manifest

**Files:**
- Create: `addons/afr_labquali_website/static/src/scss/labquali_servicos.scss`
- Modify: `addons/afr_labquali_website/__manifest__.py` (assets + version bump)

- [ ] **Step 1: Criar o SCSS** (`labquali_servicos.scss`), scoped em `.lq-servicos`:

```scss
// Marca da página /our-services (snippets Odoo). Escopo .lq-servicos.
.lq-servicos {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;

    // 1) Banner s_cover
    .s_cover {
        background: linear-gradient(135deg, var(--lq-dark) 0%, var(--lq-brand) 55%, #0d2f4a 100%);
        color: #fff;
        h1 { font-weight: 900; letter-spacing: -0.04em; color: #fff; text-wrap: balance;
             .lq-accent { color: var(--lq-accent); } }
        p, .lead { color: rgba(255,255,255,0.75); }
    }

    // 2) s_three_columns — cards flat + topo laranja
    .s_three_columns .card {
        border: 1px solid var(--lq-hairline);
        border-top: 3px solid var(--lq-accent);
        border-radius: 14px;
        background: #fff;
        transition: box-shadow .2s, transform .2s;
        &:hover { box-shadow: 0 8px 32px rgba(10,61,98,.12); transform: translateY(-3px); }
        h3, .card-title, h4 { color: var(--lq-brand); font-weight: 700; }
        p { color: var(--lq-gray); }
    }

    // 3) s_image_text / s_text_image — detalhe
    .s_image_text, .s_text_image {
        h2, h3 { color: var(--lq-brand); font-weight: 800; letter-spacing: -0.02em; }
        img { border-radius: 14px; }
        ul li::marker { color: var(--lq-accent); }
        strong { color: var(--lq-brand); }
    }

    // 4) s_quotes_carousel
    .s_quotes_carousel {
        .s_blockquote, blockquote { color: var(--lq-brand); }
        .s_blockquote_author, footer, small { color: var(--lq-accent); font-weight: 600; }
    }

    // 5) s_call_to_action — Cold-Warm: campo navy, botão laranja
    .s_call_to_action {
        background: linear-gradient(135deg, var(--lq-dark), var(--lq-brand)) !important;
        color: #fff;
        h2, h3 { color: #fff; font-weight: 900; }
        p, .lead { color: rgba(255,255,255,.8); }
        .btn_cta, .btn-primary, a.btn {
            background: var(--lq-accent); border-color: var(--lq-accent); color: #fff !important; font-weight: 700;
            &:hover { background: var(--lq-accent-2); border-color: var(--lq-accent-2); }
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .s_three_columns .card { transition: none; &:hover { transform: none; } }
    }
}
```

- [ ] **Step 2: Registrar no manifest** — adicionar ao `web.assets_frontend` (após o scss da home) e bump de version:

```python
"afr_labquali_website/static/src/scss/labquali_servicos.scss",
```
E `"version": "16.0.1.1.4"` → `"16.0.1.1.5"`.

- [ ] **Step 3: Validar compile** (libsass no container):

```bash
docker cp addons/afr_labquali_website/static/src/scss/labquali_servicos.scss odoo_engenapp-web-1:/tmp/_srv.scss
docker exec odoo_engenapp-web-1 python3 -c "import sys;sys.path.insert(0,'/usr/lib/python3/dist-packages');import sass;print('OK',len(sass.compile(filename='/tmp/_srv.scss')))"
```
Expected: `OK <n>` sem erro. (o scss standalone referencia `var(--lq-*)` — passa em libsass pois são CSS custom props, não vars sass.)

- [ ] **Step 4: Deploy + validar `-u`:**

```bash
docker exec odoo_engenapp-web-1 /entrypoint.sh -u afr_labquali_website -d odoo-labquali --stop-after-init --no-http --log-level=warn 2>&1 | grep -iE "error|traceback|servicos" | grep -viE "Missing .license|not overriding|has no _description|ondelete"
```
Expected: sem erro; exit 0.

- [ ] **Step 5: Commit** (agente haiku, staging só `labquali_servicos.scss` + `__manifest__.py`).

---

### Task 2: Semear o preview no arch_db da página

**Files:**
- Modify (DB-only, não-git): arch_db da view `website.servicos` (id via busca).

**Interfaces:**
- Consome: imagens `/web/image/afr.labquali.homepage/1/{svc_qualificacao,svc_calibracao,svc_nr13}` (ACL público já confirmado).
- Produz: página `/our-services` renderizável com 5 snippets + wrapper `.lq-servicos`.

- [ ] **Step 1: Ler o arch demo atual** pra herdar o wrapper QWeb correto (`<t t-call="website.layout">`, `#wrap`, snippet class patterns):

```bash
docker exec odoo_engenapp-web-1 python3 -c "<script lê ir.ui.view key=website.servicos arch_db e imprime>"
```

- [ ] **Step 2: Compor o novo arch** — mesmo wrapper, `<div id="wrap" class="oe_structure lq-servicos">` contendo, em ordem, os snippets com `data-snippet`/`data-name` e o conteúdo do spec (Seção 3 do design doc). H1 com `<span class="lq-accent">metrológica</span>`. Imagens dos detalhes via `t-att-src` `/web/image/...` OU `<img src="/web/image/afr.labquali.homepage/1/svc_*">` (registro id=1). Placeholder de quotes marcado.

- [ ] **Step 3: Escrever arch_db** via python in-container (SUPERUSER), `v.write({'arch': novo})`, `cr.commit()`.

- [ ] **Step 4: Validar** — reler arch: confere presença de `lq-servicos`, `s_cover`, `s_three_columns`, 3× `s_image_text`, `s_quotes_carousel`, `s_call_to_action`, 3× `/web/image`, e ausência do texto demo ("Itens exclusivos", "Jane DOE"). HTML bem-formado.

- [ ] **Step 5: Handoff visual** — pedir ao usuário abrir `/our-services` (browser dele) e confirmar. Preview é DB-only (não commitar).

## Self-Review

- Spec coverage: banner(T2)/3 serviços(T2)/detalhe QI-QO-QD(T2)/quotes(T2)/CTA(T2) + SCSS de marca(T1) — coberto.
- SCSS scoped `.lq-servicos` casa com o wrapper class do arch (T2 step 2). Consistente.
- Sem placeholders de plano; código SCSS completo em T1.
- Ressalva registrada: arch de snippet autoral pode precisar retoque no builder.

## Notas
- Preview (Task 2) é DB-only — NÃO vai pro git. Só Task 1 (SCSS+manifest) e os docs commitam.
