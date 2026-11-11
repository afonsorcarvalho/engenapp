# Página "Retrofit de automação ETO" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Landing page cinematográfica `/retrofit/eto` no site Labquali que vende o retrofit da automação de esterilizadores ETO com o software AFR-ETO, em 7 cenas com 3D (máquina genérica, painel velho→novo explodido, cilindro na balança + IHM).

**Architecture:** Modelo da máquina reaproveitado do `cena.py` da proposta MARSP (sem marca), estendido com painel velho, painel novo explodível, cilindro de ETO, balança e IHM; três scripts de animação Blender renderizam sequências PNG convertidas em webp pelo `to_webp.py` existente. Página estática `static/demos/eto/` sobre a engine `scrollcraft.js` (cópia da caldeira), overlays HTML/SVG dirigidos pelo `p` do ato. Controller `demos.py` ganha o prefixo `retrofit`.

**Tech Stack:** Blender 5.2 (Windows, `/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe`, Cycles), Python 3 + Pillow (`/home/afonso/docker/odoo_engenapp/.conda/bin/python3`), vanilla JS/SVG, Odoo 16 (container, porta 8083), `agent-browser`.

**Spec:** `addons/afr_labquali_website/docs/superpowers/specs/2026-11-11-retrofit-eto-design.md` (ler inteira, inclusive "Fonte de verdade" e "Anti-goals").

## Global Constraints

- Copy pt-BR. Primeira menção: "óxido de etileno (ETO)". Nota única no rodapé: "Dados ilustrativos de um ciclo de demonstração".
- Máquina **sem marca**: nada de "MARSP", "Montroiz", logo ou `painel_marca.png` em render ou texto. Painel velho com CLP genérico, sem marca real. Os renders `capa_render.png`/`ficha_render.png` não entram na página.
- Proibido no copy (case-insensitive): `part 11`, `criptograf`, `hash`, `assinatura eletrônica`, `nuvem`, `supervisório`, `ntp`, `detector de eto`, `marsp`, `montroiz`. Conformidade só via "validação do software e qualificação QI/QO/QD pela Labquali"; nunca "software conforme ISO 11135/RDC".
- Rota pública `/retrofit/eto`; pasta `static/demos/eto/` (decisão: slug = pasta, sem mapa extra).
- Sequências: `seq/f_0001..f_0150.webp` 1920×1080; `seqp/p_0001..p_0070.webp` 1280×720; `seqe/e_0001..e_0060.webp` 1280×720. Total de `static/demos/eto/` ≤ 12 MB.
- Visual = caldeira (fundo escuro, acento `#ff6a2b`, mono para números, `logo-dark.svg`).
- Injeção **modo massa** (decisão do user). Valores fixos (minha call, 1500 L × 600 mg/L): 5 degraus de 0,18 kg → **0,90 kg** injetados; cilindro **45,00 → 44,10 kg**; pressão interna **−0,480 → −0,330 bar** (dentro da faixa −0,900…−0,300). Nunca citar a R3 como "por massa".
- Bump `__manifest__.py` 16.0.1.10.4 → **16.0.1.11.0** no commit que cria a rota. Commits via agente `git-commit-push` (haiku) na raiz do monorepo (`afr_labquali_website` NÃO é submodule), um path por vez, nunca `git add -A` (árvore suja). **Sem push nem deploy** sem OK do user.
- Scripts Blender vivem fora do repo em `C:\Users\Afonso\scrollcraft_blender\` (nada a commitar deles). Prévia 960×540 (ou 640×360 para 1280×720) e inspeção visual (Read tool) antes de todo render final; render final em background com log.
- Testes via agente `test-runner` (sonnet), módulo `afr_labquali_website`, tag `/afr_labquali_website:TestRetrofitEto`; comando de referência na memória `reference_odoo_test_command.md` (HttpCase exige `--http-port 8999 --workers 0`).

## Review Focus

1. Overlays (callouts do painel, visor da balança, tela da IHM) desalinhados do frame quando o viewport não é 16:9 ou é mobile: posições em % de uma caixa 16:9 com `object-fit: cover` idêntica ao canvas. Teste visual em Task 6 (1440×900 e 390×844).
2. Números da injeção divergindo entre visor da balança, IHM, gráfico e relatório: todos lidos de um único bloco `eto-data`. Teste em Task 6 (dados) e Task 7 (relatório usa `LQ_ETO`).
3. Copy prometendo o que o software não faz (anti-goals): teste de termos proibidos em Task 7.
4. `prefers-reduced-motion` e mobile: frames param no poster, todos os textos/valores finais visíveis. Task 7.
5. Página pesada: teste de orçamento ≤ 12 MB em Task 7, mas cada task de render já confere `du -sh` contra sua cota.

---

### Task 1: Modelo da máquina genérica + componentes novos (`eto_maquina.py`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/eto_maquina.py`
- Copy (input): `.../PROPOSTAS/POINT SUTURE/Proposta Autoclave ETO 1500L Montroiz/blender/camara2000.json` → `C:\Users\Afonso\scrollcraft_blender\camara2000.json` (não modificar a pasta da proposta)
- Reference: `.../blender/cena.py` (funções `mat`, `importar_camara`, `carenagem`, `portico`, `skid`, `estudio`), `caldeira.py` (marcador de stage)

**Interfaces:**
- Produces: script importável por `exec` até `# ---------------------------------------------------------------- stage` que monta: coleções `maquina`, `carenagem`, `contrapesos`, `skid`; carenagem **sem** `marca`/`marca_base` (faixa da coluna esquerda vira painel inox liso); objetos nomeados `painel` (armário do skid) e `painel_porta1/2`; e **três coleções novas**:
  - `painel_velho`: dentro do armário, placa de montagem com fileira de relés, contatores, CLP genérico bege com display segmentado, registrador de papel circular na porta, fiação solta, lâmpada `lamp_falha` (material emissivo, `emission_strength` animável).
  - `painel_novo`: camadas como empties pais `camada_ihm` (IHM 7" na porta, tela = objeto `ihm_tela` com material emissivo de textura trocável), `camada_clp` (CLP + 2 módulos em trilho DIN), `camada_fonte_bornes`, `camada_cabos`; cada camada com origem no seu plano para explodir em +Y local.
  - `injecao`: `cilindro_eto` (cilindro industrial cinza com válvula e capacete), `balanca` (plataforma inox com coluna e `balanca_visor` emissivo sem dígitos), mangueira inox `mangueira_eto` até a máquina.
- Constantes: `PAINEL_POS` (Vector, centro frontal do armário), `INJ_POS` (Vector, centro da balança), `CAM_ALVO_MAQ` (Vector).
- Texturas sem números: `ihm_tela` usa imagem neutra gerada no script (fundo da IHM com barras/molduras, sem dígitos); `balanca_visor` fundo LCD vazio.

- [ ] **Step 1: Escrever `eto_maquina.py`** copiando de `cena.py` as funções de materiais, câmara, carenagem (removendo o bloco do "painel de marca"), pórtico e skid, e acrescentando as três coleções acima. Bloco `stage` = câmera 3/4 frontal + render still 1600×900 para prova.
- [ ] **Step 2: Render de prova**

```bash
cd /mnt/c/Users/Afonso/scrollcraft_blender && "/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P eto_maquina.py -- "C:\Users\Afonso\scrollcraft_blender\out\eto_test.png" 32 > eto_test.log 2>&1; grep -c Traceback eto_test.log; ls out/eto_test.png
```
Expected: `0`; arquivo existe.
- [ ] **Step 3: Inspecionar `out/eto_test.png`** (Read): máquina com carenagem inox, faixa lateral lisa, **nenhum texto/logo**; skid com painel à direita. Ajustar até passar.
- [ ] **Step 4: Prova dos componentes**: script `dbg_eto.py` que importa até `stage`, esconde `carenagem`, abre `painel_porta1`, renderiza 3 stills 1280×720/32 samples: (a) `painel_velho` visível, (b) `painel_novo` com camadas deslocadas 0,15 m em +Y cada, (c) close de `injecao`. Inspecionar: relés/registrador/lâmpada legíveis em (a); camadas separadas e distinguíveis em (b); cilindro, balança com visor, mangueira em (c).
- [ ] **Step 5:** nada a commitar (script fora do repo).

### Task 2: Sequência do hero (`anim_eto_hero.py` → `seq/`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/anim_eto_hero.py`
- Create (output): `addons/afr_labquali_website/static/demos/eto/seq/f_0001..f_0150.webp`

**Interfaces:**
- Consumes: Task 1 (`eto_maquina.py`, `PAINEL_POS`, `CAM_ALVO_MAQ`).
- Produces: 150 frames. Marcos: 1–60 órbita 3/4 frontal (máquina inteira, porta guilhotina fechada) → lateral; 61–110 câmera desce e se aproxima do skid; 111–150 assenta no **painel com porta fechada** em frontal, painel ocupando ~40 % da largura no centro-direita. Frame 150 = ponte para a cena 2. Ambiente industrial escuro como a caldeira.

- [ ] **Step 1: Escrever `anim_eto_hero.py`** nos moldes de `anim_caldeira.py` (argv `<outdir> <samples> <start> <end> [preview]`, `MODEL = "eto_maquina.py"`, `SC_FRAMES` para stills, 1920×1080, preview 960×540 `frame_step 21`).
- [ ] **Step 2: Preview** `prevH` (8 PNGs) e inspeção contra os marcos; nenhum texto/logo em nenhum frame.
- [ ] **Step 3: Render final** em background: outdir `seqH`, 48 samples, `renderH.log`; ao terminar `ls seqH | wc -l` → 150.
- [ ] **Step 4: Converter**

```bash
/home/afonso/docker/odoo_engenapp/.conda/bin/python3 /mnt/c/Users/Afonso/scrollcraft_blender/to_webp.py /mnt/c/Users/Afonso/scrollcraft_blender/seqH /home/afonso/docker/odoo_engenapp/addons/afr_labquali_website/static/demos/eto/seq
du -sh /home/afonso/docker/odoo_engenapp/addons/afr_labquali_website/static/demos/eto/seq
```
Expected: 150 arquivos `f_0001..f_0150.webp`, ≤ 7,0 MB (senão `--quality 72`).
- [ ] **Step 5: Commit** via agente: só `addons/afr_labquali_website/static/demos/eto/seq`. Mensagem: `feat(afr_labquali_website): hero render sequence for ETO retrofit page`.

### Task 3: Sequência do painel velho → novo explodido (`anim_eto_painel.py` → `seqp/`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/anim_eto_painel.py`
- Create (output): `static/demos/eto/seqp/p_0001..p_0070.webp`

**Interfaces:**
- Consumes: Task 1 coleções `painel_velho`, `painel_novo`, camadas, `lamp_falha`, `painel_porta1/2`.
- Produces: 70 frames 1280×720, câmera **fixa** em close 3/4 do armário (mesmo enquadramento do frame 150 do hero, mais perto). **Constantes de sincronismo** (copiar para o HTML na Task 5/6): `OLD_END=22` (1–8 porta abre; 9–22 painel velho, `lamp_falha` pisca: on nos frames 10–12, 16–18), `SWAP=[23,36]` (componentes velhos sobem e somem para +Z enquanto as camadas novas entram de −Y), `EXPLODE=[37,60]` (camadas novas se afastam em +Y local: IHM 0,45 m, CLP 0,30 m, fonte/bornes 0,15 m, cabos 0), `HOLD=[61,70]` (estático; fundo das chamadas numeradas).

- [ ] **Step 1: Escrever `anim_eto_painel.py`** com os keyframes acima (visibilidade por `hide_render` keyframed, posições das camadas, `emission_strength` da lâmpada).
- [ ] **Step 2: Preview** `prevP` (640×360, step 10 → 7 PNGs). Inspecionar: frame 11 lâmpada acesa; frame 30 transição legível; frame 70 quatro camadas separadas e frontais o bastante para chamadas.
- [ ] **Step 3: Render final** em background (`seqP`, 48 samples, `renderP.log`), 70 PNGs.
- [ ] **Step 4: Converter** com `to_webp.py --size 1280x720` para `static/demos/eto/seqp/` com prefixo `p_` (se `to_webp.py` não aceitar prefixo, renomear após converter); `du -sh` ≤ 2,0 MB.
- [ ] **Step 5: Commit** via agente: `static/demos/eto/seqp`. Mensagem: `feat(afr_labquali_website): old-to-new control panel sequence`.

### Task 4: Sequência da injeção (`anim_eto_injecao.py` → `seqe/`)

**Files:**
- Create: `/mnt/c/Users/Afonso/scrollcraft_blender/anim_eto_injecao.py`
- Create (output): `static/demos/eto/seqe/e_0001..e_0060.webp`

**Interfaces:**
- Consumes: Task 1 coleção `injecao`, `ihm_tela`, `INJ_POS`.
- Produces: 60 frames 1280×720. Câmera: 1–20 desliza do cilindro (close da válvula) para trás até enquadrar **cilindro + balança à esquerda e a IHM do painel à direita**; 21–60 **fixa** (fundo dos overlays numéricos). Válvula do cilindro gira de fechada para aberta em 18–22. `balanca_visor` e `ihm_tela` sem dígitos em todos os frames. Constante `INJ_FIXED=21`.

- [ ] **Step 1: Escrever `anim_eto_injecao.py`.**
- [ ] **Step 2: Preview** `prevE2` (640×360, step 10). Inspecionar frame 60: visor e tela da IHM grandes o bastante para receber texto HTML legível (visor ≥ 6 % da largura, tela IHM ≥ 18 %).
- [ ] **Step 3: Render final** (`seqE2`, 48 samples, `renderE2.log`), 60 PNGs.
- [ ] **Step 4: Converter** para `static/demos/eto/seqe/` prefixo `e_`; `du -sh` ≤ 1,8 MB.
- [ ] **Step 5: Commit** via agente: `static/demos/eto/seqe`. Mensagem: `feat(afr_labquali_website): ETO weighed-injection sequence`.

### Task 5: Rota `/retrofit/eto`, scaffold, cenas 1–2

**Files:**
- Modify: `addons/afr_labquali_website/controllers/demos.py` (docstring; `RETROFIT = ("eto",)`; `DEMOS += RETROFIT`; `PREFIXES["retrofit"] = RETROFIT`; rotas `"/retrofit/<string:slug>"` e `"/retrofit/<string:slug>/<path:fname>"` nos dois decorators)
- Create: `addons/afr_labquali_website/static/demos/eto/index.html`
- Copy: `static/demos/caldeira/scrollcraft.js`, `static/demos/caldeira/logo-dark.svg` → `static/demos/eto/`
- Modify: `addons/afr_labquali_website/__manifest__.py` (version `16.0.1.11.0`)
- Create: `addons/afr_labquali_website/tests/test_retrofit_eto.py`; Modify: `tests/__init__.py` (`from . import test_retrofit_eto`)

**Interfaces:**
- Produces: seções com ids `inicio` (scrub, canvas `data-sc-sequence="seq/f_{iiii}.webp:150:1"`), `dor` (pin), `painel` (scrub `seqp/p_{iiii}.webp:70:1`, vazio nesta task), `fases`, `injecao`, `seguranca`, `registro`, `contato` (placeholders vazios para Tasks 6–7). Botão do topo "Agendar avaliação" → `#contato`.

- [ ] **Step 1: Testes** em `test_retrofit_eto.py`, classe `TestRetrofitEto(HttpCase)`, `@tagged("post_install", "-at_install")`:
  - `test_page`: `GET /retrofit/eto` → 200; contém `Retrofit de automação ETO: vida nova ao equipamento, conformidade ao processo`, `CLP e IHM novos, ciclo totalmente rastreável e validação do software pela Labquali.`, `Quando o CLP para, a produção para`; contém `id="X"` para X em `inicio dor painel fases injecao seguranca registro contato`.
  - `test_hero_frame`: `GET /retrofit/eto/seq/f_0001.webp` → 200, `image/webp`.
  - `test_traversal_rejected`: `GET /retrofit/eto/%2e%2e/caldeira/index.html` → 404 (mesmo padrão do teste da caldeira).
  - `test_wrong_prefix_404`: `/retrofit/caldeira` → 404; `/qualificacao/eto` → 404; `/inspecao/eto` → 404.
  - `test_siblings_unchanged`: `/inspecao/caldeira` → 200; `/qualificacao/autoclave` → 200.
- [ ] **Step 2: Rodar → FAIL** (rota inexistente) via `test-runner`.
- [ ] **Step 3: Implementar** controller + `index.html` com `<head>` igual ao da caldeira (preload `seq/f_0001.webp`), topbar (logo, "Voltar ao site", botão "Agendar avaliação"), `inicio` com poster + canvas + título/sub da spec e 2 beats `data-sc-cue` (≈0.35 "O vaso, as portas e as bombas continuam bons."; ≈0.85 "O que envelheceu foi a automação."); `dor` com corpo da spec (peça descontinuada, programa sem backup, ninguém que conheça a lógica, lote retido; linha da auditoria "cadê o registro deste ciclo?") sobre o frame `seqp/p_0012.webp` como `<img>` de fundo (lâmpada acesa) e contador HTML "dias parado" (`data-sc-count` 0→7). Bump manifest.
- [ ] **Step 4: Rodar → PASS** (restart do container se o manifest exigir).
- [ ] **Step 5: agent-browser** em `http://localhost:8083/retrofit/eto` 1440×900: scroll até o fim de `dor`, 3 screenshots, console sem erro.
- [ ] **Step 6: Commit** via agente: `controllers/demos.py`, `__manifest__.py`, `static/demos/eto/index.html`, `scrollcraft.js`, `logo-dark.svg`, `tests/`. Mensagem: `feat(afr_labquali_website): ETO retrofit page route, hero and pain scene`.

### Task 6: Cena 3 (painel explodido), faixa de fases, cena 4 (injeção por peso)

**Files:**
- Modify: `static/demos/eto/index.html`
- Modify: `tests/test_retrofit_eto.py`

**Interfaces:**
- Consumes: `seqp` + constantes `OLD_END=22, SWAP=[23,36], EXPLODE=[37,60], HOLD=[61,70]`; `seqe` + `INJ_FIXED=21`.
- Produces: `<script type="application/json" id="eto-data">` com `{"steps":5,"step_kg":0.18,"total_kg":0.90,"cyl_start":45.00,"cyl_end":44.10,"p_start":-0.480,"p_end":-0.330,"p_min":-0.900,"p_max":-0.300}` e `window.LQ_ETO` (objeto parseado) consumido pela Task 7.

- [ ] **Step 1: Testes**:
  - `test_panel_scene`: HTML contém `seqp/p_{iiii}.webp:70:1"`, `CLP Delta DVP-SE`, `IHM Delta DOP-107`, `Modbus TCP`, `balança`; contém as frases "fica" e "troca" da spec (vaso, portas, bombas, camisa / automação e instrumentação).
  - `test_phase_strip`: dentro de `id="fases"`, na ordem: `Aquecimento`, `Leak test`, `Acondicionamento`, `Umidificação`, `Injeção de ETO`, `Exposição`, `Lavagens N2`, `Aeração`, `Hiperventilação`.
  - `test_injection_data`: parse de `eto-data`; `steps == 5`; `round(steps*step_kg, 2) == total_kg == 0.90`; `round(cyl_start - cyl_end, 2) == total_kg`; `p_min <= p_start < p_end <= p_max`; HTML contém `ETO dosado por peso, não por estimativa`, `O relatório registra a massa exata injetada.`, `window.LQ_ETO`, `seqe/e_{iiii}.webp:60:1"`.
  - `test_injection_frame`: `GET /retrofit/eto/seqe/e_0060.webp` e `/retrofit/eto/seqp/p_0070.webp` → 200 webp.
- [ ] **Step 2: Rodar → FAIL.**
- [ ] **Step 3: Implementar**:
  - `painel` (scrub, `data-sc-span` ≈ 4): canvas `seqp`; legenda "fica × troca"; chamadas numeradas 1–4 (IHM Delta DOP-107 7" · CLP Delta DVP-SE com módulos PT100 e analógicos · fonte, bornes e relés de interface · comunicação Modbus TCP) que aparecem em `p ≥ (EXPLODE[1]-1)/69`, posicionadas em % sobre a caixa 16:9; item 5 "instrumentação nova: PT100, transdutor de pressão, umidade e balança do cilindro".
  - `fases` (pin curto): faixa de 9 fases com ícones, marcador desliza até "Injeção de ETO" e fica `position: sticky` durante `injecao`.
  - `injecao` (scrub, span ≈ 5, `data-sc-clip-map="travel"`): canvas `seqe`; overlays HTML posicionados sobre o frame fixo: visor da balança (`#eto-cyl`, kg com 2 casas, vírgula), tela da IHM (fase "INJEÇÃO DE ETO", `#eto-step` "DEGRAU n DE 5", `#eto-inj` kg injetados, `#eto-p` bar com 3 casas); gráfico SVG massa injetada × pressão em degraus. Mapeamento: frame `f = round(p·59)+1`; para `f < INJ_FIXED` valores iniciais; de 21 a 60, progresso `q = (f-21)/39`; degrau `n = min(5, floor(q·5)+1)`; massa sobe em escada (cada degrau: rampa nos primeiros 60 % do seu intervalo, platô depois); pressão linear na massa entre `p_start` e `p_end`; cilindro = `cyl_start − massa`. Todos lidos de `LQ_ETO`. Fecho com a frase do relatório e chip "Vazamento? A balança detecta queda de massa com a válvula fechada."
  - Números reescritos por frame **fora** de `aria-live`; um `<p class="sr-only">` estático resume os valores finais.
- [ ] **Step 4: Rodar → PASS.**
- [ ] **Step 5: agent-browser** em 1440×900 e 390×844: `painel` em p≈1 (chamadas sobre as camadas certas) e `injecao` em f=21, 40, 60 (visor/IHM sobre os objetos do frame; em f=60 visor "44,10", IHM "0,90 kg" e "DEGRAU 5 DE 5", "−0,330 bar"). Ajustar % até casar (Review Focus 1–2).
- [ ] **Step 6: Commit** via agente: `feat(afr_labquali_website): panel teardown and weighed ETO injection scenes`.

### Task 7: Cenas 5–7, mobile, reduced-motion, rigor do copy, orçamento

**Files:**
- Modify: `static/demos/eto/index.html`
- Modify: `tests/test_retrofit_eto.py`
- Copy (opcional): tela real de alarmes `.../PROPOSTAS/POINT SUTURE/Proposta Autoclave ETO 1500L Montroiz/telas/07_alarmes.png` → `static/demos/eto/still/alarmes.webp` (converter; conferir que não há marca de cliente na tela; se houver "VAPOR01"/nome de cliente, reconstruir a tela em HTML)

**Interfaces:**
- Consumes: `LQ_ETO`.

- [ ] **Step 1: Testes**:
  - `test_safety_scene`: contém `Alarme que diz o que fazer`, `ISA-18.2`, `próxima ação`, `TROCAR CILINDRO DE ETO`, `pressão atmosférica`.
  - `test_record_scene`: contém `Cada ciclo deixa um registro completo`, `Quem instala é quem valida`, `QI`, `QO`, `QD`, `validação do software`; o relatório usa `LQ_ETO.total_kg` (string `LQ_ETO.total_kg` no HTML); campos `Operador` e `Responsável` com linha de assinatura.
  - `test_cta`: `id="contato"`, `id="quote"`, `Agende uma avaliação técnica`, `mailto:labquali@labquali.com.br`, ≥ 2 `href="#contato"`.
  - `test_copy_rigor`: remover blocos `<script>…</script>` e `<style>…</style>` antes (JS usa `location.hash`); no texto restante, em minúsculas, nenhum termo proibido das Global Constraints (termos curtos `hash`, `ntp`, `nuvem` com `\b`); contém `óxido de etileno (ETO)` e `Dados ilustrativos de um ciclo de demonstração`; não contém `11135` nem `rdc`.
  - `test_size_budget`: soma de `static/demos/eto/` ≤ 12 MB (mesmo código da caldeira, outra pasta).
- [ ] **Step 2: Rodar → FAIL.**
- [ ] **Step 3: Implementar**:
  - `seguranca` (pin): tela de alarmes (still ou HTML) com pendência amarela "TROCAR CILINDRO DE ETO" + "próxima ação: trocar o cilindro e confirmar na IHM"; corpo da spec; 2–3 linhas: queda de energia com ETO na câmara trava a máquina até a rotina de segurança; aborto após ETO força lavagens N2 + aeração antes de liberar a porta; porta só abre na pressão atmosférica.
  - `registro` (pin, relatório A4 montando linha a linha por `data-sc-cue`): empresa/equipamento genéricos, data, operador, código da carga, lote do cilindro, receita, tempos de cada fase, alarmes/pendências, leak test "APROVADO", massa de ETO de `LQ_ETO.total_kg`, campos de assinatura; depois bloco "Quem instala é quem valida" (QI, QO, QD e validação do software pela Labquali; documentação pronta para a próxima inspeção) + menção a usuários com níveis de acesso e CSV a cada segundo.
  - `contato`: copiar `contato`/`#quote` da caldeira, assunto do mailto `Retrofit ETO · …`, campos adaptados (empresa, volume da câmara, CLP atual, prazo), título "Agende uma avaliação técnica", texto da spec.
  - Rodapé com a nota dos dados ilustrativos. CSS mobile e `reduce` copiados/adaptados da caldeira (overlays da injeção viram faixa abaixo do frame no mobile).
  - Passe de humanizer no copy (skill `anthropic-skills:humanizer`) sem alterar fatos.
- [ ] **Step 4: Rodar suíte `TestRetrofitEto` → PASS.**
- [ ] **Step 5: agent-browser final** 1440×900 e 390×844: scroll completo, console sem erro, screenshots de cada cena; emular `prefers-reduced-motion: reduce` e conferir leitura completa com valores finais.
- [ ] **Step 6: Commit** via agente: `feat(afr_labquali_website): ETO retrofit safety, record and CTA scenes`. Sem push/deploy; avisar o user para testar em `http://localhost:8083/retrofit/eto`.
