# MARSP: identidade visual e site de produtos

Data: 2026-11-13. Módulo: `afr_labquali_website` (monorepo, não é submodule).

## Intenção

MARSP é a marca dos equipamentos desenvolvidos em parceria pela AFR (São Luís, MA) e pela LabQuali (São Paulo, SP). Hoje a marca só existe como um painel provisório no render da autoclave ETO. O user quer:

1. Uma identidade visual para a MARSP, com logo.
2. Um site, linkado no site da LabQuali, que apresente os equipamentos **como uma montadora apresenta carros**: uma vitrine com a linha inteira e uma página por modelo, com imagem grande, destaques, ficha técnica e pedido de proposta.

O objetivo do visitante é **conhecer a linha toda**, não só pedir proposta de um item.

Esta entrega é para **ver o conceito**. O user aceitou explicitamente que dados técnicos saiam aproximados ou errados agora; serão corrigidos depois.

## Produtos da linha

| Produto | Código | Slug | Material de origem |
|---|---|---|---|
| Autoclave ETO 1500 L | MSP 1500-E | `autoclave-eto` | `PROPOSTAS/POINT SUTURE/Proposta Autoclave ETO 1500L Montroiz/` (`blender/cena.blend`, `proposta.md`); `CAMARAS ETO/Camara ETO 1500L.FCStd` |
| Gerador de vapor | a definir | `gerador-de-vapor` | `CAMARAS ETO/BOILER.FCStd`, `BOILER E GERADOR REV A.pdf`; `PROPOSTAS/AUTOMAÇÃO/GERADOR DE VAPOR/Gerador de vapor.xlsx` |
| Aquecedor (vaporizador) de gás ETO | a definir | `aquecedor-eto` | `PROPOSTAS/AMED/VAPORIZADOR ETO/Folha_Dados_Vaporizador_EtO_Rev4.docx` (casco-e-tubo horizontal, TEMA BEM, ~25 kW, 120 kg/h); `CAMARAS ETO/AQUECEDOR LINHA ETO/Aquecedor linha ETO.iam` |
| Psicrômetro 4–20 mA | a definir | `psicrometro` | `CAMARAS ETO/SENSOR DE UMIDADE.FCStd`; `ESP32/SENSOR_UMIDADE/SENSOR STANDALONE/` |

Todos os caminhos são relativos a `C:\Users\Afonso\OneDrive\Documentos\` (`/mnt/c/Users/Afonso/OneDrive/Documentos/` no WSL).

## Identidade (aprovada pelo user)

### Logo

Símbolo "C1": um aro vazado grosso (o horizonte de um buraco negro / planeta) cruzado por um anel achatado inclinado, que passa pela frente embaixo e por trás em cima, com uma folga separando as peças. Sem pixels, sem ponteiro.

Geometria de referência, em caixa 120×120 com centro (60, 60):

- Aro: círculo externo r = 35, interno r = 20.
- Anel: elipse externa rx = 58, ry = 12,5; elipse interna com as mesmas proporções × 0,64; rotação −36°.
- Folga entre anel e aro: 2,2.
- A metade "de trás" do anel (lado de cima no eixo do anel) fica oculta dentro do círculo de raio 35 + folga; a metade "da frente" recorta o aro com a folga.

O gerador de referência é `scratchpad/gen17.py` (função `eclipse`, variante `g1`) da sessão de brainstorm; os esboços aprovados estão em `.superpowers/brainstorm/2542215-1794603220/content/` (`logo-g1-cores.html`, `mockups-marca-v2.html`, `design-system-v2.html`). O builder deve reproduzir a forma em SVG limpo (paths resolvidos, sem máscaras), não copiar o gerador.

Nome: "MARSP" em Nasalization (Typodermic, "Nasalization Rg"), convertido em contornos no SVG, espaçamento 0,10em, ao lado do símbolo. A licença gratuita da Nasalization permite logo em SVG/imagem, mas não servir a fonte em site; por isso ela só existe como contorno e nunca como webfont.

2026-11-13: a fonte do nome foi trocada de Michroma para Nasalization a pedido do user.

Versões:

| Versão | Aro | Anel | Nome |
|---|---|---|---|
| Principal (fundo claro) | `#0A3D62` | `#FF6B35` | `#0A3D62` |
| Invertida (fundo escuro), a preferida | `#FFFFFF` | `#FF6B35` | `#FFFFFF` |
| Uma cor (gravação, carimbo) | uma cor | mesma cor | mesma cor |

Símbolo sozinho: mínimo 16 px. Com nome: mínimo 24 px de altura. Área livre: meia altura do símbolo em toda a volta.

### Cores

| Nome | Hex | Uso |
|---|---|---|
| Tinta | `#071E32` | fundos escuros, títulos |
| Azul MARSP | `#0A3D62` | cor da marca, links |
| Azul médio | `#1E6091` | apoio |
| Laranja | `#FF6B35` | botão principal, anel do logo |
| Laranja escuro | `#C2410C` | texto e código laranja sobre branco |
| Ardósia | `#5A7184` | texto secundário |
| Aço | `#C6CDD4` | bordas de campo |
| Fio | `#E0E8F0` | divisórias |
| Névoa | `#EEF2F5` | etiquetas, fundo de foto |
| Gelo | `#F4F7FA` | seção alternada |

São as cores do site da LabQuali (`DESIGN.md`), de propósito, para a página encaixar. O laranja fica restrito a ação e ao anel; não vira fundo de seção.

### Tipografia e medidas

- Nasalization (em contornos): só no nome "MARSP" dentro do logo.
- Michroma: só em códigos de modelo exibidos como texto vivo, porque a licença gratuita da Nasalization não cobre uso como webfont.
- Inter: todo o resto. Título de página 800 48/1,1; seção 800 34/1,15; subtítulo 700 22/1,3; texto 400 17/1,6; pequeno 400 14/1,5; números de ficha 600 tabular.
- Espaçamento: 4, 8, 12, 16, 24, 32, 48, 80. Seções com 80 px verticais.
- Cantos: 6 (botão, campo), 10 (bloco), 14 (card), 20 (etiqueta).

### Componentes

Botão primário (laranja), secundário (contorno azul; contorno branco em fundo escuro), link com seta; etiqueta em pílula; card de produto (imagem, código em Michroma, nome, até 3 características, link); tabela de ficha técnica; campo de formulário; faixa de assinatura "Uma parceria AFR · LabQuali / São Luís · MA | São Paulo · SP".

## Site

### Abordagens consideradas

- **A. Uma página só** com uma seção por equipamento. Rápida, mas nenhum produto tem página própria; não lembra site de montadora.
- **B. Vitrine + uma página por produto**, com imagens estáticas. Estrutura certa, sem o impacto visual.
- **C. B com abertura 3D animada pela rolagem em cada página**, no padrão das demos que já existem no módulo (`/inspecao/caldeira`, `/retrofit/eto`). **Escolhida pelo user.** Custo: exige modelo 3D de cada equipamento; hoje só a autoclave tem cena Blender pronta.

### Estrutura

- `/marsp`: vitrine. Abertura com a marca, a linha com os quatro produtos lado a lado (render de cada um, nome, uma frase, link), bloco sobre a parceria AFR + LabQuali, chamada para proposta.
- `/marsp/<slug>`: página do produto. Abertura 3D dirigida pela rolagem (o equipamento gira/se abre), 3 a 4 destaques amarrados a momentos da animação, galeria de renders, ficha técnica, links para os outros produtos da linha, pedido de proposta.

### Como se encaixa no módulo

- Páginas são builds estáticos em `static/demos/<pasta>/`, servidos pelo controller `controllers/demos.py`, que hoje atende os prefixos `qualificacao`, `inspecao` e `retrofit`. Acrescentar o prefixo `marsp` e a rota índice `/marsp`. O slug `eto` já é da página de retrofit; as pastas da MARSP usam nomes próprios (ex.: `marsp`, `marsp-autoclave-eto`).
- Reusar o motor de rolagem e o `_vendor` das demos atuais, e o mesmo mecanismo de pedido de proposta/contato usado em `/retrofit/eto`.
- 3D em Blender, renderizado em sequência de quadros (como a caldeira, 150 quadros), com alternativa estática para `prefers-reduced-motion` e versão mais leve no celular.
- Arquivos do logo e as variáveis de cor/fonte da MARSP ficam em um lugar só e são usados por todas as páginas MARSP.
- Testes no padrão de `tests/test_retrofit_eto.py`.
- Regra do módulo: bump de `version` no `__manifest__.py` em todo commit (feat → MINOR).

### Etapas

Cada etapa tem plano próprio, é entregue e testada pelo user antes da seguinte.

1. **Marca.** SVGs finais do logo (três versões, símbolo sozinho, favicon), variáveis de cor e fonte.
2. **Vitrine + autoclave ETO.** `/marsp` e `/marsp/autoclave-eto` com 3D, a partir da `cena.blend` existente, agora **com** a marca MARSP no painel. Na vitrine, os outros três aparecem como silhueta "em breve" (ver decisões).
3. **Gerador de vapor.** Modelo 3D a partir do `BOILER.FCStd` e dos PDFs; página.
4. **Aquecedor de gás ETO.** Modelo 3D a partir da folha de dados (casco-e-tubo horizontal) e do `.iam` se abrir; página.
5. **Psicrômetro.** Modelo 3D a partir do `SENSOR DE UMIDADE.FCStd`; página.

## Metas, não-metas, antimetas

**Metas**
- O visitante entende que a MARSP é uma linha de equipamentos para esterilização por ETO e vê os quatro produtos.
- Cada produto tem página própria com presença visual de "modelo de carro".
- A página parece parte da família LabQuali e, ao mesmo tempo, uma marca própria.

**Não-metas**
- Exatidão dos dados técnicos nesta fase (conceito).
- Preços, configurador, área de cliente, catálogo em PDF.
- Aplicações impressas da marca (cartão, papel timbrado): ficaram só como mockup.
- Deploy no servidor remoto e item de menu no site: só com autorização do user, depois do teste local.

**Antimetas**
- Parecer template SaaS genérico (ver `PRODUCT.md`: cards idênticos repetidos, rótulo em maiúsculas sobre toda seção, gradiente decorativo).
- Vazar dado de cliente ou comercial dos documentos de origem: nada de nomes de clientes (AMED, Point Suture etc.), TAGs de projeto ou valores de proposta.
- Reintroduzir pixels, ponteiro de manômetro ou outras ideias de logo já descartadas.

## Restrições

- Odoo 16; container próprio na porta 8083; testes via agente `test-runner`; commits via agente (`git-commit-push`), só depois de o user testar.
- Texto em pt-BR, no tom do `PRODUCT.md` (técnico, direto, sem hype), passado pelo humanizer.
- Material de origem está no Windows (`/mnt/c/...`), em FreeCAD, Inventor, DOCX, XLSX e PDF. Arquivos `.iam` do Inventor podem não abrir no ambiente; nesse caso modelar pela folha de dados.

## Decisões minhas (o user pode vetar)

- Rotas `/marsp` e `/marsp/<slug>` com os slugs da tabela.
- Só a autoclave mostra código de modelo; os outros três aparecem sem código até o user definir.
- A página não cita a Montroiz (fabricante metalúrgica da autoclave); a assinatura é "AFR · LabQuali".
- Dados que não constarem nos documentos são omitidos, não inventados; os que constarem entram mesmo que preliminares.
- Ordem das etapas 3 a 5.
- Texto da assinatura da parceria e chamadas de exemplo dos mockups são rascunho.
- **Pedido de proposta é um link de e-mail**, igual ao de `/retrofit/eto` (`mailto:labquali@labquali.com.br` com assunto pronto, citando o produto). Não há formulário nesta fase: as páginas continuam 100% estáticas e o controller só ganha o prefixo `marsp`. O "campo de formulário" do design system fica reservado para uma fase futura.
- **Na vitrine da etapa 2, os três produtos sem modelo 3D aparecem como "teaser"**, do jeito que montadora anuncia modelo novo: silhueta escura do equipamento em SVG, contraluz, com "em breve". Não se antecipa modelagem das etapas 3 a 5. Quando cada produto ganha sua página, a silhueta é trocada pelo render.

## Deixado para o builder

- Roteiro de câmera e momentos de destaque de cada animação.
- Quantidade de quadros e resolução por dispositivo.
- Estrutura interna de arquivos dentro de `static/demos/`.
- Redação final dos textos, a partir dos documentos de origem.
