# Demo "Inspeção NR-13 em caldeira" — design

Data: 2026-11-10. Módulo: `afr_labquali_website`. Status: revisado por builder-check; aguardando aprovação do user.

## Intenção

Quinta página de demonstração do site Labquali, irmã das quatro de qualificação térmica
(`/qualificacao/autoclave`, `termodesinfectora`, `estufa`, `camara-fria`). Mostra, em scroll
cinematográfico com render 3D, como a Labquali faz uma **inspeção de segurança NR-13 em
caldeira**. Objetivo comercial: visitante (engenharia clínica, manutenção hospitalar,
lavanderia, indústria média) entende o que é a inspeção, percebe rigor técnico e pede
orçamento. Objetivo de posicionamento: sinalizar que a Labquali atende NR-13 além de
autoclaves.

O user pediu acabamento **excepcional**: este demo deve superar os anteriores em detalhe de
modelagem e sincronismo entre 3D e dados, não apenas igualar.

## Goals

- Página estática `static/demos/caldeira/` servida pelo controller existente em
  `controllers/demos.py` (adicionar slug à tupla `DEMOS`), mesma engine `scrollcraft.js`,
  mesmo visual (tema escuro, laranja `#ff6a2b`, mono para números, logo Labquali).
- Dois clímax com dados simulados sincronizados ao 3D: **medição de espessura por
  ultrassom** e **ensaio da válvula de segurança**.
- Copy tecnicamente correta conforme NR-13 redação 2022 (Portaria MTP 1.846/2022). Fonte
  de verdade: `docs/superpowers/research/2026-11-10-nr13-caldeiras.md` e texto da norma em
  `/tmp/claude-1000/.../scratchpad/dl/sp.pdf.txt` (se já expirou, baixar o PDF listado na
  pesquisa).
- Desktop e mobile funcionando; mobile com motion reduzida como nos demos anteriores.

## Non-goals

- Não é módulo de gestão de inspeções no Odoo. Nada de models, nada de dados do banco.
- Não cobre vasos de pressão, tubulações nem tanques. Uma linha no fechamento pode citar
  "também inspecionamos autoclaves e vasos de pressão" e linkar o demo de autoclave.
- Não substitui o link no menu do site (conteúdo é builder-owned no banco; user adiciona o
  item no menu "Como qualificamos" depois, ou pede separado).

## Anti-goals (falha mesmo funcionando)

- Afirmar algo que a NR-13 2022 não diz: "PH", "teste hidrostático periódico obrigatório",
  "caldeira aposenta aos 25 anos", "categoria por PMTA", prazo diferente de 12 meses para
  cat. B sem SPIE/SGC.
- Marca de fabricante visível na caldeira ou na válvula (modelo genérico, como os anteriores).
- Página pesada demais: alvo ≤ 12 MB total por demo (os atuais ficam entre 5,4 e 7,8 MB;
  este tem duas sequências). Engine carrega sequência inteira também no mobile.
- Parecer template: cada clímax tem composição própria, não é "gráfico ao lado do render".

## Restrições e contexto técnico

- Odoo 16, porta host 8083, container com entrypoint custom. Bump de versão obrigatório no
  `__manifest__.py` a cada commit (feat → MINOR: 16.0.1.7.x → 16.0.1.8.0).
- Pipeline 3D já existe em `/mnt/c/Users/Afonso/scrollcraft_blender/` (Windows, Blender 5.2.2
  LTS, Cycles). Padrão: um script procedural por equipamento (`autoclave.py`, `camara.py`,
  `estufa.py`) + `anim.py` que importa o modelo via `SC_MODEL`, anima câmera e renderiza
  frames `f_0001..f_0150.webp` em 1920×1080. Logs `prev*.log`/`render*.log` mostram a
  invocação. Referências visuais das válvulas em `ref_caldeira/`.
- Engine: `static/demos/_vendor/scrollcraft.js` (cópia por demo). Atos `scrub|pin|pan|flow`,
  `data-sc-sequence`, `data-sc-cue`, `data-sc-count`, `data-sc-reveal`. Ler cabeçalho do
  arquivo antes de autorar.
- O demo de autoclave (`static/demos/autoclave/index.html`, 732 linhas) é a referência de
  estrutura: hero scrub 150 frames → pin com simulação (SVG chart dirigido por `--sc-p`) →
  flow de método → pan de laudos → pin de CTA.

## O equipamento (dados simulados, fixos no HTML)

Caldeira flamotubular horizontal, 3 passes, gás natural. Placa:

| Campo | Valor |
|---|---|
| Fabricante | genérico, sem nome |
| Nº de ordem | 2014-0471 |
| Ano | 2014 |
| PMTA | 10,5 kgf/cm² (1,03 MPa) |
| Capacidade | 2.000 kg/h |
| Superfície de aquecimento | 55 m² |
| Código | ASME I, ed. 2010 |
| Pressão de operação | 7,0 kgf/cm² |
| Categoria | **B** (operação < 1.960 kPa) → periódica a cada **12 meses** |

Duas válvulas de segurança flangeadas no topo (tipo mola, alavanca), ajustadas em 10,0 e
10,5 kgf/cm². Instalada em casa de caldeiras: piso industrial, parede ao fundo, luz lateral
de janela/telha translúcida, leve vapor nos purgadores.

## Roteiro do scroll (6 seções, aprovado pelo user)

### 1. Hero · `data-sc-act="scrub"` · sequência principal (~150 frames)

Caldeira aparece em orbita lenta na casa de caldeiras. Título "Inspeção de segurança
NR-13". Subtítulo: "Feita por engenheiro legalmente habilitado, com ART. Relatório em até
60 dias." Durante o scrub a câmera percorre: vista 3/4 frontal (queimador) → lateral com as
válvulas no topo → aproxima do costado (prepara o ultrassom). Beats de texto nos pontos de
parada, como `beat--door`/`beat--inside` do autoclave.

### 2. Enquadramento · `pin` curto

Placa de identificação renderizada em HTML (não no 3D) surgindo sobre o frame parado. Campos
aparecem um a um (`data-sc-cue`). Chip final: "Categoria B — inspeção interna e externa a
cada 12 meses (NR-13, 13.4.4.4)". Nota discreta: "Categoria A a partir de 1.960 kPa de
pressão de operação (13.4.1.1)."

### 3. Etapas · `flow`

Seis passos em linha, mesmo componente de método do autoclave: 1 documentos e Registro de
Segurança → 2 parada, resfriamento, bloqueio → 3 exame externo → 4 exame interno (lado água e
lado fogo) → 5 ensaios: ultrassom e válvula de segurança → 6 relatório e anotação no Registro.
Cada passo com uma frase e o subitem da norma em nota.

### 4. Clímax 1 · Ultrassom · `pin` longo (span ~6)

Composição: frame do costado em close (vem da sequência principal ou de sequência curta
dedicada; ver "Sequências 3D"). Sobre o frame, pontos de medição aparecem em ordem (HTML
absoluto, posições calibradas para o frame fixo). Ao lado, painel do aparelho de ultrassom:
**A-scan** em SVG (pulso inicial + eco de fundo, posição do eco proporcional à espessura),
leitura grande em mm (`data-sc-count`), cor do ponto verde/amarelo/vermelho vs mínimo.

Sequência de pontos e valores (todos em mm):

| Região | Pontos | Nominal | Mínimo | Leituras |
|---|---|---|---|---|
| Costado | C1..C6 | 12,7 | 10,0 | 12,4 · 12,5 · 12,2 · 12,6 · 12,3 · 12,1 |
| Espelho frontal | E1..E3 | 19,0 | 15,0 | 18,6 · 18,4 · 17,9 |
| Fornalha | F1..F3 | 12,7 | 9,5 | 12,0 · 11,4 · **10,8** (alerta) |

F3 pulsa em vermelho/âmbar. Fecho do ato: card "Vida remanescente" com fórmula em texto
plano (taxa = (12,7 − 10,8) / 12 anos = 0,16 mm/ano; vida = (10,8 − 9,5) / 0,16 ≈ 8 anos) e
uma barra/linha do tempo 2014 → 2026 → 2034 (fim da vida pela taxa atual) com marco
"2039: 25 anos, avaliação de integridade obrigatória (13.4.4.6)". Ano 2014 foi escolhido
para a aritmética fechar com 12 anos de operação em 2026 (decisão minha). Recomendação exibida: "Reinspecionar fornalha em 12 meses; próxima inspeção
≤ metade da vida remanescente."

### 5. Clímax 2 · Válvula de segurança · `scrub` dedicado (~90 frames)

Sequência 3D própria. Cena: **bancada de teste** ao lado da caldeira (decisão do user):
a válvula de 10,5 kgf/cm² já desmontada, flange presa a um cabeçote de teste, manômetro
padrão e linha de pressão à vista; ao fundo, desfocada, a caldeira com o bocal vazio. Câmera
parte da caldeira e desliza até colar na válvula na bancada. No meio da sequência o corpo
da válvula passa a **corte** (metade do casco removida, estilo cutaway das referências):
mola, haste, disco e sede visíveis. Nos pops a mola comprime, o disco levanta e sai jato
(ar comprimido/vapor da bancada). Três pops, depois reassentamento. Corte e jato são
animados no Blender (shape keys/keyframes), não em CSS.

Overlay HTML sincronizado ao mesmo `p`: gráfico pressão × tempo em SVG com linha tracejada
da PMTA (10,5) e faixa de tolerância ±3 %; curva sobe, marca pop 1 (10,42), desce
(blowdown ~7 %), pop 2 (10,47), pop 3 (10,45). Leitura ao vivo em kgf/cm² (pressão da bancada, não da caldeira). Ao final:
carimbo "APROVADA — abertura ≤ PMTA (13.4.1.2 'a')" e certificado nº CV-2026-0187 que
reaparece no relatório. Nota: "Válvula desmontada, inspecionada e testada em bancada no
prazo da inspeção periódica (13.4.4.7). Teste em campo só em caráter excepcional
(13.4.4.7.1)."

Dica de produção: os três pops devem ocupar janelas de `p` conhecidas (ex.: 0,38, 0,58,
0,78) para que frames e SVG casem. Registrar esses índices de frame no HTML como constantes.

### 6. Relatório e CTA · `pan` + `pin`

Rail horizontal de páginas do relatório, com conteúdo real das seções anteriores: capa com
dados da placa e categoria; página de exame interno com 2 fotos (frames do 3D interno ou do
close); mapa de espessura (mesma tabela da seção 4); certificado da válvula; "Itens da NR-13
não atendidos: nenhum" ou um item leve (ex.: "sensor de gás ausente na casa de caldeiras,
13.4.2.4 'd'", a critério do builder, dá verossimilhança); parecer conclusivo; próxima
inspeção 2027-11; assinatura do PLH com nº CREA fictício e ART. Rodapé dos 14 itens do
13.4.4.12. Fecho: "Solicite sua inspeção" com o mesmo botão/contato dos outros demos e link
"Também fazemos autoclaves e vasos de pressão" → `/qualificacao/autoclave`.

## Sequências 3D (decisão minha, builder pode ajustar)

Para manter peso: **duas** sequências.

- `seq/` principal, 150 frames 1920×1080 webp (~47 KB/frame): orbita + aproximação do
  costado → **porta frontal abre** → frame final mostra espelho frontal e boca da fornalha
  com o costado ainda no quadro. Esse frame final é o fundo das seções 2 e 4: os pontos
  C (costado), E (espelho) e F (fornalha, pela boca) ficam todos visíveis nele. Isso exige
  modelar porta articulada, espelho com tubos/solda tubo-espelho e entrada da fornalha
  (decisão minha; o interior completo não é modelado).
- `seqv/` válvula, ~80 frames em **1280×720** (close aguenta; mantém o total ≤ 12 MB):
  orbita até a válvula, corte, 3 pops com vapor, reassentamento.

Fotos do exame interno no relatório (seção 6): 2 stills renderizados à parte (não
sequência) do espelho/boca da fornalha, 1280×720. Qualidade: Cycles, samples iguais aos demos anteriores,
denoise; prévia em 960×540 antes do render final.

Modelagem (`caldeira.py`, procedural, sem marca): casco cilíndrico horizontal com isolamento
e chapa de acabamento, espelhos frontal/traseiro com parafusos, queimador frontal com
ventilador, porta frontal com dobradiças, câmara de reversão traseira com chaminé, skid com
pés, duas válvulas flangeadas no topo (corpo angular, castelo, mola visível no corte,
alavanca), manômetro, visor de nível com colunas, bomba de alimentação, purgadores com vapor
(volumétrico leve ou partículas com emissão, o que for mais barato em render). Válvula com
detalhe suficiente para close a tela cheia: chanfros, parafusos reais, textura fundida.

## Copy e rigor

- Escrever "PLH" e expandir uma vez: "Profissional Legalmente Habilitado".
- Cada afirmação normativa com subitem entre parênteses ou nota de rodapé discreta.
- Todos os números são simulados: nota de rodapé única "Dados ilustrativos de uma caldeira
  fictícia" como nos demos anteriores.
- pt-BR.

## Entrega e verificação

- Build em `static/demos/caldeira/`; slug `caldeira` em `DEMOS`; versão 16.0.1.8.0.
- Testar no Odoo local (8083) com `agent-browser`: desktop 1440 e mobile 390, scroll
  completo, sem erro de console, frames carregando, pops casando com a curva.
- Lighthouse/peso: total de assets ≤ 12 MB.
- Deploy remoto só após OK do user (regra do projeto: commit após teste do user).

## Deixado ao builder

- Posições exatas da câmera, ritmo dos spans, easing dos cues.
- Como animar o corte da válvula (boolean animado vs. duas malhas com visibilidade).
- Vapor: volumétrico vs. sprites.
- Se os pontos de ultrassom ficam sobre frame fixo (mais simples) ou acompanham câmera por
  pequeno trecho (mais vistoso; só se calibrar for barato).
- Item "não atendido" do relatório: nenhum ou um leve.
