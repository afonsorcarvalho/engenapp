# LabQuali Website — Design Spec

**Date:** 2026-06-23
**Module:** `afr_labquali_website`
**Odoo:** 16.0

## Goal

Landing page institucional para a LabQuali (qualificação/calibração de equipamentos de esterilização). Público: clientes potenciais chegando via Google. Estilo: impactante — hero full-screen dark, laranja bold, Navy dominant.

## Brand

Vars já definidas em `afr_labquali_layout`:
- `--lq-brand: #0A3D62` (navy primário)
- `--lq-brand-2: #1E6091` (navy secundário)
- `--lq-accent: #FF6B35` (laranja)
- `--lq-gray: #5A7184`
- `--lq-gray-light: #EEF2F5`
- Font: Inter (woff2 já em `afr_labquali_layout/static/fonts/inter/`)

## Architecture

Novo módulo `afr_labquali_website` (subdiretório em `addons/`, NÃO submodule).

**Depends:** `website`, `website_form`, `afr_labquali_layout`

### Files

```
afr_labquali_website/
├── __manifest__.py
├── __init__.py
├── static/src/scss/
│   └── labquali_website.scss      # brand vars + section styles
├── views/
│   ├── labquali_homepage.xml      # homepage QWeb template (extends website.layout)
│   └── website_layout_override.xml  # header/footer custom overrides
└── data/
    └── website_data.xml           # website.page record + menu items
```

## Sections (em ordem)

1. **Nav** — fixed top, navy bg, logo LQ left, links + CTA button right
2. **Hero** — full-viewport-height, dark navy gradient + geometric circles, h1 impactante, badge normas, 3 stats bottom, 2 CTA buttons
3. **Serviços** — 4 cards (Qualificação IQ/OQ/PQ, Calibração, NR13, Mapeamento Térmico), borda laranja topo
4. **Diferenciais** — fundo navy, 6 cards translúcidos, ícones Unicode
5. **Equipamentos** — fundo cinza claro, grid 6×2 (12 equipamentos)
6. **Clientes** — grid 5×2 placeholders (editar no builder depois)
7. **CTA Final** — banner gradiente navy→laranja, botão branco → form Odoo (`/contactus`)
8. **Rodapé** — dark navy, 4 colunas (brand, serviços, empresa, contato)

## Implementation Approach

- Homepage = QWeb template `afr_labquali_website.labquali_homepage` extends `website.layout`
- SCSS injected via `website.assets_frontend` asset bundle
- `website.page` record aponta para o template, URL `/`
- Header/navbar: override SCSS para aplicar navy bg + overrides de cor
- Footer: template override com estrutura custom (4 colunas)
- CTA "Solicitar Orçamento" → link para `/contactus` (formulário nativo Odoo)

## Out of Scope

- Shop (`/shop`) — não alterado
- Portal cliente — não alterado
- Conteúdo dos clientes (logos reais) — placeholders por ora
- Textos finais — copy rascunho no template, user ajusta via Website Builder ou dev

## Copy (rascunho)

### Hero
- Badge: `✓ ISO 17025 · RDC 665/2022 · NR13`
- H1: `Qualificação e Calibração de Equipamentos de Esterilização`
- Sub: `Laudos técnicos com rastreabilidade metrológica para autoclaves, estufas, câmaras de estabilidade e inspeções NR13.`
- Stats: `+500 Equipamentos/ano` · `15+ Anos de experiência` · `100% Laudos rastreáveis`

### Serviços
1. Qualificação IQ/OQ/PQ — conforme RDC 665/2022
2. Calibração de Sensores — rastreabilidade RBC/Inmetro
3. Inspeção NR13 — vasos de pressão e caldeiras
4. Mapeamento Térmico — câmaras e estufas

### Diferenciais
1. Rastreabilidade Metrológica
2. Laudos em até 5 dias úteis
3. Equipe Especializada
4. Portal do Cliente
5. Atendimento Nacional
6. Conformidade Regulatória (ANVISA/MTE)

### Equipamentos (12)
Autoclaves, Estufas, Câmaras Estabilidade, Câmaras Frias, Incubadoras, Geladeiras Farmacêuticas, Vasos de Pressão, Caldeiras, Liofilizadores, Túneis de Calor, Lavadoras Ultrassônicas, Termômetros/Sondas

### CTA Final
- H2: `Pronto para estar em conformidade?`
- P: `Solicite orçamento sem compromisso. Equipe técnica responde em até 24h úteis.`
- Botão: `Solicitar Orçamento Gratuito →`
