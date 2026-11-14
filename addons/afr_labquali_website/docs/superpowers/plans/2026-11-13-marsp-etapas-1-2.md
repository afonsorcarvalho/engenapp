# MARSP etapas 1 e 2 (marca, vitrine, autoclave ETO) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar localmente a marca MARSP (logo em SVG, cores, fontes), a vitrine `/marsp` e a página `/marsp/autoclave-eto` com abertura 3D dirigida pela rolagem.

**Architecture:** Builds estáticos em `static/demos/`, servidos por `controllers/demos.py`, que ganha o prefixo `marsp` e a rota índice. A marca fica em `static/demos/_marsp/` e é usada por todas as páginas MARSP. O 3D é renderizado no Blender (Windows) a partir da cena já usada no retrofit ETO, agora com a marca no painel, e vira sequência webp tocada pelo `scrollcraft.js`.

**Tech Stack:** Odoo 16 (container `odoo_engenapp-web-1`, porta 8083, db de dev `odoo-labquali`); HTML/CSS/JS sem framework + `scrollcraft.js`/`scrollcraft.css` (copiar de `static/demos/eto/`); Blender 5.2 (`/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe`, Cycles); Python + Pillow (`/home/afonso/docker/odoo_engenapp/.conda/bin/python3`); `agent-browser`.

**Spec:** `docs/superpowers/specs/2026-11-13-marsp-design.md` (ler inteira). Referências visuais em `docs/superpowers/specs/marsp/`: `logo-reference.svg` (forma aprovada, com máscaras), `logo-reference-generator.py`, `logo-cores.png`, `mockups.png`, `design-system.png`.

Todos os caminhos de repo são relativos a `addons/afr_labquali_website/` no monorepo `/home/afonso/docker/odoo_engenapp` (este módulo **não** é submodule; git roda na raiz do monorepo).

## Global Constraints

- Cores exatas: Tinta `#071E32`, Azul `#0A3D62`, Azul médio `#1E6091`, Laranja `#FF6B35`, Laranja escuro `#C2410C`, Ardósia `#5A7184`, Aço `#C6CDD4`, Fio `#E0E8F0`, Névoa `#EEF2F5`, Gelo `#F4F7FA`.
- Fontes: Michroma só no nome "MARSP" e em códigos de modelo (espaçamento 0,22em); Inter em todo o resto.
- Laranja só em botão/ação e no anel do logo; nunca como fundo de seção. Texto laranja sobre branco usa `#C2410C`.
- Texto em pt-BR, tom do `PRODUCT.md` (técnico, direto, sem hype). Sem rótulo em maiúsculas espaçadas acima de toda seção, sem cards idênticos repetidos, sem gradiente decorativo.
- Proibido em página, render, alt e meta: nomes de clientes (AMED, Point Suture, Medplast, Oximed, Steriliza), "Montroiz", TAGs de projeto (ex.: `VAP-EtO-001`), preços e valores de proposta.
- Dado técnico que não constar nos documentos de origem é omitido, não inventado. Só a autoclave mostra código (`MSP 1500-E`).
- Pedido de proposta = `mailto:labquali@labquali.com.br` com assunto citando o produto. Sem formulário.
- Logo: sem pixels, sem ponteiro, sem variações já descartadas.
- Scripts Blender ficam fora do repo, em `C:\Users\Afonso\scrollcraft_blender\` (`/mnt/c/Users/Afonso/scrollcraft_blender/`). Não modificar a pasta da proposta (`PROPOSTAS/POINT SUTURE/...`). Prévia de baixa resolução e inspeção visual (Read) antes de todo render final.
- Orçamento de peso: `static/demos/marsp-autoclave-eto/` ≤ 12 MB; `static/demos/marsp-vitrine/` ≤ 2 MB.
- Toda task que commita faz bump MINOR de `version` no `__manifest__.py` (partindo de `16.0.1.12.0`). Commit **local, sem push**, via agente `git-commit-push` (haiku) rodando na raiz do monorepo, só com os caminhos da task. Push e deploy remoto só com OK do user.
- Testes Odoo rodam pelo agente `test-runner` (HttpCase exige `--http-port 8999 --workers 0`; ver memória `reference_odoo_test_command`). Depois de mexer em controller: reiniciar o container.
- Não tocar em `static/src/js/lq_hero_scene.js` (mudança pendente do user, fora deste trabalho).

## Review Focus

1. **Diretório estático sombreado em produção**: o servidor remoto tem cópia antiga do módulo; assets precisam funcionar tanto por `/afr_labquali_website/static/demos/...` quanto por `/marsp/<pasta>/<arquivo>`. Teste na Task 2.
2. **Slug de produto ainda sem página** (`/marsp/gerador-de-vapor`, `/marsp/aquecedor-eto`, `/marsp/psicrometro`): deve dar 404 limpo, e a vitrine não pode linkar para eles. Testes nas Tasks 2 e 5.
3. **`prefers-reduced-motion` e JS desligado**: a página do produto precisa mostrar imagem estática, todo o texto e a ficha. Teste na Task 4.
4. **Celular (390 px de largura)**: sem rolagem horizontal, logo legível, sequência carregando versão leve. Verificação na Task 6.
5. **Vazamento de dado proibido** copiado dos documentos de origem. Teste de lista negra na Task 6.

---

### Task 1: Arquivos da marca

**Files:**
- Create: `static/demos/_marsp/logo-symbol.svg`, `logo-light.svg`, `logo-dark.svg`, `logo-mono.svg`, `favicon.svg`, `marsp.css`
- Create: `tests/test_marsp.py` (classe `TestMarspBrand`), registrar em `tests/__init__.py`
- Modify: `__manifest__.py` (version → `16.0.1.13.0`)

**Interfaces:**
- Produces: URLs `/afr_labquali_website/static/demos/_marsp/<arquivo>`; em `marsp.css`, variáveis `--m-ink`, `--m-navy`, `--m-mid`, `--m-orange`, `--m-orange-deep`, `--m-slate`, `--m-steel`, `--m-hair`, `--m-pale`, `--m-fog`, `--m-r-sm:6px`, `--m-r-md:10px`, `--m-r-lg:14px`, `--m-r-pill:20px`; classes `.m-wordmark` (Michroma, 0,22em), `.m-btn`, `.m-btn--primary`, `.m-btn--ghost`, `.m-btn--ghost-dark`, `.m-link`, `.m-tag`, `.m-spec` (tabela de ficha), `.m-sign` (faixa da parceria); `@import` de Inter e Michroma do Google Fonts.

- [ ] **Step 1: Teste que falha.** `TestMarspBrand(TransactionCase)` lê os arquivos com `get_module_resource("afr_labquali_website", "static", "demos", "_marsp", nome)` e verifica: os 6 arquivos existem; nenhum SVG contém `<mask`, `<clipPath`, `<image`, `<script` nem `font-family` (texto do nome convertido em path); `logo-symbol.svg` e `logo-light.svg` contêm `#0A3D62` e `#FF6B35`; `logo-dark.svg` contém `#FFFFFF` (ou `#fff`) e `#FF6B35` e não contém `#0A3D62`; `logo-mono.svg` usa só `currentColor`; `marsp.css` contém cada um dos 10 hex das Global Constraints e as strings `Michroma` e `Inter`.
- [ ] **Step 2: Rodar e ver falhar** (agente `test-runner`, tag `/afr_labquali_website:TestMarspBrand`).
- [ ] **Step 3: Gerar o símbolo com geometria resolvida.** Forma (caixa 120×120, centro 60,60): aro = círculo r 35 menos círculo r 20; anel = elipse rx 58, ry 12,5 menos elipse rx 37,12, ry 8,0, girado −36°; folga 2,2. A metade da frente do anel (y > 0 no eixo do anel) é desenhada inteira e recorta o aro com a folga; a metade de trás só aparece fora do círculo de raio 37,2. Calcular as booleanas com `shapely` num venv em scratchpad e emitir `<path>` (curvas amostradas com ≥ 96 pontos por arco ou ajustadas); `viewBox` justo ao desenho com a área livre da spec. `logo-light`/`logo-dark`/`logo-mono` = símbolo + "MARSP" em Michroma convertido em path (fonttools/`fontTools.pens.svgPathPen` a partir do TTF do Google Fonts), nome com altura ≈ 0,42 da altura do símbolo e espaço de 0,12. `favicon.svg` = símbolo invertido sobre quadrado `#071E32` com cantos 22%.
- [ ] **Step 4: Conferir contra a referência.** Rasterizar `docs/superpowers/specs/marsp/logo-reference.svg` e `logo-symbol.svg` no mesmo enquadramento 480×480 (agent-browser ou `rsvg-convert`) e comparar com Pillow: diferença média por pixel < 2%. Abrir os dois PNGs com Read e conferir a olho: anel passa pela frente embaixo à esquerda, por trás em cima à direita, folga visível.
- [ ] **Step 5: Escrever `marsp.css`** com as variáveis e classes do bloco Interfaces, medidas da spec (seção "Tipografia e medidas" e "Componentes").
- [ ] **Step 6: Rodar o teste e ver passar.**
- [ ] **Step 7: Commit local** `feat(afr_labquali_website): MARSP brand assets and tokens`.

### Task 2: Rotas `/marsp` no controller

**Files:**
- Modify: `controllers/demos.py`
- Create: `static/demos/marsp-vitrine/index.html` e `static/demos/marsp-autoclave-eto/index.html` (esqueleto mínimo: `<title>`, `<h1>`, link para `marsp.css`; conteúdo real vem nas Tasks 4 e 5)
- Modify: `tests/test_marsp.py` (classe `TestMarspRoutes(HttpCase)`), `__manifest__.py` (→ `16.0.1.14.0`)

**Interfaces:**
- Produces: `GET /marsp` → `static/demos/marsp-vitrine/index.html`; `GET /marsp/<slug>` → `static/demos/marsp-<slug>/index.html` para slug em `MARSP = ("autoclave-eto",)`; `GET /marsp/<pasta>/<path:fname>` → arquivo de `static/demos/<pasta>/` para pasta em `("marsp-vitrine", "marsp-autoclave-eto", "_marsp")`. Constante `MARSP` é a lista de slugs com página; etapas futuras só acrescentam itens.
- Regra para os autores de HTML: assets da própria página por caminho relativo (`seq/f_0001.webp`); assets da marca por caminho absoluto `/afr_labquali_website/static/demos/_marsp/...` (o controller troca o prefixo quando o estático está sombreado).

- [ ] **Step 1: Testes que falham** em `TestMarspRoutes`:
  - `/marsp` → 200 e contém `<h1`; `/marsp/autoclave-eto` → 200.
  - `/marsp/gerador-de-vapor`, `/marsp/aquecedor-eto`, `/marsp/psicrometro`, `/marsp/eto`, `/marsp/caldeira` → 404.
  - `/retrofit/autoclave-eto`, `/qualificacao/marsp-vitrine` → 404.
  - `/marsp/_marsp/logo-symbol.svg` → 200, `Content-Type` `image/svg+xml`; `/marsp/_marsp/marsp.css` → 200, `text/css`.
  - `/marsp/marsp-autoclave-eto/%2e%2e/eto/index.html` → 404 (mesmo padrão de `test_traversal_rejected` em `tests/test_retrofit_eto.py`).
  - Irmãos intactos: `/retrofit/eto`, `/inspecao/caldeira`, `/qualificacao/autoclave` → 200.
  - Sombreamento: com `unittest.mock.patch` de `controllers.demos._static_dir_is_ours` retornando `False` e `_html_cache` limpo, o HTML de `/marsp/autoclave-eto` não contém `/afr_labquali_website/static/demos/` e contém `/marsp/_marsp/marsp.css`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.** Generalizar `_page_html` para receber a pasta (`folder`) separada do slug; `PREFIXES["marsp"]`; rota índice `/marsp` (sem barra final; `/marsp/` redireciona 301 para `/marsp`); a rota de asset do prefixo `marsp` valida a pasta contra a lista acima em vez dos slugs. Não mudar o comportamento dos três prefixos existentes.
- [ ] **Step 4: Reiniciar o container, rodar `TestMarspRoutes` + `TestRetrofitEto` + `TestDemoCaldeira`, ver passar.**
- [ ] **Step 5: Commit local** `feat(afr_labquali_website): /marsp routes`.

### Task 3: Renders da autoclave com a marca

**Files:**
- Create (fora do repo): `/mnt/c/Users/Afonso/scrollcraft_blender/marsp_autoclave.py`, `anim_marsp_hero.py`, `anim_marsp_abre.py`, `marsp_painel.png`
- Create: `static/demos/marsp-autoclave-eto/seq/f_0001.webp … f_0150.webp`, `seqa/a_0001.webp … a_0070.webp`, `seq-m/` e `seqa-m/` (versões 960 px para celular), `still-capa.webp`, `g1.webp … g4.webp`; `static/demos/marsp-vitrine/autoclave.webp`
- Modify: `__manifest__.py` (→ `16.0.1.15.0`)

**Interfaces:**
- Consumes: `logo-symbol.svg`/`logo-mono.svg` da Task 1 (rasterizar para a textura do painel).
- Produces: sequência `seq/f_{iiii}.webp` (150 quadros, 1600×900): órbita lenta 3/4 frontal → lateral com o painel da marca legível → frente. Sequência `seqa/a_{iiii}.webp` (70 quadros): carenagem some/abre e a porta guilhotina sobe, revelando a câmara. `still-capa.webp` = quadro para reduced-motion e `og:image`. `g1..g4.webp` = galeria (porta aberta com câmara; plataforma de utilidades; painel/IHM; vista traseira/segunda porta). `marsp-vitrine/autoclave.webp` = 3/4 frontal sobre fundo `#071E32`, 1400 px.

- [ ] **Step 1: Ler** `eto_maquina.py` e `anim_eto_hero.py` (cena do retrofit, máquina sem marca) e `PROPOSTAS/POINT SUTURE/Proposta Autoclave ETO 1500L Montroiz/blender/cena.py` (bloco do painel de marca) em `/mnt/c/Users/Afonso/...`. `marsp_autoclave.py` reaproveita a máquina nova (sem painel velho, sem giroflex) e recoloca o painel lateral.
- [ ] **Step 2: Textura `marsp_painel.png`** (400×2000): fundo inox claro, símbolo MARSP no topo (aro `#27323D`, anel `#FF6B35`), "MARSP" em Michroma, "AUTOCLAVE ETO" na vertical, como no mockup 1 de `docs/superpowers/specs/marsp/mockups.png`. Sem "Montroiz".
- [ ] **Step 3: Render de prova** 960×540, 32 samples, de 3 poses (frente 3/4, lateral do painel, porta aberta). Abrir com Read: marca legível e não espelhada, ambiente em tons de `#071E32`, sem artefato. Corrigir até passar.
- [ ] **Step 4: Renders finais** em background com log (`seq` 150 quadros, `seqa` 70, stills), 48 samples. Conferir contagem de arquivos e ausência de `Traceback` no log.
- [ ] **Step 5: Converter** com `/mnt/c/Users/Afonso/scrollcraft_blender/to_webp.py` para as pastas do repo; gerar as versões `-m`. `du -sh static/demos/marsp-autoclave-eto` ≤ 11 MB (sobra 1 MB para HTML/CSS/JS).
- [ ] **Step 6: Commit local** `feat(afr_labquali_website): MARSP autoclave render sequences`.

### Task 4: Página `/marsp/autoclave-eto`

**Files:**
- Modify: `static/demos/marsp-autoclave-eto/index.html`
- Create: `static/demos/marsp-autoclave-eto/scrollcraft.js`, `scrollcraft.css` (cópias de `static/demos/eto/`), `page.css`
- Modify: `tests/test_marsp.py` (classe `TestMarspAutoclave(HttpCase)`), `__manifest__.py` (→ `16.0.1.16.0`)

**Interfaces:**
- Consumes: sequências e stills da Task 3; `marsp.css` e logos da Task 1; rotas da Task 2. API do motor: `data-sc-act`, `data-sc-span`, `data-sc-stage`, `data-sc-sequence="seq/f_{iiii}.webp:150:1"`, `data-sc-cue` (ver cabeçalho de `scrollcraft.js` e o uso em `static/demos/eto/index.html`).
- Produces: seções com ids `inicio`, `destaques`, `galeria`, `ficha`, `linha`, `proposta`.

Estrutura (modelo: página de um carro):
1. Topo fixo: logo invertido (link para `/marsp`), "Linha MARSP", botão "Pedir proposta".
2. `#inicio`: ato `scrub` com `seq/`; nome "Autoclave ETO", código `MSP 1500-E` em Michroma, uma frase; três frases curtas em `data-sc-cue` ao longo da órbita.
3. `#destaques`: ato `scrub` com `seqa/`; quatro destaques, um por momento da abertura: câmara de 1500 L em inox 316L; dupla porta guilhotina vertical (1000 × 1000 × 1500 mm); automação AFR com ciclo rastreável; qualificação LabQuali entregue no mesmo fornecimento.
4. `#galeria`: `g1..g4.webp` com legenda.
5. `#ficha`: tabela `.m-spec` com os dados que constam em `proposta.md` (seções de escopo/especificação), sem preço, cliente ou fabricante.
6. `#linha`: os outros três produtos como "em breve", sem link.
7. `#proposta`: fundo `#071E32`, botão `mailto:labquali@labquali.com.br?subject=Proposta%20MARSP%20-%20Autoclave%20ETO%20MSP%201500-E`; faixa `.m-sign`.

- [ ] **Step 1: Testes que falham** em `TestMarspAutoclave`: 200; contém `MSP 1500-E`, `Autoclave ETO`, `1000 × 1000 × 1500 mm`, `316L`; contém os seis ids; contém `data-sc-sequence="seq/f_{iiii}.webp` e `seqa/a_{iiii}.webp`; contém o `mailto:` exato acima; contém `prefers-reduced-motion` no CSS servido (`/marsp/marsp-autoclave-eto/page.css`) e um `<img` com `still-capa.webp` dentro de `<noscript>` ou como fallback; `/marsp/marsp-autoclave-eto/seq/f_0001.webp` e `/seqa/a_0070.webp` → 200 `image/webp`; não contém `href="/marsp/gerador-de-vapor"`, `/marsp/aquecedor-eto`, `/marsp/psicrometro`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Escrever a página.** Copy a partir de `proposta.md`, obedecendo às Global Constraints; passar o texto pela skill `anthropic-skills:humanizer`. Em `prefers-reduced-motion: reduce` e sem JS, os atos viram blocos estáticos com `still-capa.webp` e todo o texto visível. Em telas ≤ 760 px, as sequências apontam para `seq-m/` e `seqa-m/`.
- [ ] **Step 4: Rodar os testes e ver passar.**
- [ ] **Step 5: Conferir no navegador** com `agent-browser` em `http://localhost:8083/marsp/autoclave-eto` (1440×900): capturas no topo, no meio de cada ato e no fim; conferir com Read que a sequência anima, os destaques entram no momento certo e nada sobrepõe o texto.
- [ ] **Step 6: Commit local** `feat(afr_labquali_website): MARSP autoclave ETO product page`.

### Task 5: Vitrine `/marsp`

**Files:**
- Modify: `static/demos/marsp-vitrine/index.html`
- Create: `static/demos/marsp-vitrine/page.css`, `sil-gerador.svg`, `sil-aquecedor.svg`, `sil-psicrometro.svg`
- Modify: `tests/test_marsp.py` (classe `TestMarspVitrine(HttpCase)`), `__manifest__.py` (→ `16.0.1.17.0`)

**Interfaces:**
- Consumes: `marsp-vitrine/autoclave.webp` (Task 3), marca (Task 1), rotas (Task 2).
- Produces: seções `inicio`, `linha`, `parceria`, `proposta`.

Estrutura (modelo: home de montadora):
1. `#inicio`: fundo `#071E32`, logo invertido grande, título "Equipamentos para esterilização por óxido de etileno." e uma frase sobre a linha; botão "Conhecer a linha" (âncora `#linha`).
2. `#linha`: quatro modelos lado a lado (rolagem horizontal no celular). Autoclave: `autoclave.webp`, `MSP 1500-E`, uma frase, link `/marsp/autoclave-eto`. Os outros três: silhueta escura em contraluz (SVG próprio de cada equipamento: gerador = vaso vertical com tubulação; aquecedor = casco-e-tubo horizontal sobre berços; psicrômetro = haste de sensor com cabeçote), nome, uma frase do que faz no ciclo ETO, "em breve", **sem link**.
3. `#parceria`: AFR (São Luís, MA) projeta e automatiza; LabQuali (São Paulo, SP) qualifica e valida. Texto corrido, sem cards gêmeos.
4. `#proposta`: `mailto:labquali@labquali.com.br?subject=Proposta%20MARSP`; faixa `.m-sign`.

- [ ] **Step 1: Testes que falham** em `TestMarspVitrine`: 200; contém os quatro ids; contém `Autoclave ETO`, `Gerador de vapor`, `Aquecedor de gás ETO`, `Psicrômetro`; exatamente um `href="/marsp/autoclave-eto"` dentro de `#linha` e nenhum `href` para os outros três slugs; `em breve` aparece 3 vezes (case-insensitive); as três silhuetas respondem 200 `image/svg+xml`; contém o `mailto:` exato.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Escrever a página e as silhuetas.** Mesmo cuidado de copy (humanizer). Página sem scrollcraft: é estática, com transições CSS simples e respeito a `prefers-reduced-motion`.
- [ ] **Step 4: Rodar os testes e ver passar.**
- [ ] **Step 5: Conferir no navegador** (`http://localhost:8083/marsp`, 1440×900 e 390×844) com capturas lidas via Read.
- [ ] **Step 6: Commit local** `feat(afr_labquali_website): MARSP showcase page`.

### Task 6: Fechamento

**Files:**
- Modify: `tests/test_marsp.py` (classe `TestMarspGuards`), `__manifest__.py` (→ `16.0.1.18.0`), o que os achados exigirem

- [ ] **Step 1: Testes de guarda.** Para os HTML e CSS de `marsp-vitrine`, `marsp-autoclave-eto` e `_marsp`: nenhuma ocorrência (case-insensitive) de `montroiz`, `amed`, `point suture`, `medplast`, `oximed`, `steriliza`, `VAP-EtO`, `R$`; soma dos arquivos de `marsp-autoclave-eto` ≤ 12 MB e de `marsp-vitrine` ≤ 2 MB (via `os.walk` no caminho de `get_module_resource`).
- [ ] **Step 2: Rodar a suíte inteira do módulo** (`/afr_labquali_website`) e ver passar.
- [ ] **Step 3: Passada de celular** com `agent-browser` em 390×844 nas duas páginas: sem rolagem horizontal (`document.documentElement.scrollWidth <= innerWidth`), logo legível, sequência `-m` carregada (conferir na aba de rede/`performance.getEntriesByType('resource')`). Corrigir o que falhar.
- [ ] **Step 4: Passada de reduced-motion** (`agent-browser` com emulação, ou `matchMedia` forçado): tudo legível sem animação.
- [ ] **Step 5: Commit local** `test(afr_labquali_website): MARSP guards and mobile fixes`.
- [ ] **Step 6: Relatar** ao orquestrador as URLs locais, o tamanho final de cada pasta e a lista de dados técnicos usados com a origem de cada um (para o user revisar depois).
