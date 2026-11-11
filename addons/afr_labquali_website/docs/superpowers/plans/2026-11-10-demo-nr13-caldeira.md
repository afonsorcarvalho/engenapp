# Demo "Inspeção NR-13 em caldeira" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quinta página de demo do site Labquali: scroll cinematográfico com caldeira flamotubular em 3D, dois clímax (ultrassom de espessura, ensaio de válvula de segurança em bancada) e relatório, servida em `/qualificacao/caldeira`.

**Architecture:** Modelo procedural da caldeira em Blender (`caldeira.py`) + dois scripts de animação que renderizam sequências PNG, convertidas em webp por script Python (Pillow). Página estática em `static/demos/caldeira/` autorada em HTML semântico sobre a engine `scrollcraft.js` (copiada do demo autoclave), com overlays SVG dirigidos pela variável `--sc-p` do ato. Controller existente ganha o slug.

**Tech Stack:** Blender 5.2.2 (Windows, via `/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe`, Cycles OptiX), Python 3 + Pillow 11 (WSL, `/home/afonso/docker/odoo_engenapp/.conda/bin/python3`), vanilla JS/SVG, Odoo 16 (container, porta 8083), `agent-browser` para verificação.

**Spec:** `addons/afr_labquali_website/docs/superpowers/specs/2026-11-10-demo-nr13-caldeira-design.md` (ler inteira). Dados normativos: `docs/superpowers/research/2026-11-10-nr13-caldeiras.md`.

## Global Constraints

- Copy em pt-BR; termo "PLH" (Profissional Legalmente Habilitado); nunca "PH".
- Proibido no copy: teste hidrostático periódico obrigatório; "aposentadoria aos 25 anos"; categoria por PMTA; prazo ≠ 12 meses para cat. B. Cada afirmação normativa cita o subitem (ex.: "13.4.4.4").
- Sem marca de fabricante em modelo 3D ou texto. Nota única: "Dados ilustrativos de uma caldeira fictícia".
- Placa: nº ordem 2014-0471, ano 2014, PMTA 10,5 kgf/cm², 2.000 kg/h, 55 m², ASME I ed. 2010, operação 7,0 kgf/cm², Categoria B.
- Peso total de `static/demos/caldeira/` ≤ 12 MB. `seq/` 150 frames 1920×1080 webp; `seqv/` ~80 frames 1280×720 webp.
- Visual: mesmo tema do demo autoclave (fundo escuro, acento `#ff6a2b`, fonte mono para números, `logo-dark.svg`).
- Bump `__manifest__.py` 16.0.1.7.1 → 16.0.1.8.0 no commit que adiciona a página. Commits via agente `git-commit-push` (haiku), a partir do monorepo (`afr_labquali_website` NÃO é submodule). Não fazer push/deploy remoto sem OK do user.
- Blender roda no Windows; chamar o exe a partir do WSL com paths Windows (`C:\Users\Afonso\scrollcraft_blender\...`). Renders longos em background com log em `render*.log`. Preview sempre antes de render final.

## Review Focus

1. Pops da válvula (frames) × curva SVG desalinhados: reader vê disco levantar antes/depois do pico. Teste em Task 6 (índices de frame constantes compartilhados e verificados).
2. Pontos de ultrassom fora da geometria quando a viewport muda (aspect-ratio ≠ 16:9, mobile): posições em % do frame renderizado via `object-fit: cover` + mesma caixa. Teste em Task 5.
3. Página pesada no mobile (engine carrega toda sequência): poster + `loading` progressivo já existem na engine; orçamento 12 MB verificado em Task 7.
4. Copy normativo errado: grep de termos proibidos em Task 7.
5. `prefers-reduced-motion`: frames param no poster e textos aparecem; Task 7 testa com emulação.

---

### Task 1: Modelo procedural da caldeira (`caldeira.py`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/caldeira.py`
- Reference: `autoclave.py` (materiais `principled`, `brushed`; bloco `# ---- stage` que `anim.py` descarta), `ref_caldeira/*.png`, foto 2 (caldeira com 2 válvulas).

**Interfaces:**
- Produces: script que, importado por `exec` até o marcador `# ---------------------------------------------------------------- stage`, cria no cenário objetos nomeados: `shell` (casco), `head_front`, `head_rear`, `door_front` (porta frontal articulada, origem na dobradiça, eixo Z), `burner`, `stack`, `skid`, `valve_a` e `valve_b` (empties pais das válvulas, `valve_b` é a de 10,5 ajustada no topo traseiro), `gauge`, `level_glass`, `pump`, `room_floor`, `room_wall`, `window_light`, e constantes `SHELL_R`, `SHELL_L`, `SHELL_Z` (raio, comprimento, altura do eixo), `VALVE_B_POS` (Vector). Também define a função `build_valve(name, loc, cut=False)` que constrói uma válvula de segurança flangeada (corpo angular, flange de entrada e saída com 8 parafusos, castelo cilíndrico, mola helicoidal visível quando `cut=True`, haste, disco, alavanca) e devolve o empty pai; com `cut=True` a metade +X do corpo/castelo é removida (boolean) e mola/haste/disco ficam expostos. Objetos internos da válvula nomeados `{name}_spring`, `{name}_stem`, `{name}_disc`.
- Materiais: chapa de acabamento da caldeira cinza-azulado escuro (`(0.18,0.20,0.23)` metal 0.6), válvulas em fundido cinza claro (foto 1), partes internas em aço polido.

- [ ] **Step 1: Escrever `caldeira.py`** com cabeçalho igual ao de `autoclave.py` (argv `<out.png> [samples]`, `read_factory_settings`), geometria acima, materiais, e bloco `# ---- stage` com câmera 3/4 frontal + render still 1600×900 (não 1600×1600).

- [ ] **Step 2: Render de prova rápido**

Run (WSL):
```bash
cd /mnt/c/Users/Afonso/scrollcraft_blender && "/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P caldeira.py -- "C:\Users\Afonso\scrollcraft_blender\out\caldeira_test.png" 32 > caldeira_test.log 2>&1; tail -3 caldeira_test.log
```
Expected: `caldeira_test.png` existe; log sem Traceback.

- [ ] **Step 3: Inspecionar `out/caldeira_test.png`** (Read tool) contra checklist: casco horizontal com isolamento, queimador frontal, porta frontal com dobradiças, chaminé traseira, 2 válvulas no topo, manômetro, visor de nível, skid, chão/parede/luz lateral, sem texto/marca. Ajustar e repetir até passar.

- [ ] **Step 4: Render de prova da válvula em corte**: script temporário `dbg_valve.py` que importa `caldeira.py` até `stage`, chama `build_valve("vtest", (0,0,0), cut=True)`, câmera a 0,6 m, render 1200×1200, 32 samples. Inspecionar: mola, haste, disco e sede visíveis; flange com parafusos; alavanca.

- [ ] **Step 5: Commit** (`caldeira.py` fica fora do monorepo; registrar no monorepo apenas o doc): nada a commitar nesta task além de anotar no plano que o script existe. Prosseguir.

### Task 2: Sequência principal do hero (`anim_caldeira.py` → `seq/`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/anim_caldeira.py`
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/to_webp.py`
- Create (output): `addons/afr_labquali_website/static/demos/caldeira/seq/f_0001..f_0150.webp`, `addons/afr_labquali_website/static/demos/caldeira/still/interno_1.webp`, `still/interno_2.webp`

**Interfaces:**
- Consumes: Task 1 objetos/constantes.
- Produces: 150 frames. Marcos de câmera (frame): 1–45 orbita 3/4 frontal → lateral (válvulas visíveis no topo em 30–45); 46–95 aproxima do costado; 96–130 porta frontal abre (`door_front` rotação 0 → 110°); 131–150 câmera assenta no frame final: costado à direita, espelho frontal e boca da fornalha à esquerda, tudo nítido (f/16). Frame 150 é o fundo das seções 2 e 4. `to_webp.py <src_dir> <dst_dir> [--size WxH] [--quality Q]`: converte PNG → webp com Pillow, imprime média de KB/frame.

- [ ] **Step 1: Escrever `anim_caldeira.py`** nos moldes de `anim.py` (argv `<outdir> <samples> <start> <end> [preview]`, `SC_MODEL` fixo `caldeira.py`, mesmo bloco de render Cycles/OptiX/AgX, 1920×1080, preview 960×540 com `frame_step 21`). Keyframes de câmera e `door_front` nos marcos acima; vapor leve nos purgadores via partículas/volume barato (opcional, pode cair se custar > 20 % do tempo de render).

- [ ] **Step 2: Preview**

Run:
```bash
cd /mnt/c/Users/Afonso/scrollcraft_blender && "/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P anim_caldeira.py -- "C:\Users\Afonso\scrollcraft_blender\prevK" 24 1 150 1 > prevK.log 2>&1; ls prevK | wc -l
```
Expected: 8 PNGs (1, 22, 43, ..., 148). Inspecionar cada um contra os marcos; no último, espelho + boca da fornalha + costado visíveis.

- [ ] **Step 3: Render final em background**

Run com `run_in_background`: mesmo comando sem o `1` final, outdir `C:\Users\Afonso\scrollcraft_blender\seqK`, samples 48, log `renderK.log`. Ao terminar: `ls seqK | wc -l` → 150.

- [ ] **Step 4: Escrever `to_webp.py`** (Pillow; `--quality` default 80; `--size` opcional com resample LANCZOS) e converter:
```bash
/home/afonso/docker/odoo_engenapp/.conda/bin/python3 /mnt/c/Users/Afonso/scrollcraft_blender/to_webp.py /mnt/c/Users/Afonso/scrollcraft_blender/seqK /home/afonso/docker/odoo_engenapp/addons/afr_labquali_website/static/demos/caldeira/seq
du -sh addons/afr_labquali_website/static/demos/caldeira/seq
```
Expected: 150 arquivos, ≤ 7,5 MB. Se maior, baixar quality para 72.

- [ ] **Step 5: Dois stills do exame interno** (`still/interno_1.webp`: close do espelho com tubos e solda tubo-espelho; `still/interno_2.webp`: boca da fornalha), 1280×720, via script `still_caldeira.py` que reaproveita o modelo com a porta aberta. Converter com `to_webp.py --size 1280x720`.

- [ ] **Step 6: Commit** via agente `git-commit-push` (cwd monorepo): `addons/afr_labquali_website/static/demos/caldeira/seq`, `still`. Mensagem: `feat(afr_labquali_website): boiler hero render sequence for NR-13 demo`.

### Task 3: Sequência da válvula em bancada (`anim_valvula.py` → `seqv/`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/anim_valvula.py`
- Create (output): `addons/afr_labquali_website/static/demos/caldeira/seqv/v_0001..v_0080.webp`

**Interfaces:**
- Consumes: Task 1 `build_valve(..., cut=True)`, cena da caldeira (fundo desfocado, `valve_b` oculta e bocal vazio).
- Produces: 80 frames 1280×720. **Constantes de sincronismo** (frame 1-based, a serem copiadas para o HTML na Task 6): `CUT_START=28` (corte termina de revelar em 36), `POP1=38`, `POP2=54`, `POP3=70`, cada pop com disco levantando em 3 frames, aberto 3, reassentando 4; jato visível enquanto aberto. Câmera: 1–27 desliza da caldeira até a bancada e enquadra a válvula inteira; 28–80 fixa em close 3/4 com o corte voltado para a câmera.

- [ ] **Step 1: Escrever `anim_valvula.py`**: bancada (tampo metálico, cabeçote de teste com flange, manômetro padrão, mangueira), válvula montada `cut=True` com o corte animado por keyframe de visibilidade/boolean a partir de `CUT_START`; shape key ou keyframe de posição em `vtest_disc`/`vtest_stem` e escala Z em `vtest_spring` nos pops; jato = cone de partículas/volume emissivo branco só nos frames abertos. Render 1280×720, preview 640×360.

- [ ] **Step 2: Preview** (`prevV`, step 10 → 8 frames) e inspeção: frame 40 mostra disco levantado + jato; frame 48 reassentado; corte legível.

- [ ] **Step 3: Render final** em background (`seqV`, 48 samples, `renderV.log`); conferir 80 PNGs.

- [ ] **Step 4: Converter** com `to_webp.py` para `static/demos/caldeira/seqv/` (prefixo `v_`); `du -sh` ≤ 3 MB.

- [ ] **Step 5: Commit** via agente: `feat(afr_labquali_website): safety valve bench test sequence`.

### Task 4: Página: scaffold, hero, enquadramento, etapas

**Files:**
- Create: `addons/afr_labquali_website/static/demos/caldeira/index.html`
- Copy: `static/demos/autoclave/scrollcraft.js` → `static/demos/caldeira/scrollcraft.js`; `static/demos/autoclave/logo-dark.svg` → `static/demos/caldeira/logo-dark.svg`
- Modify: `addons/afr_labquali_website/controllers/demos.py:22` (`DEMOS` += `"caldeira"`)
- Modify: `addons/afr_labquali_website/__manifest__.py:4` (16.0.1.8.0)
- Test: `addons/afr_labquali_website/tests/test_demo_caldeira.py` (novo; módulo pode não ter `tests/` — criar `tests/__init__.py` importando o teste)

**Interfaces:**
- Produces: seções com ids `inicio` (scrub, span 5.2, canvas `data-sc-sequence="seq/f_{iiii}.webp:150:1"`), `placa` (pin, span 2), `etapas` (flow), e placeholders vazios `<section id="ultrassom">`, `<section id="valvula">`, `<section id="relatorio">` para as tasks 5–7. CSS: copiar bloco de variáveis/base do autoclave; adicionar `.plate` (placa), `.steps` (6 passos).

- [ ] **Step 1: Teste de controller** `test_demo_caldeira.py` (`HttpCase`, tag `post_install`): `GET /qualificacao/caldeira` → 200, body contém `Inspeção de segurança NR-13` e `Categoria B`; `GET /qualificacao/caldeira/seq/f_0001.webp` → 200 `image/webp`; `GET /qualificacao/caldeira/../autoclave/index.html` → 404.

- [ ] **Step 2: Rodar o teste e ver falhar** (slug ausente → 404). Via agente `test-runner`, módulo `afr_labquali_website`, tag `test_demo_caldeira`. Comando de referência em memória `reference_odoo_test_command.md`.

- [ ] **Step 3: Implementar**: slug no controller; `index.html` com `<head>` igual ao autoclave (preload `seq/f_0001.webp`, favicon, fontes), barra superior com logo e link "Voltar ao site", seção `inicio` com poster + canvas + `hero__copy` (título "Inspeção de segurança NR-13", subtítulo "Feita por engenheiro legalmente habilitado (PLH), com ART. Relatório em até 60 dias.") e 3 beats em `data-sc-cue` (0.30–0.50 "Duas válvulas de segurança, abertura ≤ PMTA — 13.4.1.2"; 0.55–0.75 "Costado: onde a espessura conta"; 0.82–0.98 "Porta aberta: espelho e fornalha, o lado fogo"); seção `placa` com placa HTML (7 campos em `data-sc-cue` escalonados) e chip "Categoria B — inspeção interna e externa a cada 12 meses (13.4.4.4)" + nota "Categoria A a partir de 1.960 kPa de pressão de operação (13.4.1.1)"; seção `etapas` com os 6 passos da spec, cada um com subitem. Bump manifest.

- [ ] **Step 4: Rodar teste → PASS.** Restart do container se necessário para o manifest.

- [ ] **Step 5: agent-browser** em `http://localhost:8083/qualificacao/caldeira` desktop: scroll até o fim de `etapas`, screenshot em 3 pontos, console sem erro.

- [ ] **Step 6: Commit** via agente: `feat(afr_labquali_website): NR-13 boiler demo page skeleton (hero, plate, steps)` incluindo bump.

### Task 5: Clímax 1 — ultrassom de espessura

**Files:**
- Modify: `static/demos/caldeira/index.html` (seção `ultrassom` + CSS + script IIFE `ut`)

**Interfaces:**
- Consumes: frame `seq/f_0150.webp` como `<img>` de fundo (`object-fit: cover`, caixa 16:9 centrada), classes/vars de Task 4.
- Produces: `window.LQ_UT = { points: [...] }` com os 12 pontos `{id, region, x, y, nominal, min, read}` (x,y em % do frame 16:9), tabela reaproveitada pela Task 7 via `LQ_UT.points`.

- [ ] **Step 1: Teste de dados** em `test_demo_caldeira.py`: extrair do HTML o JSON de pontos (bloco `<script type="application/json" id="ut-data">`) e asserir: 12 pontos; leituras exatas da spec (C 12,4 12,5 12,2 12,6 12,3 12,1; E 18,6 18,4 17,9; F 12,0 11,4 10,8); todo `read > min`; F3 é o único com `read - min < 1.5`.

- [ ] **Step 2: Rodar → FAIL** (bloco ausente).

- [ ] **Step 3: Implementar** seção `<section id="ultrassom" data-sc-act="pin" data-sc-span="6">`: fundo com o frame; pontos `<button class="ut-pt">` posicionados por %; painel do aparelho à direita com SVG A-scan (`viewBox 0 0 320 160`, pulso inicial em x=20, eco de fundo em x = 20 + read/20·280, altura fixa), leitura `<b id="ut-mm">` (`data-sc-count` não serve por ponto; animar no script), chip de região e cor (`ok` ≥ min+1,5; `warn` < min+1,5; `bad` < min). Script lê `--sc-p` do ato (como `tick()` do autoclave) e mapeia p ∈ [0.05, 0.75] sobre os 12 pontos em ordem C1..C6, E1..E3, F1..F3; p ∈ [0.78, 1] revela card "Vida remanescente": texto da fórmula com 0,16 mm/ano e ≈ 8 anos, linha do tempo 2014 → 2026 → 2034 → 2039 com rótulos da spec, recomendação. Reduced-motion: todos os pontos visíveis e card aberto.

- [ ] **Step 4: Rodar teste → PASS.**

- [ ] **Step 5: agent-browser**: viewport 1440×900 e 390×844; em cada, scroll até p≈0.5 e p≈0.95; screenshot; conferir que o ponto F3 está sobre a boca da fornalha nas duas larguras (Review Focus 2) e que em p≈0.5 o painel mostra o ponto E1 com "18,6" (ajustar posições em % até casar).

- [ ] **Step 6: Commit** via agente: `feat(afr_labquali_website): ultrasonic thickness climax`.

### Task 6: Clímax 2 — ensaio da válvula em bancada

**Files:**
- Modify: `static/demos/caldeira/index.html` (seção `valvula` + CSS + script IIFE `psv`)

**Interfaces:**
- Consumes: `seqv/v_{iiii}.webp:80:1`; constantes de Task 3: `POP=[38,54,70]`, `CUT_START=28`, `NF=80`.
- Produces: `window.LQ_PSV = { cert: "CV-2026-0187", pops: [10.42, 10.47, 10.45], pmta: 10.5 }` lido pela Task 7.

- [ ] **Step 1: Teste**: HTML contém `data-sc-sequence="seqv/v_{iiii}.webp:80:1"`, `data-sc-clip-map="travel"`, bloco JSON `id="psv-data"` com `pops` [38,54,70] e `pressures` [10.42,10.47,10.45], `pmta` 10.5, `cert` "CV-2026-0187"; cada pressure ≤ pmta e ≥ pmta·0,97.

- [ ] **Step 2: Rodar → FAIL.**

- [ ] **Step 3: Implementar** `<section id="valvula" data-sc-act="scrub" data-sc-span="6" data-sc-clip-map="travel">`: canvas da sequência; overlay inferior-direito com SVG pressão × tempo (`viewBox 0 0 640 260`): eixo y 6–11 kgf/cm², linha tracejada em 10,5 rotulada "PMTA", faixa ±3 % (10,185–10,5), curva gerada por função `pressure(f)` para f ∈ [1,80]: 1–27 rampa 7,0 → 9,6; sobe até cada pop no frame POP[i] atingindo `pressures[i]`, cai 7 % em 4 frames, sobe de novo; depois de 74 estabiliza em 9,7. Cursor e leitura `<b id="psv-kgf">` seguem o frame atual = `round(p·79)+1` (mesmo mapeamento `travel` da engine). Carimbo "APROVADA — abertura ≤ PMTA (13.4.1.2 'a')" + "Certificado CV-2026-0187" em p ≥ 0.92. Legenda do ato: "Válvula desmontada, inspecionada e testada em bancada no prazo da inspeção periódica (13.4.4.7). Teste em campo só em caráter excepcional (13.4.4.7.1)." Beats de texto em `data-sc-cue` para o corte (p≈0.35) e cada pop.

- [ ] **Step 4: Rodar → PASS.**

- [ ] **Step 5: Sincronismo (Review Focus 1)**: agent-browser, rolar até o frame 38 (p = 37/79), screenshot: disco levantado no frame E cursor no pico 10,42. Repetir para 54 e 70. Se divergir, ajustar constantes no JSON (nunca a curva "no olho").

- [ ] **Step 6: Commit** via agente: `feat(afr_labquali_website): safety valve bench test climax`.

### Task 7: Relatório, CTA, mobile, orçamento e verificação final

**Files:**
- Modify: `static/demos/caldeira/index.html` (seções `relatorio` pan + `contato` pin, CSS mobile, reduced-motion)
- Test: `test_demo_caldeira.py` (peso e termos proibidos)

**Interfaces:**
- Consumes: `LQ_UT.points`, `LQ_PSV`, `still/interno_*.webp`.

- [ ] **Step 1: Testes**: (a) soma dos arquivos em `static/demos/caldeira/` ≤ 12 MB; (b) HTML não contém, case-insensitive, `"PH "` isolado, `teste hidrostático periódico`, `aposentad`, `categoria por PMTA`; contém `PLH`, `13.4.4.12`, `Dados ilustrativos de uma caldeira fictícia`, `/qualificacao/autoclave`.

- [ ] **Step 2: Rodar → FAIL** nos itens de conteúdo.

- [ ] **Step 3: Implementar** `<section id="relatorio" data-sc-act="pan" data-sc-span="3">` com rail de 6 páginas A4 (capa com placa/categoria/datas; exame interno com `interno_1/2` e legendas; mapa de espessura gerado de `LQ_UT.points`; certificado da válvula de `LQ_PSV`; "Itens da NR-13 não atendidos" com um item leve a critério ou "nenhum"; parecer conclusivo + "Próxima inspeção: 11/2027" + assinatura PLH "CREA-MA 000000-0 · ART nº 0000000"); rodapé "Conteúdo mínimo conforme 13.4.4.12". Seção `contato` igual à `cotacao` do autoclave (formulário/botão), mais link "Também inspecionamos autoclaves e vasos de pressão" → `/qualificacao/autoclave`. Nota de rodapé dos dados ilustrativos. CSS mobile: copiar bloco `/* ---------- mobile ---------- */` do autoclave e adaptar (`.ut` painel empilha abaixo do frame; overlay da válvula vira faixa inferior). Reduced-motion: `const reduce` como no autoclave.

- [ ] **Step 4: Rodar testes → PASS** (suíte inteira `test_demo_caldeira`).

- [ ] **Step 5: agent-browser final**: desktop 1440 e mobile 390: scroll completo, console sem erro, screenshots do relatório; emular `prefers-reduced-motion: reduce` e conferir que a página lê inteira sem frames. Conferir tempo de carregamento aceitável (network idle < 10 s em localhost).

- [ ] **Step 6: Commit** via agente: `feat(afr_labquali_website): NR-13 boiler demo report, CTA and mobile`. Não fazer push nem deploy; avisar user para testar em `http://localhost:8083/qualificacao/caldeira`.
