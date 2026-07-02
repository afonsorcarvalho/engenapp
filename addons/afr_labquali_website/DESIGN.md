---
name: LabQuali Website
description: Landing institucional de qualificação e calibração de equipamentos — autoridade metrológica em navy + laranja
colors:
  engineering-navy: "#0A3D62"
  navy-mid: "#1E6091"
  ink-navy: "#071E32"
  calibration-orange: "#FF6B35"
  calibration-orange-deep: "#D9482A"
  slate-gray: "#5A7184"
  pale-surface: "#EEF2F5"
  fog-surface: "#F4F7FA"
  hairline: "#E0E8F0"
  paper: "#FFFFFF"
typography:
  display:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "3rem"
    fontWeight: 900
    lineHeight: 1.1
    letterSpacing: "-0.1rem"
  headline:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "2.375rem"
    fontWeight: 900
    lineHeight: 1.1
    letterSpacing: "-0.0625rem"
  title:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "2.125rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.05rem"
  body:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "2.5px"
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
  pill: "20px"
spacing:
  section-y: "80px"
  card-pad: "20px"
  gutter: "18px"
components:
  button-primary:
    backgroundColor: "{colors.calibration-orange}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "8px 20px"
  button-primary-hover:
    backgroundColor: "{colors.calibration-orange-deep}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "8px 20px"
  cta-button:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.engineering-navy}"
    rounded: "8px"
    padding: "16px 40px"
  service-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.slate-gray}"
    rounded: "{rounded.lg}"
    padding: "20px 18px 22px"
  equip-item:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.engineering-navy}"
    rounded: "{rounded.md}"
    padding: "20px 12px"
---

# Design System: LabQuali Website

## 1. Overview

**Creative North Star: "The Certified Blueprint"**

LabQuali é uma planta técnica certificada, não um folheto de vendas. O fundo é
o azul de engenharia — profundo, sóbrio, o azul de um documento de projeto
carimbado. Sobre ele, marcações em laranja de calibração aparecem exatamente
onde uma medida importa: o CTA, o número de prova, a palavra que carrega o
valor. Nada é decorativo; cada acento é uma cota. A hierarquia tipográfica faz
o trabalho da diagramação de uma folha técnica: pesada, apertada nos títulos,
precisa no corpo.

O sistema comunica **rigor, confiança e competência técnica** (PRODUCT.md).
Rejeita explicitamente o template SaaS genérico: cards idênticos infinitos,
eyebrow uppercase acima de toda seção, hero-metric com gradiente, hype de
startup. A credibilidade vem de prova visível (equipamentos, normas, clientes
reais) e de execução impecável do layout, não de scaffolding de landing.

O laranja é escasso por doutrina. Num mundo de landings navy-and-orange
corporativas, o que diferencia aqui é o **contraste de temperatura controlado**
— laranja quente pontual sobre navy frio dominante — e a densidade de prova
técnica, não a paleta em si.

**Key Characteristics:**
- Navy de engenharia domina; laranja de calibração pontua ≤15% da superfície.
- Contraste tipográfico por peso (400→900), não por família.
- Superfícies planas; profundidade só em hover/estado.
- Prova técnica sobre adjetivos de marketing.

## 2. Colors

Paleta committed de dois polos: navy frio de engenharia como base institucional,
laranja quente de calibração como sinal de ação/valor. Neutros são navy
dessaturado, nunca cinza puro.

### Primary
- **Engineering Navy** (#0A3D62): cor institucional. Fundo de seções de
  autoridade (diferenciais), títulos de seção, cor de texto de headings sobre
  claro, badges de card. É o "papel" do blueprint.
- **Navy Mid** (#1E6091): navy mais claro para gradientes e camadas
  intermediárias do hero/diferenciais.
- **Ink Navy** (#071E32): navy quase-preto. Base do gradiente do hero, fundo do
  footer, o ponto mais escuro do sistema.

### Tertiary (accent)
- **Calibration Orange** (#FF6B35): o sinal. CTA primário, palavra de valor
  dentro de títulos (`<span>`), número de estatística, borda-topo de card
  (3px), tag de seção. Escasso e deliberado.
- **Calibration Orange Deep** (#D9482A): estado hover do laranja. Nunca em
  repouso.

### Neutral
- **Slate Gray** (#5A7184): texto de corpo secundário sobre superfície clara,
  logos de cliente. Navy dessaturado, não cinza neutro.
- **Fog Surface** (#F4F7FA): fundo de seções claras alternadas (equipamentos).
- **Pale Surface** (#EEF2F5): superfície mais pálida, hover de botão claro.
- **Hairline** (#E0E8F0): bordas de card e divisores sobre claro.
- **Paper** (#FFFFFF): fundo de seções de serviços/clientes e de cards.

### Named Rules
**The Calibration Point Rule.** Calibration Orange aparece só onde há uma medida
a marcar: o CTA, o número de prova, a palavra de valor no título. Nunca como
preenchimento nem como cor de bloco grande. Sua raridade é a mensagem — laranja
em toda parte vira ruído de startup.

**The Cold-Warm Rule.** Navy é frio e domina; laranja é quente e pontua. Nunca
inverter o domínio. O calor da marca vem do acento e da tipografia, nunca do
fundo.

## 3. Typography

**Display / Body Font:** Inter (fallback 'Segoe UI', Arial, sans-serif)

**Character:** uma única família geométrica-neutra carregada por contraste de
peso extremo — 400 no corpo, 800-900 nos títulos. Inter já é a identidade
embarcada (self-hosted via afr_labquali_layout); preservação de identidade vence
a regra greenfield de evitar Inter. A voz vem do peso e do tracking apertado dos
títulos, não de um pairing.

### Hierarchy
- **Display** (900, 3rem, lh 1.1, ls -0.1rem): H1 do hero. Único no fold. Cai
  para 2.25rem ≤768px. Branco sobre navy, com `<span>` laranja na palavra-valor.
- **Headline** (900, 2.375rem, lh 1.1, ls -0.0625rem): H2 do CTA final.
- **Title** (800, 2.125rem, lh 1.2, ls -0.05rem): título de seção
  (`.lq-section-title`). Navy sobre claro, ou branco sobre navy nos diferenciais.
- **Body** (400, 1.0625rem hero / 0.8125rem cards, lh 1.6): parágrafos. Corpo de
  card em Slate Gray; sub-hero em branco 70%. Cap em ~65ch.
- **Label** (700, 0.6875rem, ls 2.5px, uppercase): tags de seção, badges,
  labels de estatística. **Uso restrito — ver regra abaixo.**

### Named Rules
**The Weight-Not-Family Rule.** Contraste de hierarquia vem do peso (400 vs 900)
numa família só. Nunca introduzir uma segunda família "para dar contraste" — Inter
em peso extremo já resolve.

## 4. Elevation

Sistema plano por padrão. Superfícies em repouso não têm sombra; profundidade é
resposta a estado (hover). O blueprint é chapado; o relevo aparece só quando o
usuário toca.

### Shadow Vocabulary
- **Navy Lift** (`box-shadow: 0 8px 32px rgba(10,61,98,0.12)`): hover de service
  card. Sombra tingida de navy, nunca preto neutro.
- **Deep Lift** (`box-shadow: 0 8px 32px rgba(0,0,0,0.3)`): hover de card sobre
  fundo navy (diferenciais), onde a sombra tingida some.
- **Soft Lift** (`box-shadow: 0 4px 16px rgba(10,61,98,0.1)`): hover de item de
  equipamento, mais discreto.
- **CTA Float** (`box-shadow: 0 8px 32px rgba(0,0,0,0.25)`): botão branco do CTA
  em repouso — única sombra permanente, porque flutua sobre gradiente.

### Named Rules
**The Flat-By-Default Rule.** Superfícies são planas em repouso. Sombra só como
resposta a hover/elevação. Sombras de superfície clara são tingidas de navy
(rgba 10,61,98), não preto.

## 5. Components

### Buttons
- **Shape:** cantos suaves (6px; CTA 8px).
- **Primary:** Calibration Orange, texto branco, peso 700, padding 8px 20px.
  Firme e decisivo — "preciso e confiante".
- **Hover:** vira Calibration Orange Deep (#D9482A). Transição de cor simples.
- **CTA (invertido):** fundo branco, texto Engineering Navy, peso 800, padding
  16px 40px, CTA Float shadow permanente. Vive sobre o gradiente navy→laranja da
  seção final; hover → Pale Surface (#EEF2F5).

### Cards / Containers
- **Corner Style:** 14px (service/diff), 12px (equip), 10px (client logo).
- **Background:** Paper sobre claro; branco 6% translúcido sobre navy
  (diferenciais).
- **Shadow Strategy:** plano em repouso; Navy Lift / Deep Lift no hover +
  translateY(-3px).
- **Border:** Hairline (#E0E8F0) sobre claro; branco 12% sobre navy.
- **Signature — topo laranja:** `.lq-card-body` tem `border-top: 3px solid
  Calibration Orange`. Marcação de cota, não faixa lateral decorativa — é o
  único stripe permitido e é no topo, cheio, semântico.
- **Internal Padding:** 20px 18px 22px.

### Navigation
- Navbar branca, `border-bottom: 2px solid Engineering Navy`, sombra navy 8%.
  Brand em navy peso 800 com `<span>` laranja. Links navy 0.875rem/500 → hover
  laranja. Botão CTA laranja embutido.

### Signature — Hero
- Gradiente diagonal `135deg` de Ink Navy → Engineering Navy → laranja-tingido
  no canto (`#1a0a00`), com glow radial laranja 12% a 80% 50%. Badge de pílula
  laranja translúcida. Barra de estatísticas com números laranja peso 900 +
  labels uppercase, separada por hairline branca 10%.

## 6. Do's and Don'ts

### Do:
- **Do** manter Calibration Orange (#FF6B35) em ≤15% da superfície — CTA, número
  de prova, palavra-valor no título. Rarididade é a mensagem (The Calibration
  Point Rule).
- **Do** contrastar hierarquia por peso Inter (400→900), família única (The
  Weight-Not-Family Rule).
- **Do** tingir sombras de superfície clara com navy (`rgba(10,61,98,x)`), nunca
  preto neutro.
- **Do** manter superfícies planas em repouso; sombra só em hover.
- **Do** usar o `border-top` laranja de 3px no corpo do card como marcação de
  cota — cheio, no topo, semântico.

### Don't:
- **Don't** virar isto num **template SaaS genérico** (anti-ref de PRODUCT.md):
  cards idênticos infinitos, hero-metric com gradiente, hype de startup.
- **Don't** repetir a **tag uppercase-tracked (`.lq-section-tag`) acima de toda
  seção** — é o eyebrow-scaffold de AI. Bane pela anti-ref "template SaaS
  genérico"; usar no máximo como um kicker nomeado deliberado, não como gramática
  de seção. Preferir outra cadência (número real de sequência, ou nada).
- **Don't** inverter o domínio cold-warm: navy sempre domina, laranja sempre
  pontua. Fundo laranja de bloco grande é proibido.
- **Don't** introduzir segunda família tipográfica "para variar".
- **Don't** usar `border-left`/`border-right` colorido >1px como faixa lateral
  decorativa em card ou callout.
- **Don't** deixar texto cinza claro (Slate Gray) sobre fundo tingido em corpo
  longo sem checar contraste 4.5:1 — puxar para o navy se ficar perto.
