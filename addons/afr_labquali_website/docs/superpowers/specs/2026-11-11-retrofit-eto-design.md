# Página "Retrofit de automação ETO" — design

Data: 2026-11-11. Módulo: `afr_labquali_website`. Status: builder-check feito; aguardando aprovação do user.

## Intenção

A Labquali distribui o software **AFR-ETO** (automação de esterilizadores a óxido de etileno, da AFR Soluções Inteligentes) e valida o sistema que instala. O cliente é a **indústria** (não hospital): tem um esterilizador ETO cujo vaso, portas e bombas ainda servem, mas a automação envelheceu. Dois gatilhos levam esse cliente a procurar o retrofit (palavras do user):

1. **CLP antigo**: sem peça de reposição, sem suporte, ninguém que conheça a lógica.
2. **Auditoria ou inspeção da Anvisa**: falta registro do ciclo, rastreio de operador e lote, integridade dos dados.

A página é uma landing page para onde vendedor e anúncio mandam esse cliente. Ela usa o mesmo formato cinematográfico de `/inspecao/caldeira`: scroll guiado, máquina em 3D como protagonista. O objetivo é que o cliente entenda o serviço de retrofit (o que muda na máquina, o que o software faz, o que fica registrado, quem valida) e agende uma avaliação técnica.

A máquina mostrada é **genérica, sem marca** (decisão do user). A geometria vem do modelo da MARSP, mas sem a placa "MARSP / AUTOCLAVE ETO", sem logo Montroiz e sem nenhuma marca de fabricante. Motivo: na cena 2 o painel dessa máquina aparece velho e com falha, e isso não pode ser associado à MARSP nem à parceira Montroiz. A página **não vende a MARSP nova**.

## Goals

- Página estática em `static/demos/retrofit-eto/`, servida em **`/retrofit/eto`** pelo controller `controllers/demos.py`, com o mesmo engine `scrollcraft.js` e a mesma linguagem visual dos demos anteriores (tema escuro, laranja `#ff6a2b`, mono para números, logo Labquali).
- Sete cenas na ordem aprovada pelo user (seção "Roteiro").
- Clímax na **injeção de ETO por pesagem**: 3D do cilindro na balança com visor e IHM mostrando a admissão, com números sincronizados ao scroll.
- Copy fiel ao que o AFR-ETO faz de fato, com fonte no levantamento do projeto (seção "Fonte de verdade").
- Desktop e mobile funcionando; mobile com motion reduzida, como nos demos anteriores.

## Non-goals

- Não vende a MARSP nova. Essa página vem depois, em separado.
- Não fala do supervisório nem de nuvem, criptografia, backup ou impressão digital. Existem no supervisório do user e terão página própria depois.
- Não cobre esterilizador a vapor (AFR-VAP). Fica para depois.
- Não mexe no menu do site. O conteúdo do menu é builder-owned no banco; o item de menu é tarefa separada, pedida pelo user.
- Nada de models ou dados do banco.

## Anti-goals (falha mesmo funcionando)

Prometer o que o software não entrega. **Proibido** na página:

- "Conforme 21 CFR Part 11", "assinatura eletrônica", "dados criptografados", "hash" ou "integridade certificada". O relatório tem campos de assinatura manual e não há hash.
- "Software conforme ISO 11135/RDC". Quem sustenta a conformidade do **processo** é a validação Labquali. Fórmula permitida: "validação do software e qualificação QI/QO/QD pela Labquali".
- "Detector de ETO integrado": o detector ambiente fica fora do CLP.
- Gráfico P/T na IHM: foi retirado. A curva aparece **na página**, como visualização dos dados registrados, e não como tela da IHM.
- NTP ou sincronização de relógio.
- Supervisório, nuvem ou acesso remoto.

Também é falha:

- Parecer template: cada cena tem composição própria.
- Página pesada demais: alvo ≤ 12 MB no total, como a caldeira.

## Restrições e contexto técnico

- Odoo 16, porta host 8083, container com entrypoint custom. **Bump de versão obrigatório** no `__manifest__.py` a cada commit. A versão atual é 16.0.1.10.4; feat → 16.0.1.11.0.
- Controller: adicionar o prefixo `retrofit` com a tupla `RETROFIT = ("eto",)` em `PREFIXES` e as rotas `/retrofit/<slug>` e `/retrofit/<slug>/<path:fname>`, no mesmo padrão de `/inspecao/`. O slug em disco é `retrofit-eto`, e a URL pública é `/retrofit/eto`. O builder decide o mapeamento: pasta `static/demos/eto/` ou um dict slug→pasta. Testes existentes do controller devem continuar verdes, com um teste novo para a rota.
- Pipeline 3D: `/mnt/c/Users/Afonso/scrollcraft_blender/` (Blender 5.2 LTS em Windows, Cycles, frames webp 1920×1080). Seguir o padrão de `caldeira.py` + `anim.py`.
- **Modelo da MARSP já existe:** `C:\Users\Afonso\OneDrive\Documentos\PROPOSTAS\POINT SUTURE\Proposta Autoclave ETO 1500L Montroiz\blender\cena.blend` (+ `cena.py`, `camara2000.json`, `painel_marca.png`). Renders de referência estão em `imagens/capa_render.png` (com carenagem e marca MARSP) e `imagens/ficha_render.png` (sem carenagem, plataforma de utilidades com painel, bombas e boiler). Reaproveitar a geometria, sem remodelar, **removendo a marca** (`painel_marca.png`, textos MARSP/Montroiz). Os renders `capa_render.png` e `ficha_render.png` mostram a marca e **não podem ir para a página** como estão.
- Engine: cada demo leva cópia própria (ex.: `static/demos/caldeira/scrollcraft.js`; `_vendor/` só tem `three.module.js`). Copiar da caldeira e ler o cabeçalho antes de autorar. A caldeira (`static/demos/caldeira/index.html`) é a referência de estrutura mais recente.

## Fonte de verdade (o que o AFR-ETO faz)

Projeto em `C:\Users\Afonso\OneDrive\Documentos\AUTOMAÇÃO\desenvolvimento\ETO` (WSL: `/mnt/c/Users/Afonso/OneDrive/Documentos/AUTOMAÇÃO/desenvolvimento/ETO`). Fatos levantados:

- **Hardware:** CLP Delta DVP-SE com módulos DVP04PT (PT100) e DVP06XA; IHM Delta DOP-107EV de 7" (800×480); Modbus TCP entre IHM e CLP; balança em RS-485 Modbus. Instrumentação: PT100 (câmara, boiler, carga opcional), transdutor de pressão, umidade (sensor 4–20 mA ou psicrômetro), balança do cilindro de ETO.
- **Fases (11):** aquecimento → leak test → acondicionamento (pulsos de vácuo com quebra por N2) → umidificação → injeção de ETO → exposição (com reposição) → lavagens N2 → aeração → hiperventilação → finalizado. Também há os estados ocioso, iniciando e abortado. Nomes em `ihm/textos.py` (FASES).
- **Injeção por massa:** admissão em degraus (SP, Y %, janela X s), com a balança medindo o cilindro. O relatório registra a massa injetada. A balança detecta vazamento quando a massa cai com a válvula fechada.
- **Receitas:** 10 no total. R1 leak test, R2 aeração, R3 ETO 180 min, R4 purga N2+ar, R5–R10 configuráveis. A validação de parâmetros acontece na edição. Editar exige supervisor; editar parâmetros dos ciclos exige manutenção.
- **Segurança:** a máquina só aborta por segurança. Os demais problemas viram **pendência** com a "próxima ação do operador", sem perder o ciclo. Há cerca de 45 alarmes com prioridade ISA-18.2. Aborto após ETO força lavagens N2 + aeração antes de liberar a porta. Se a energia volta com ETO na câmara, a máquina trava até a rotina de segurança. A porta só abre na pressão atmosférica, com equalização.
- **Registro:**
  - Níveis de acesso: operador, supervisor, calibração, manutenção.
  - Log de operações com o usuário e histórico de alarmes.
  - CSV por ciclo com uma amostra por segundo.
  - Relatório do ciclo em PDF A4 + TXT, contendo empresa, equipamento, data e hora, operador, código da carga, lote do cilindro, receita, parâmetros, tabela P/T/UR/massa, eventos, tempos de cada fase, veredito do leak test, massa de ETO e campos de assinatura do operador e do responsável.
- **Verificação interna:** bateria de 50 cenários de falha aprovada em simulador com o ladder real do CLP.
- **Imagens reais da IHM:**
  - `PROPOSTAS/.../telas/01_inicio … 08_resultado.png` (800×480);
  - `ETO/ihm/telas_ihm/*.png`;
  - `ETO/ihm/telas_ihm/vivo/ciclo/` (211 quadros 800×480 de um ciclo real na bancada).
- **Dados de ciclo** (conferir como a fase de injeção vem rotulada no JSON, porque nenhum nome contém "ETO"): `ETO/simulador/execucoes/2026-10-09_212049/series/01_ciclo_r3_ok.json`, com 352 amostras de t, fase, P, T, UR, eto_kg, cil_kg e válvulas. É um ciclo comprimido (exposição curta), então os tempos do eixo devem ser reescalados para o ciclo R3 ETO 180 min, ou o eixo deve mostrar só a ordem das fases, sem relógio. A forma das curvas vem do arquivo.

## Roteiro do scroll (7 cenas, aprovado pelo user)

Os títulos são do user. Corpo e movimento são o ponto de partida; o builder pode ajustar o texto, desde que respeite os anti-goals.

### 1. Hero · `scrub`, sequência principal

- **Título:** "Retrofit de automação ETO: vida nova ao equipamento, conformidade ao processo"
- **Sub:** "CLP e IHM novos, ciclo totalmente rastreável e validação do software pela Labquali."
- **3D:** esterilizador ETO genérico (geometria da MARSP, **sem marca**; a faixa lateral vira painel liso de inox ou recebe só "ETO" sem logo), com carenagem, em órbita lenta num ambiente industrial limpo. Ao longo do scrub, a câmera vai da vista 3/4 frontal até a plataforma de utilidades e o painel elétrico, preparando a cena 2.

### 2. A dor · "Quando o CLP para, a produção para"

- **Corpo:** peça descontinuada, programa desatualizado (não validável, fora das regras atuais), sem suporte técnico, ninguém que conheça a lógica. Cada parada é um lote retido esperando liberação. Fecha com o registro: "E o registro do ciclo ainda sai numa impressora matricial antiga?" (revisão do user, 2026-11-11; a cena 6 responde com "gravado em arquivo digital").
- **Visual:** close do painel em versão "antiga", com porta aberta, relés, CLP genérico fora de linha (sem marca real), fiação desorganizada, impressora matricial de painel com fita de papel (o registrador circular saiu: máquinas ETO não usam) e uma lâmpada de falha piscando. Contador "dias parado" em HTML.
- **3D:** sequência curta ou estado alternativo do painel. O builder escolhe entre sequência ou still + overlay, dependendo do peso.

### 3. Por dentro da nova automação

- **Visual:** painel novo "explode" em camadas no 3D: IHM 7", CLP com módulos de temperatura e analógicos, fonte, bornes, relés de interface e cabo de rede até a IHM. Chamadas numeradas em HTML, no estilo da ficha técnica da proposta.
- **Texto das chamadas:** CLP Delta DVP-SE · IHM Delta DOP-107 7" · módulos PT100 e analógicos · comunicação Modbus TCP · instrumentação nova (PT100, transdutor de pressão, umidade, balança).
- Uma frase deixa claro o que **fica** (vaso, portas, bombas, camisa) e o que **troca** (automação e quadro elétrico) e o que se **entrega** (esquema elétrico do painel novo, para a manutenção). Revisão do user, 2026-11-11.

### Faixa de fases (antes da cena 4)

Faixa curta com as fases do ciclo em ordem (ícones como os da barra da IHM). Ao rolar, o marcador anda até "Injeção de ETO" e a faixa fica fixa durante a cena 4. Objetivo: mostrar o ciclo completo sem tirar o foco da injeção. Aprovado pelo user.

### 4. Clímax · "ETO dosado por massa, não estimado por gradiente de pressão"

- **3D (pedido do user):** cilindro de ETO sobre a **balança com visor** digital, mangueira até a máquina e a **IHM mostrando a tela de injeção**.
- **Roteiro 3D v3 (revisão do user, 2026-11-11), `seqe/` com 112 frames** (`anim_eto_injecao.py` + `eto_valvulas.py`):
  - **1–14 · válvula do cilindro:** close na válvula nova (foto01 do user): corpo forjado em T de **inox**, rosca cônica no gargalo, saída lateral com rosca fêmea larga, ressalto de segurança oposto, castelo sextavado e volante de 6 lóbulos em alumínio escovado com tampa azul. O volante gira 150° no sentido de abrir (2–12).
  - **10–36 · válvula pneumática de admissão:** a câmera vai até a válvula de assento angular NF (foto02), instalada na linha entre a mangueira trançada do cilindro e a máquina (corpo em Y inox com flanges e seta de fluxo, atuador inox com indicador de posição e tomada de ar). Em 30–36 a meia-casca da frente sai de cena e fica o **corte** (foto03).
  - **36–54 · abertura em corte:** o ar entra sob o pistão laranja, a mola é comprimida, a haste recua e o obturador sai da sede; o ETO (volume azul translúcido com setas) atravessa o corpo. Faces de corte em bege.
  - **54–70 · recuo:** a meia-casca volta e a câmera recua para o plano fixo (mesma câmera de antes, então o `.ov--lcd` não mudou).
  - **71–112 · plano fixo:** os cinco degraus. A IHM 3D mostra a **tela real do AFR-ETO renderizada frame a frame** (`patch_tela.py --injecao`, mesmas fórmulas do JS: degrau, injetada, cilindro, valor, alvo do degrau, tempos). O indicador da válvula sobe enquanto a massa do degrau rampa e desce na espera. O overlay HTML `.ov--hmi` (tela inventada) foi removido; o visor da balança continua em overlay HTML.
- **Ao rolar:**
  - O visor da balança conta a massa do cilindro descendo.
  - A IHM mostra degrau N de 5 e a massa injetada subindo.
  - Pressão interna sobe em degraus até o alvo.
- **Sincronismo:** o visor da balança, o espelho da IHM e o gráfico ficam em HTML sincronizado ao frame `f = round(p·111)+1`. A tela da IHM 3D é renderizada com os mesmos valores, frame a frame, a partir das mesmas fórmulas.
- **Gráfico (HTML/SVG ao lado):** massa injetada × pressão interna, com os degraus marcados.
- **Fecho da cena:** "O relatório registra a massa exata injetada." Chip: "Vazamento? A balança detecta queda de massa com a válvula fechada."
- **Modo massa (decisão do user):** o retrofit mostrado **inclui a balança como item padrão** e a cena mostra a injeção no **modo massa** (`RC_ETO_MODO = 1`, exige `M_USA_BALANCA`). Atenção: a receita padrão R3 e a tela `05_eto.png` estão em modo **pressão**. Não usar os números da `05_eto` nem dizer que o ciclo padrão é por massa. Degraus em **kg**, com a pressão acompanhando. O builder calcula valores coerentes com a câmara de 1500 L (alvo de massa, 5 degraus, pressão final dentro de −0,900 a −0,300 bar). A layout da tela de injeção da IHM pode seguir a `05_eto` com os campos do modo massa. Os valores são ilustrativos, com a mesma nota dos outros demos.
- A balança entra na lista de "instrumentação nova" da cena 3 como item padrão.

### 5. Segurança · "Alarme que diz o que fazer"

- **Corpo:** cerca de 45 alarmes por prioridade (ISA-18.2). O que não é segurança vira pendência com a próxima ação do operador, sem perder o ciclo. O que é segurança aborta e, depois do ETO, força a purga antes de liberar a porta.
- **Visual:** a **tela real de alarmes do AFR-ETO** (tela 54, `tela-alarmes.webp`, revisão do user 2026-11-12), montada por `patch_alarmes.py` (Blender dir) com a geometria e as cores do gerador da IHM (`ETO/ihm/gera_ihm_eto.py`, `alarmes()`: lista de ativos DISPARO/ALARME, botões SOBE/DESCE/RECONHECER/RECONHECER FALHAS DE PORTA, sem banner) sobre o cabeçalho e o rodapé da captura limpa. Linha ativa: "3 PENDÊNCIA: TROCAR CILINDRO DE ETO (ciclo 00412)" em amarelo (prioridade 3); botão de alarmes do rodapé amarelo até reconhecer. A tela em HTML reconstruída saiu. Fundo (revisão do user, 2026-11-12): giroflex vermelho renderizado (`seqg/g_0001..0024.webp`, uma volta em 24 frames), num suporte de parede no alto à direita, com os feixes varrendo a parede; loop por tempo (~16 fps, só com a cena visível), um frame parado em reduced motion.
- **Exemplos de 2–3 linhas:** queda de energia com ETO na câmara trava a máquina; a porta só abre na pressão atmosférica.

### 6. Registro · "Cada ciclo deixa um registro completo"

- **Corpo:** quem operou, qual carga, qual cilindro, quanto ETO, quanto durou cada fase, que alarmes ocorreram, resultado do leak test. Também os usuários com níveis de acesso e o CSV a cada segundo.
- **Visual:** relatório A4 que se monta linha por linha conforme rola. O conteúdo é coerente com as cenas anteriores (mesma massa injetada, mesmo lote) e tem campos de assinatura de operador e responsável.
- **Fecho:** a validação Labquali, "A Labquali faz a validação" (revisão do user, 2026-11-12): QI, QO, QD e validação do software, com a documentação pronta para a próxima inspeção.

### 7. CTA · "Agende uma avaliação técnica"

- **Corpo:** visita para levantar painel, instrumentação e utilidades e propor o retrofit.
- **Mecânica:** mesmo componente e destino de contato da caldeira (`#contato`). Botão do topo: "Agendar avaliação".

## Sequências 3D (minha call, builder pode ajustar)

| Sequência | Conteúdo | Frames / resolução |
|---|---|---|
| `seq/` hero | Órbita da máquina genérica → aproximação do painel | ~150 · 1920×1080 |
| `seqp/` painel | Painel antigo → painel novo, explodindo em camadas | ~90 · 1920×1080 ou 1280×720 |
| `seqe/` injeção | Válvula do cilindro → válvula pneumática em corte → recuo para balança + IHM (roteiro v3 na cena 4) | 112 · 1280×720 |

- A tela da IHM no 3D é a **tela real do AFR-ETO** (Injeção de ETO, captura de bancada `vivo/ciclo/182812_f06.png`), limpa de "modo simulação", usuário convidado e nome VAPOR01, com valores coerentes com a página (degrau 5 de 5, 0,90 kg). Revisão do user, 2026-11-11: "a tela tem que ser a do software AFR-ETO e não uma inventada". Na cena 3, a chamada da IHM mostra a mesma tela em recorte legível (`tela-ihm.webp`). O visor da balança segue neutro, com os números em overlay HTML.
- Painel antigo, painel novo, cilindro, balança e IHM ainda não existem no `cena.blend` e precisam ser modelados.
- Peso: a caldeira tem 10 MB com 230 quadros, e aqui são cerca de 320. Para caber em ≤ 12 MB, o builder reduz quadros e/ou resolução de `seqp/` e `seqe/` (minha call: priorizar a qualidade do hero e da injeção).
- Prévia em 960×540 antes do render final; mesmos samples e denoise dos demos anteriores.

## Copy e rigor

- pt-BR. "Óxido de etileno (ETO)" por extenso na primeira menção.
- Tudo é ilustrativo (revisão do user, 2026-11-12): "Imagens, telas e valores meramente ilustrativos" sob o texto do hero e no rodapé; na injeção, "Valores meramente ilustrativos". A ponte entre a faixa de fases e a injeção diz "Fase 5 · Injeção de ETO: dosagem gravimétrica, pela balança do cilindro."
- Fazer o mesmo passe de humanizer usado na caldeira.

## Entrega e verificação

- Build em `static/demos/retrofit-eto/` (ou `eto/`, ver controller); rota `/retrofit/eto`; versão 16.0.1.11.0.
- Testes do controller verdes, incluindo o novo teste da rota.
- Validação visual via `agent-browser` em desktop e mobile, antes de pedir teste ao user.
- Commit só após o user testar e aprovar (regra do projeto). Deploy no remoto só com autorização.

## Decisões minhas (para o user revisar)

- Máquina sem marca na faixa lateral (painel liso ou só "ETO"); a decisão de tirar a marca é do user.
- URL `/retrofit/eto` com prefixo novo `retrofit`.
- Três sequências 3D.
- Números por overlay HTML, e não no render.
- Painel antigo genérico, sem marca real.
- Curva do simulador reescalada.
- Nenhum link no menu nesta entrega.
