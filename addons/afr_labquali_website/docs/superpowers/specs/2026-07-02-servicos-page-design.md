# Design — Página de Serviços (`/our-services`) LabQuali

Data: 2026-07-02
Módulo: `afr_labquali_website`
Superfície: página `/our-services` (view `website.servicos`, menu "Serviços" seq 30)

## Objetivo

Transformar a página `/our-services` — hoje conteúdo **demo do tema** (blocos
`s_title`/`s_three_columns`/`s_references`/`s_quotes_carousel` com texto genérico
"Itens exclusivos", "Jane DOE · CEO") — numa página de serviços LabQuali dentro
das especificações de [DESIGN.md](../../../DESIGN.md) (North Star "The Certified
Blueprint"), usando ao máximo a **estrutura de blocos nativos do Odoo**.

## Decisões de arquitetura (confirmadas)

- **Abordagem A** — snippets nativos + SCSS de marca. O **conteúdo vive no
  builder** (editável pela equipe; NÃO versionado em git). O **SCSS de marca vai
  pro git** (durável, deployável por `-u`).
- **Conteúdo entregue como spec** (este doc) pra colar no builder — abordagem
  (ii). Além disso, um **preview é semeado no DB** (arch da página) pra
  visualização imediata; preview é DB-only, não-git.
- **Depoimentos: placeholder** marcado `[substituir]`.

### Restrição conhecida

Não é possível dirigir o editor OWL do Odoo deste ambiente (browser bloqueado no
WSL; agent-browser não interage com OWL). Logo: SCSS validado estaticamente
(libsass) e via `-u`; **render visual é verificado pelo usuário** abrindo
`/our-services`. Instância é multi-db sem db-filter (curl a `/` dá 303→/web);
não bloqueia o usuário com sessão.

## Estrutura da página (blocos Odoo, topo→base)

| # | Bloco Odoo | Papel | Marca (DESIGN.md) |
|---|---|---|---|
| 1 | `s_cover` | Banner "Serviços" + headline técnico | Fundo navy Ink→Engineering, Inter 900, palavra-valor laranja |
| 2 | `s_three_columns` | Os 3 serviços (título + desc curta) | Cards flat-by-default, borda hairline, topo laranja 3px, hover Navy Lift |
| 3 | `s_image_text` ×3 (alternado) | Detalhe por serviço (o que inclui + normas) | Imagem `/web/image` radius 14px, título Inter 800, bullets marcador laranja |
| 4 | `s_quotes_carousel` | Depoimentos (placeholder) | Aspas navy, atribuição laranja pequena |
| 5 | `s_call_to_action` | CTA "Solicitar Orçamento" | **Cold-Warm**: campo navy, botão laranja/branco |

Notas:
- **3 serviços** (Mapeamento Térmico removido do escopo) → `s_three_columns`
  (exatamente 3 colunas, já é o bloco do demo).
- `s_image_text` alternado (esq/dir) = padrão canônico Odoo, editável.
- CTA já nasce **Cold-Warm correto** (campo navy) — a home ainda tem o débito P1
  do `.lq-cta` laranja-cheio (fora deste escopo).

## Estratégia SCSS de marca

- **Arquivo novo:** `static/src/scss/labquali_servicos.scss`, adicionado ao
  `web.assets_frontend` no `__manifest__.py`. Separado do SCSS da home.
- **Escopo:** tudo sob wrapper **`.lq-servicos`** (classe no bloco/topo da
  página) — evita vazar overrides pra `/contactus` e outras páginas de snippet.
- **Reusa tokens `--lq-*`** e regras de DESIGN.md: Calibration Point (laranja só
  em acentos/CTA, ≤15%), Flat-By-Default (sombra só em hover, tingida de navy),
  Cold-Warm (navy domina), contraste AA verificado.
- **Alvos:** `s_cover` (fundo navy + tipografia), `s_three_columns .card` (flat +
  topo laranja 3px + hover lift), `s_image_text` (título Inter 800 + bullets
  laranja + imagem radius), `s_quotes_carousel` (aspas navy), `s_call_to_action`
  (campo navy + botão laranja).

## Spec de conteúdo (colar no builder)

### 1. Banner (`s_cover`)
- **H1:** Rastreabilidade <span accent>metrológica</span>, do sensor ao relatório.
  (acento laranja na palavra "metrológica")
- **Sub:** Qualificação, calibração e inspeção de equipamentos críticos com
  cadeia rastreável RBC/Inmetro.

### 2. `s_three_columns` — 3 serviços (título + desc curta)
- **Qualificação** — QI/QO/QD de autoclaves, estufas e câmaras conforme RDC
  665/2022 e BPF.
- **Calibração de Sensores** — Termopares, termômetros, manômetros e sensores de
  pressão com rastreabilidade RBC/Inmetro.
- **Inspeção NR13** — Vasos de pressão, caldeiras e autoclaves conforme NR13 do
  MTE, com relatório para fiscalização.

### 3. `s_image_text` ×3 — detalhe

**Qualificação** (imagem `svc_qualificacao`):
- **QI — Qualificação de Instalação:** verifica se o equipamento foi instalado
  conforme especificação do fabricante e requisitos de projeto.
- **QO — Qualificação de Operação:** comprova operação dentro dos parâmetros em
  toda a faixa de trabalho.
- **QD — Qualificação de Desempenho:** demonstra desempenho consistente e
  reprodutível na rotina, com carga real.
- Normas: RDC 665/2022 (ANVISA), BPF.

**Calibração de Sensores** (imagem `svc_calibracao`):
- Termopares, PT100, termômetros, manômetros, sensores de pressão/umidade.
- Cadeia rastreável até o BIPM via laboratórios acreditados RBC.
- Certificado com incerteza declarada.
- Normas: RBC/Inmetro, ISO/IEC 17025.

**Inspeção NR13** (imagem `svc_nr13`):
- Inspeção inicial, periódica e extraordinária de vasos de pressão, caldeiras e
  autoclaves.
- Relatório + prontuário para fiscalização.
- Normas: NR13 (MTE), ABNT aplicáveis.

### 4. `s_quotes_carousel` — placeholder `[substituir por depoimento real]`
- "[placeholder] Relatórios claros e no prazo; fiscalização aprovou sem
  ressalvas." — Gestor de Qualidade, Hospital [X]
- "[placeholder] Rastreabilidade impecável — auditoria RBC tranquila." —
  Responsável Técnico, Farmácia [Y]

### 5. `s_call_to_action`
- **Título:** Precisa de qualificação ou calibração?
- **Texto:** Solicite um orçamento sem compromisso. Retorno em até 24h úteis.
- **Botão:** Solicitar Orçamento → `/contactus`

## Preview no DB

Escrever `arch_db` da view `website.servicos` (COW, sem xmlid, website_id=1) com
os 5 snippets + conteúdo real acima + wrapper `.lq-servicos`. Snippets com
`data-snippet`/`data-name` corretos (base: arch demo existente + markup padrão
Odoo) → seguem editáveis no builder. Imagens via
`/web/image/afr.labquali.homepage/1/svc_*`.

**Ressalva:** arch de snippet autoral pode precisar de retoque no builder pra
ficar 100% "nativo-editável"; renderiza corretamente pro preview.

## Entregáveis

1. `static/src/scss/labquali_servicos.scss` (git) + registro no manifest + bump.
2. Este spec de conteúdo (git, docs/).
3. Preview semeado no arch da página (DB-only).

## Validação

- SCSS compila (libsass no container), HTML bem-formado, `-u` exit 0.
- Arch escrito; snippets reconhecíveis.
- Render visual: **usuário** abre `/our-services`.

## Fora de escopo

- Mapeamento Térmico (removido dos serviços).
- Consistência IQ/OQ/PQ → QI/QO/QD na **home** (follow-up separado).
- Débito P1 do `.lq-cta` laranja-cheio na home.
- Depoimentos reais (placeholder até a equipe fornecer).
