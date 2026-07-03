# Home → Native Odoo Snippets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) para implementar task-a-task. Steps usam checkbox (`- [ ]`).

**Goal:** Converter a homepage code-driven (.lq-/GSAP) para snippets nativos Odoo editáveis no builder, com SCSS de marca site-wide e GSAP removido.

**Architecture:** Remove o template inherit + a view do DB; a `website.homepage` passa a servir conteúdo builder. SCSS refatorado em 2 arquivos (chrome + snippets site-wide). Preview semeado no arch da homepage (DB-only).

**Tech Stack:** Odoo 16 website snippets, SCSS (libsass), QWeb, psql.

## Global Constraints

- Odoo 16.0; container `odoo_engenapp-web-1`; DB `odoo-labquali`; `/entrypoint.sh -u ... --stop-after-init --no-http`.
- DESIGN.md: North Star "Certified Blueprint"; tokens `--lq-*`; Calibration Point (laranja ≤ acentos/CTA); Flat-By-Default; Cold-Warm (navy domina).
- **Bump obrigatório** de `version` no manifest.
- Commits via agente haiku, staging só de paths do módulo. Preview no DB é não-git.
- Browser bloqueado: validar SCSS via libsass + `-u` exit 0; render = usuário abre `/`.
- Imagens já existem: `/web/image/afr.labquali.homepage/1/{svc_*,dif_*,eqp_*}` (registro id=1, ACL público).

---

### Task 1: SCSS site-wide de snippets + refactor chrome + manifest + remover GSAP

**Files:**
- Create: `static/src/scss/labquali_snippets.scss` (marca snippet site-wide, sem scope)
- Modify: `static/src/scss/labquali_website.scss` (enxugar p/ chrome+tokens)
- Modify: `__manifest__.py` (assets: −GSAP, −labquali_servicos.scss, +labquali_snippets.scss; data: −views/labquali_homepage.xml; version bump)
- Delete: `static/src/lib/gsap.min.js`, `static/src/lib/ScrollTrigger.min.js`, `static/src/js/labquali_animations.js`, `static/src/scss/labquali_servicos.scss`

- [ ] **Step 1:** Criar `labquali_snippets.scss` — mover o conteúdo de `labquali_servicos.scss` **sem** o wrapper `.lq-servicos` (regras aplicam site-wide), e adicionar `s_banner`, `s_numbers`. Alvos: `s_banner`/`s_cover` (fundo navy Ink→Engineering, h1 Inter 900, `.lq-accent` laranja, badge), `s_numbers` (número laranja Inter 900 + label uppercase; painel navy quando `.o_cc`+navy), `s_three_columns .card` (flat + topo laranja 3px + hover lift), `s_image_text/s_text_image` (título Inter 800, bullets marcador laranja, img radius 14px), `s_quotes_carousel` (aspas navy), `s_call_to_action` (campo navy + botão laranja). Reduced-motion.

- [ ] **Step 2:** Enxugar `labquali_website.scss` — manter só: `@font-face` Inter, `:root{--lq-*}` (+ `--lq-fog`/`--lq-hairline`), `focus-visible`, navbar (`.o_main_nav`/`.navbar`), footer (`.lq-footer` só se ainda usado; senão remover). **Remover** `.lq-hero`, `.lq-services`, `.lq-diff`, `.lq-equip`, `.lq-clients`/`.lq-proof`, `.lq-cta`, `.lq-section-*`, `.lq-hero-*`, will-change block.

- [ ] **Step 3:** Manifest — `assets.web.assets_frontend`: remover as 3 linhas GSAP e `labquali_website.scss`? não: manter `labquali_website.scss` (chrome) + trocar `labquali_servicos.scss`→`labquali_snippets.scss`, remover gsap/scrolltrigger/animations. `data`: remover `"views/labquali_homepage.xml"`. `version` bump.

- [ ] **Step 4:** Deletar os 4 arquivos (3 GSAP/JS + labquali_servicos.scss).

- [ ] **Step 5:** Validar compile ambos SCSS (libsass) + `-u` exit 0:
```bash
for f in labquali_website labquali_snippets; do docker cp addons/afr_labquali_website/static/src/scss/$f.scss odoo_engenapp-web-1:/tmp/_$f.scss; docker exec odoo_engenapp-web-1 python3 -c "import sys;sys.path.insert(0,'/usr/lib/python3/dist-packages');import sass;print('$f OK',len(sass.compile(filename='/tmp/_$f.scss')))"; done
docker exec odoo_engenapp-web-1 /entrypoint.sh -u afr_labquali_website -d odoo-labquali --stop-after-init --no-http --log-level=warn 2>&1 | grep -iE "error|traceback|labquali" | grep -viE "Missing .license|not overriding|has no _description|ondelete"
```
Expected: ambos `OK <n>`; `-u` sem erro.

---

### Task 2: Remover a view code-driven da homepage do DB

**Files:** DB-only — deletar view `afr_labquali_website.labquali_homepage` (extension de website.homepage).

- [ ] **Step 1:** Deletar a view (senão continua injetando `.lq-` no `#wrap`):
```python
v=env.ref('afr_labquali_website.labquali_homepage', raise_if_not_found=False)
if v: v.unlink()
```
Via python in-container + `cr.commit()`.

- [ ] **Step 2:** Validar: `env.ref(...)` retorna None; `website.homepage` combined arch NÃO contém `lq-hero`.

---

### Task 3: Semear o arch da website.homepage com snippets nativos

**Files:** DB-only — arch_db da view `website.homepage`.

**Interfaces:** Consome imagens `/web/image/afr.labquali.homepage/1/{svc_*,dif_*,eqp_*}`.

- [ ] **Step 1:** Ler arch atual da `website.homepage` (wrapper `<t t-name>` + `<t t-call="website.layout">` + `#wrap`).
- [ ] **Step 2:** Compor arch: `#wrap` (oe_structure) com 7 snippets na ordem do spec (s_banner, s_numbers, s_three_columns serviços, s_three_columns diff ×2, s_three_columns equip compacto, s_numbers prova+tags, s_call_to_action), conteúdo do spec (QI/QO/QD), `o_animate o_anim_fade_in` nos blocos, imagens `/web/image`.
- [ ] **Step 3:** Escrever arch_db (`v.write({'arch': ...})`, `cr.commit()`).
- [ ] **Step 4:** Validar: presença de `s_banner`, 2×`s_numbers`, 3+`s_three_columns`, `s_call_to_action`, N×`/web/image`; ausência de `lq-hero`/`Itens exclusivos`.

---

### Task 4: Validar + commit git

- [ ] **Step 1:** Re-`-u` (garantir assets) + reler combined arch homepage (sem `.lq-hero`, com snippets).
- [ ] **Step 2:** Commit (agente haiku) — staging só: `labquali_website.scss`, `labquali_snippets.scss`, `__manifest__.py`, deleções (gsap/scrolltrigger/animations.js/labquali_servicos.scss), remoção de `views/labquali_homepage.xml`, e o plano. NÃO o arch (DB-only).
- [ ] **Step 3:** Handoff: usuário abre `/`.

## Self-Review
- Spec coverage: file changes(T1), remoção template+view(T1 manifest/T2), seed(T3), validação(T4). Coberto.
- ⚠️ `views/labquali_homepage.xml` removido do `data` (T1) mas o **arquivo** deve ser deletado ou mantido? Spec diz remover do manifest; deletar o arquivo é limpo. Deletar em T1 Step 4 junto (adicionar à lista).
- Sem placeholders de plano.
- Ressalva: arch de snippet autoral pode precisar retoque no builder.

## Notas
- Preview (T2/T3) DB-only, não-git.
- `/our-services` continua OK (marca agora global; wrapper `.lq-servicos` inofensivo).
