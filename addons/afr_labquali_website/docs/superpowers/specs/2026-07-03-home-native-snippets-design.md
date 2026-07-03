# Design — Home LabQuali em snippets nativos Odoo

Data: 2026-07-03
Módulo: `afr_labquali_website`
Superfície: `website.homepage` (rota `/`)

## Objetivo

Converter a homepage — hoje **code-driven** (inherit `website.homepage` +
xpath `#wrap` com seções custom `.lq-`, animações GSAP) — para **snippets
nativos do Odoo editáveis no builder** (abordagem A), consistente com a página
`/our-services`. Conteúdo passa a viver no builder; marca vive no git (SCSS).

## Decisões (confirmadas)

- **Full native** — todas as seções viram snippets nativos, editáveis no builder.
- **Drop GSAP** — contadores via `s_numbers` (nativo), reveals via `o_animate`
  (nativo). Remove os 118KB de GSAP do bundle (resolve débito P1 de perf).
- **SCSS unificado site-wide** — um `labquali_snippets.scss` marca os blocos
  Odoo globalmente (home + serviços + futuras páginas).
- **Conteúdo:** port do atual + consistência **IQ/OQ/PQ → QI/QO/QD**.
- **Cards com imagem** em Diferenciais e Equipamentos (não ícones).
- Conteúdo entregue como preview semeado no DB (não-git); marca no git.

### Restrição conhecida
Browser bloqueado (WSL) → SCSS validado por libsass + `-u`; render visual é o
usuário abrindo `/`. Instância multi-db sem db-filter (curl a `/` dá 303→/web).

## Mudanças de arquivo (git)

- **Remover** `views/labquali_homepage.xml` (inherit + xpath que injeta `.lq-`)
  do manifest `data`, e **deletar a view do DB** (senão continua injetando).
- **Manifest:** tirar `views/labquali_homepage.xml`; remover GSAP
  (`gsap.min.js`, `ScrollTrigger.min.js`, `labquali_animations.js`) dos assets;
  adicionar `labquali_snippets.scss`; **bump** version.
- **Deletar arquivos** vendored mortos: `static/src/lib/gsap.min.js`,
  `static/src/lib/ScrollTrigger.min.js`, `static/src/js/labquali_animations.js`.
- **SCSS refactor (2 arquivos finais):**
  - `labquali_website.scss` → só **chrome do site**: tokens `:root`,
    `@font-face`, navbar, footer, focus-visible. Remove todo
    `.lq-hero/.lq-services/.lq-diff/.lq-equip/.lq-clients/.lq-cta/.lq-proof`
    (morto após conversão).
  - `labquali_servicos.scss` → renomear/expandir para **`labquali_snippets.scss`**
    (sem scope `.lq-servicos` — site-wide): `s_banner`, `s_cover`, `s_numbers`,
    `s_three_columns`, `s_showcase`/`s_image_text`/`s_text_image`,
    `s_quotes_carousel`, `s_call_to_action`.

### Efeitos colaterais
- `/our-services` segue funcionando (mesmas classes de snippet, marca agora
  global; wrapper `.lq-servicos` fica inofensivo).
- GSAP fora de todas as páginas → perf.

## Mapa seção → snippet

| # | Seção | Snippet | Marca |
|---|---|---|---|
| 1 | Hero | `s_banner` | Fundo navy (Ink→Engineering), Inter 900, badge label, 2 CTAs |
| 2 | Stats | `s_numbers` | Contador nativo: +500 / 15+ / 100% |
| 3 | Serviços (4) | `s_three_columns` (4× col-lg-3) | Cards flat, topo laranja 3px, hover lift, imagem `/web/image` |
| 4 | Diferenciais (6) | `s_three_columns` ×2 (col-lg-4) | idem cards com imagem |
| 5 | Equipamentos (12) | `s_three_columns` compacto (col-lg-2) | cards menores imagem+label |
| 6 | Prova/Clientes | `s_numbers` + tags | 120+ / 12 / 5000+ + pills de segmento |
| 7 | CTA | `s_call_to_action` | Campo navy + botão laranja (Cold-Warm ✓) |

Reveals: blocos com `o_animate o_anim_fade_in` (nativo). `s_numbers` conta só.

## Conteúdo (port + QI/QO/QD)

### 1. Hero (`s_banner`)
- Badge: `✓ ISO 17025 · RDC 665/2022 · NR13`
- H1: Qualificação e Calibração de <span accent>Equipamentos</span> de Esterilização
- Sub: Laudos técnicos com rastreabilidade metrológica para autoclaves, estufas,
  câmaras de estabilidade e inspeções NR13.
- CTAs: **Solicitar Orçamento** → `/contactus` · **Ver Serviços** → `/our-services`

### 2. Stats (`s_numbers`)
- +500 Equipamentos/ano · 15+ Anos de experiência · 100% Laudos rastreáveis

### 3. Serviços (`s_three_columns`, 4 cards, imagens svc_*)
- **Qualificação QI/QO/QD** — Qualificação de instalação, operação e desempenho
  conforme RDC 665/2022 e boas práticas de fabricação.
- **Calibração de Sensores** — Termopares, termômetros, manômetros e sensores de
  pressão com rastreabilidade metrológica RBC/Inmetro.
- **Inspeção NR13** — Vasos de pressão, caldeiras e autoclaves conforme NR13 do
  MTE. Relatórios para fiscalização.
- **Mapeamento Térmico** — Mapeamento de temperatura em câmaras, estufas e
  geladeiras com malha de pontos e análise estatística.

### 4. Diferenciais (`s_three_columns` ×2, imagens dif_*)
Rastreabilidade Metrológica · Laudos em até 5 dias úteis · Equipe Especializada ·
Portal do Cliente · Atendimento Nacional · Conformidade Regulatória (descrições
atuais da home).

### 5. Equipamentos (`s_three_columns` compacto, imagens eqp_*)
Autoclaves a Vapor · Estufas de Esterilização · Câmaras de Estabilidade · Câmaras
Frias · Incubadoras · Geladeiras Farmacêuticas · Vasos de Pressão · Caldeiras ·
Liofilizadores · Túneis de Calor · Lavadoras Ultrassônicas · Termômetros e Sondas.

### 6. Prova/Clientes (`s_numbers` + tags)
- 120+ Instituições atendidas ⚠️placeholder · 12 Estados ⚠️placeholder · 5000+
  Qualificações realizadas
- Segmentos: Hospitais · Farmácias · Indústrias · Laboratórios

### 7. CTA (`s_call_to_action`)
- Título: Pronto para estar em conformidade?
- Texto: Solicite um orçamento sem compromisso. Nossa equipe técnica entra em
  contato em até 24 horas úteis.
- Botão: **Solicitar Orçamento Gratuito** → `/contactus`

## Preview no DB
Semear `arch_db` da `website.homepage` com os 7 blocos + conteúdo + `o_animate`.
Imagens via `/web/image/afr.labquali.homepage/1/{svc_*,dif_*,eqp_*}` (ACL público
ok). Snippets com `data-snippet`/`data-name` → editáveis no builder.

## Entregáveis
1. `labquali_snippets.scss` (git) + `labquali_website.scss` enxuto + manifest
   (−GSAP/−homepage.xml/+snippets, bump) + deleção dos 3 arquivos GSAP + remoção
   da view homepage do DB.
2. Preview semeado no arch da `website.homepage` (DB-only).
3. Este spec (git).

## Validação
- SCSS compila (libsass), HTML bem-formado, `-u` exit 0.
- Arch escrito; 7 snippets + contadores presentes; `.lq-hero`/demo ausentes.
- Render visual: **usuário** abre `/`.

## Fora de escopo
- Depoimentos na home (não entram).
- Números reais 120+/12 (placeholder até a equipe fornecer).
- "Laudos" → "Relatórios" na home (só foi pedido em /our-services).
