# LabQuali Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar módulo Odoo 16 `afr_labquali_website` com landing page institucional completa para a LabQuali.

**Architecture:** Módulo independente (não submodule) em `addons/afr_labquali_website/`. SCSS injetado em `web.assets_frontend` para brand colors + navbar navy. Homepage = QWeb template `labquali_homepage` registrado como `website.page` em `/`. Footer = override de `website.footer_custom`.

**Tech Stack:** Odoo 16 QWeb, Bootstrap 5 (bundled com Odoo), SCSS, `website` module, `website_form`, `afr_labquali_layout` (fontes Inter).

## Global Constraints

- Odoo 16.0 — sintaxe QWeb Odoo 16 (atributos `t-attf-`, `t-esc`, `t-if`)
- Brand: `#0A3D62` navy, `#FF6B35` laranja, `#5A7184` gray, `#EEF2F5` light gray
- Fonte: Inter via `/afr_labquali_layout/static/fonts/inter/Inter-*.woff2`
- CTA "Solicitar Orçamento" → `/contactus`
- Commit via agente `git-commit-push` do dir `/home/afonso/docker/odoo_engenapp` (monorepo, NÃO submodule)
- Upgrade/install via: `docker exec odoo-labquali odoo --db_host db --db_port 5432 --db_user odoo --db_password odoo -d odoo-labquali -u afr_labquali_website --stop-after-init`
- Instalar pela primeira vez: trocar `-u` por `-i` no comando acima

---

### Task 1: Module skeleton + SCSS brand styles

**Files:**
- Create: `addons/afr_labquali_website/__init__.py`
- Create: `addons/afr_labquali_website/__manifest__.py`
- Create: `addons/afr_labquali_website/static/src/scss/labquali_website.scss`

**Interfaces:**
- Produces: módulo instalável; SCSS carregado em `web.assets_frontend`

- [ ] **Step 1: Criar `__init__.py`**

```python
# addons/afr_labquali_website/__init__.py
```

(arquivo vazio — sem modelos Python neste módulo)

- [ ] **Step 2: Criar `__manifest__.py`**

```python
# addons/afr_labquali_website/__manifest__.py
{
    "name": "LabQuali Website",
    "version": "16.0.1.0.0",
    "category": "Website",
    "license": "LGPL-3",
    "author": "AFR Sistemas",
    "summary": "Landing page institucional LabQuali — qualificação e calibração de equipamentos",
    "depends": ["website", "website_form", "afr_labquali_layout"],
    "data": [
        "views/labquali_homepage.xml",
        "views/website_layout_override.xml",
        "data/website_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "afr_labquali_website/static/src/scss/labquali_website.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
```

- [ ] **Step 3: Criar SCSS `labquali_website.scss`**

```scss
// addons/afr_labquali_website/static/src/scss/labquali_website.scss

// ── Font Face ────────────────────────────────────────────────────────
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 400;
    src: url('/afr_labquali_layout/static/fonts/inter/Inter-Regular.woff2') format('woff2');
}
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 500;
    src: url('/afr_labquali_layout/static/fonts/inter/Inter-Medium.woff2') format('woff2');
}
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 700;
    src: url('/afr_labquali_layout/static/fonts/inter/Inter-Bold.woff2') format('woff2');
}
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 800;
    src: url('/afr_labquali_layout/static/fonts/inter/Inter-ExtraBold.woff2') format('woff2');
}

// ── Brand Variables ──────────────────────────────────────────────────
:root {
    --lq-brand:      #0A3D62;
    --lq-brand-2:    #1E6091;
    --lq-accent:     #FF6B35;
    --lq-accent-2:   #D9482A;
    --lq-gray:       #5A7184;
    --lq-gray-light: #EEF2F5;
    --lq-dark:       #071e32;
}

body { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; }

// ── Navbar ────────────────────────────────────────────────────────────
.o_main_nav,
header.o_top_fixed_element .navbar {
    background-color: var(--lq-brand) !important;
    border-bottom: none !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25) !important;

    .navbar-brand,
    .navbar-brand:hover { color: #fff !important; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.03rem; }
    .navbar-brand span { color: var(--lq-accent); }

    .nav-link { color: rgba(255,255,255,0.75) !important; font-size: 0.875rem; font-weight: 500; }
    .nav-link:hover, .nav-link:focus { color: #fff !important; }

    .btn-primary,
    .o_btn_cta,
    a.btn.btn-primary {
        background-color: var(--lq-accent) !important;
        border-color: var(--lq-accent) !important;
        color: #fff !important;
        font-weight: 700;
        border-radius: 6px;
        padding: 8px 20px;
        &:hover {
            background-color: var(--lq-accent-2) !important;
            border-color: var(--lq-accent-2) !important;
        }
    }
}

// ── Section helpers ───────────────────────────────────────────────────
.lq-section-tag {
    font-size: 0.6875rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--lq-accent);
    font-weight: 700;
    margin-bottom: 0.625rem;
    display: block;
}
.lq-section-title {
    font-size: 2.125rem;
    font-weight: 800;
    color: var(--lq-brand);
    letter-spacing: -0.05rem;
    line-height: 1.2;
    span { color: var(--lq-accent); }
}

// ── Hero ──────────────────────────────────────────────────────────────
.lq-hero {
    min-height: 100vh;
    background: linear-gradient(135deg, #071e32 0%, #0A3D62 40%, #0d2f4a 70%, #1a0a00 100%);
    display: flex;
    align-items: center;
    position: relative;
    overflow: hidden;
    padding: 120px 0 100px;

    &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 60% 80% at 80% 50%, rgba(255,107,53,0.12) 0%, transparent 70%);
        pointer-events: none;
    }

    .lq-hero-badge {
        display: inline-block;
        background: rgba(255,107,53,0.18);
        border: 1px solid rgba(255,107,53,0.4);
        color: var(--lq-accent);
        font-size: 0.6875rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-weight: 700;
        padding: 5px 14px;
        border-radius: 20px;
        margin-bottom: 1.25rem;
    }

    h1 {
        font-size: 3rem;
        font-weight: 900;
        line-height: 1.1;
        color: #fff;
        letter-spacing: -0.1rem;
        margin-bottom: 1.125rem;
        span { color: var(--lq-accent); }
        @media (max-width: 768px) { font-size: 2.25rem; }
    }

    .lq-hero-sub {
        font-size: 1.0625rem;
        color: rgba(255,255,255,0.7);
        line-height: 1.6;
        margin-bottom: 2.25rem;
        max-width: 540px;
    }

    .lq-hero-stats {
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        display: flex;
        gap: 2.5rem;
        flex-wrap: wrap;

        .lq-stat-num {
            font-size: 1.75rem;
            font-weight: 900;
            color: var(--lq-accent);
            line-height: 1;
        }
        .lq-stat-label {
            font-size: 0.75rem;
            color: rgba(255,255,255,0.55);
            text-transform: uppercase;
            letter-spacing: 0.0625rem;
            margin-top: 2px;
        }
    }
}

// ── Serviços ──────────────────────────────────────────────────────────
.lq-services {
    padding: 80px 0;
    background: #fff;

    .lq-service-card {
        border: 1px solid #EEF2F5;
        border-radius: 12px;
        padding: 28px 22px;
        height: 100%;
        position: relative;
        overflow: hidden;
        transition: box-shadow 0.2s, transform 0.2s;

        &::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: var(--lq-accent);
        }
        &:hover {
            box-shadow: 0 8px 32px rgba(10,61,98,0.1);
            transform: translateY(-2px);
        }

        .lq-service-icon {
            width: 48px; height: 48px;
            background: var(--lq-gray-light);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.375rem;
            margin-bottom: 1rem;
        }
        h3 { font-size: 0.9375rem; font-weight: 700; color: var(--lq-brand); margin-bottom: 0.5rem; }
        p   { font-size: 0.8125rem; color: var(--lq-gray); line-height: 1.6; margin: 0; }
        .lq-service-tag {
            display: inline-block;
            margin-top: 0.875rem;
            font-size: 0.6875rem;
            font-weight: 700;
            color: var(--lq-accent);
            letter-spacing: 0.0625rem;
            text-transform: uppercase;
        }
    }
}

// ── Diferenciais ──────────────────────────────────────────────────────
.lq-diff {
    padding: 80px 0;
    background: linear-gradient(135deg, #0A3D62 0%, #0d4e7a 100%);

    .lq-section-title { color: #fff; }
    .lq-section-sub   { color: rgba(255,255,255,0.6); }

    .lq-diff-card {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 28px;
        height: 100%;

        .lq-diff-icon {
            width: 52px; height: 52px;
            background: rgba(255,107,53,0.15);
            border: 1px solid rgba(255,107,53,0.3);
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }
        h3 { font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem; }
        p  { font-size: 0.8125rem; color: rgba(255,255,255,0.6); line-height: 1.6; margin: 0; }
    }
}

// ── Equipamentos ──────────────────────────────────────────────────────
.lq-equip {
    padding: 80px 0;
    background: #F4F7FA;

    .lq-equip-item {
        background: #fff;
        border: 1px solid #E0E8F0;
        border-radius: 12px;
        padding: 20px 12px;
        text-align: center;
        display: flex; flex-direction: column; align-items: center;
        gap: 10px;
        transition: box-shadow 0.2s;
        &:hover { box-shadow: 0 4px 16px rgba(10,61,98,0.1); }

        .lq-equip-icon {
            width: 44px; height: 44px;
            background: linear-gradient(135deg, #0A3D62, #1E6091);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.25rem;
            color: #fff;
        }
        span { font-size: 0.71875rem; font-weight: 600; color: var(--lq-brand); line-height: 1.3; }
    }
}

// ── Clientes ──────────────────────────────────────────────────────────
.lq-clients {
    padding: 64px 0;
    background: #fff;

    .lq-client-logo {
        height: 72px;
        background: #F4F7FA;
        border: 1px solid #E0E8F0;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--lq-gray);
        letter-spacing: 0.0625rem;
    }
}

// ── CTA ───────────────────────────────────────────────────────────────
.lq-cta {
    padding: 80px 0;
    background: linear-gradient(120deg, #0A3D62 0%, #FF6B35 130%);
    text-align: center;
    position: relative;
    overflow: hidden;

    &::before {
        content: '';
        position: absolute; inset: 0;
        background: repeating-linear-gradient(
            -55deg, transparent, transparent 60px,
            rgba(255,255,255,0.03) 60px, rgba(255,255,255,0.03) 61px
        );
        pointer-events: none;
    }

    h2 {
        font-size: 2.375rem;
        font-weight: 900;
        color: #fff;
        letter-spacing: -0.0625rem;
        margin-bottom: 0.875rem;
    }
    p { font-size: 1.0625rem; color: rgba(255,255,255,0.8); margin-bottom: 2.25rem; }

    .lq-cta-btn {
        display: inline-block;
        background: #fff;
        color: #0A3D62 !important;
        padding: 16px 40px;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 800;
        text-decoration: none !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        &:hover { background: #EEF2F5; }
    }
}

// ── Footer ────────────────────────────────────────────────────────────
.lq-footer {
    background: #071e32;
    padding: 52px 0 28px;
    color: rgba(255,255,255,0.6);
    font-size: 0.8125rem;

    h4 {
        color: #fff;
        font-size: 0.8125rem;
        font-weight: 700;
        letter-spacing: 0.03125rem;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    ul { list-style: none; padding: 0; margin: 0; }
    ul li { margin-bottom: 0.625rem; }
    a { color: rgba(255,255,255,0.5); text-decoration: none; }
    a:hover { color: #fff; }

    .lq-footer-brand-name {
        font-size: 1.375rem;
        font-weight: 800;
        color: #fff;
        letter-spacing: -0.03125rem;
        margin-bottom: 0.75rem;
        display: block;
        span { color: var(--lq-accent); }
    }

    .lq-footer-divider {
        border-top: 1px solid rgba(255,255,255,0.08);
        padding-top: 1.375rem;
        margin-top: 2.5rem;
        font-size: 0.75rem;
        color: rgba(255,255,255,0.4);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
}
```

- [ ] **Step 4: Criar diretórios necessários**

```bash
mkdir -p /home/afonso/docker/odoo_engenapp/addons/afr_labquali_website/static/src/scss
mkdir -p /home/afonso/docker/odoo_engenapp/addons/afr_labquali_website/views
mkdir -p /home/afonso/docker/odoo_engenapp/addons/afr_labquali_website/data
```

---

### Task 2: Homepage QWeb template

**Files:**
- Create: `addons/afr_labquali_website/views/labquali_homepage.xml`

**Interfaces:**
- Consumes: SCSS classes de Task 1 (`lq-hero`, `lq-services`, etc.)
- Produces: template `afr_labquali_website.labquali_homepage` referenciável em `website.page`

- [ ] **Step 1: Criar `views/labquali_homepage.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="labquali_homepage" name="LabQuali Homepage">
        <t t-call="website.layout">
            <t t-set="pageName" t-value="'labquali_homepage'"/>
            <t t-set="no_breadcrumbs" t-value="True"/>

            <!-- ── HERO ──────────────────────────────────────────── -->
            <section class="lq-hero">
                <div class="container position-relative" style="z-index:1;">
                    <div class="row">
                        <div class="col-lg-7">
                            <span class="lq-hero-badge">✓ ISO 17025 · RDC 665/2022 · NR13</span>
                            <h1>Qualificação e Calibração de<br/><span>Equipamentos</span><br/>de Esterilização</h1>
                            <p class="lq-hero-sub">Laudos técnicos com rastreabilidade metrológica para autoclaves, estufas, câmaras de estabilidade e inspeções NR13.</p>
                            <div class="d-flex gap-3 flex-wrap">
                                <a href="/contactus"
                                   style="background:#FF6B35;color:#fff;font-weight:700;border-radius:8px;padding:14px 30px;box-shadow:0 8px 24px rgba(255,107,53,0.4);text-decoration:none;font-size:1rem;">
                                    Solicitar Orçamento →
                                </a>
                                <a href="#lq-services"
                                   style="color:rgba(255,255,255,0.8);border:1px solid rgba(255,255,255,0.25);border-radius:8px;padding:14px 28px;text-decoration:none;font-size:1rem;">
                                    Ver Serviços
                                </a>
                            </div>
                            <div class="lq-hero-stats">
                                <div>
                                    <div class="lq-stat-num">+500</div>
                                    <div class="lq-stat-label">Equipamentos/ano</div>
                                </div>
                                <div>
                                    <div class="lq-stat-num">15+</div>
                                    <div class="lq-stat-label">Anos de experiência</div>
                                </div>
                                <div>
                                    <div class="lq-stat-num">100%</div>
                                    <div class="lq-stat-label">Laudos rastreáveis</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- ── SERVIÇOS ──────────────────────────────────────── -->
            <section class="lq-services" id="lq-services">
                <div class="container">
                    <div class="text-center mb-5">
                        <span class="lq-section-tag">O que fazemos</span>
                        <h2 class="lq-section-title">Nossos <span>Serviços</span></h2>
                        <p class="text-muted mt-2" style="font-size:1rem;">Soluções completas de qualificação, calibração e inspeção para equipamentos críticos de saúde.</p>
                    </div>
                    <div class="row g-4">
                        <div class="col-lg-3 col-md-6">
                            <div class="lq-service-card">
                                <div class="lq-service-icon">⚗️</div>
                                <h3>Qualificação IQ/OQ/PQ</h3>
                                <p>Qualificação de instalação, operacional e de desempenho conforme RDC 665/2022 e boas práticas de fabricação.</p>
                                <span class="lq-service-tag">Autoclave · Estufa · Câmara</span>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6">
                            <div class="lq-service-card">
                                <div class="lq-service-icon">🌡️</div>
                                <h3>Calibração de Sensores</h3>
                                <p>Calibração de termopares, termômetros, manômetros e sensores de pressão com rastreabilidade metrológica RBC/Inmetro.</p>
                                <span class="lq-service-tag">Temperatura · Pressão · Umidade</span>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6">
                            <div class="lq-service-card">
                                <div class="lq-service-icon">🛡️</div>
                                <h3>Inspeção NR13</h3>
                                <p>Inspeção de vasos de pressão, caldeiras e autoclaves conforme NR13 do MTE. Relatórios para fiscalização.</p>
                                <span class="lq-service-tag">Vasos de Pressão · Caldeiras</span>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-6">
                            <div class="lq-service-card">
                                <div class="lq-service-icon">📋</div>
                                <h3>Mapeamento Térmico</h3>
                                <p>Mapeamento de temperatura em câmaras, estufas e geladeiras com malha de pontos e análise estatística completa.</p>
                                <span class="lq-service-tag">Câmaras · Geladeiras · Incubadoras</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- ── DIFERENCIAIS ──────────────────────────────────── -->
            <section class="lq-diff" id="lq-diff">
                <div class="container">
                    <div class="text-center mb-5">
                        <span class="lq-section-tag">Por que a LabQuali</span>
                        <h2 class="lq-section-title">Confiança técnica em <span>cada laudo</span></h2>
                        <p class="lq-section-sub mt-2" style="font-size:1rem;">Combinamos expertise metrológica, sistemas digitais e atendimento ágil para garantir sua conformidade regulatória.</p>
                    </div>
                    <div class="row g-4">
                        <div class="col-lg-4 col-md-6">
                            <div class="lq-diff-card">
                                <div class="lq-diff-icon">📜</div>
                                <h3>Rastreabilidade Metrológica</h3>
                                <p>Padrões calibrados em laboratórios acreditados pela RBC. Cadeia ininterrupta até o BIPM para temperatura e pressão.</p>
                            </div>
                        </div>
                        <div class="col-lg-4 col-md-6">
                            <div class="lq-diff-card">
                                <div class="lq-diff-icon">⚡</div>
                                <h3>Laudos em até 5 dias úteis</h3>
                                <p>Sistema digital de geração de relatórios garante entrega ágil com assinatura eletrônica e acesso imediato.</p>
                            </div>
                        </div>
                        <div class="col-lg-4 col-md-6">
                            <div class="lq-diff-card">
                                <div class="lq-diff-icon">🔬</div>
                                <h3>Equipe Especializada</h3>
                                <p>Engenheiros e técnicos com formação em metrologia, farmácia industrial e engenharia hospitalar.</p>
                            </div>
                        </div>
                        <div class="col-lg-4 col-md-6">
                            <div class="lq-diff-card">
                                <div class="lq-diff-icon">📱</div>
                                <h3>Portal do Cliente</h3>
                                <p>Acesse todos os seus laudos, histórico de qualificações e certificados a qualquer momento, de qualquer dispositivo.</p>
                            </div>
                        </div>
                        <div class="col-lg-4 col-md-6">
                            <div class="lq-diff-card">
                                <div class="lq-diff-icon">🗺️</div>
                                <h3>Atendimento Nacional</h3>
                                <p>Presença em todo o Brasil. Equipes locais nas principais capitais para atendimento presencial ágil.</p>
                            </div>
                        </div>
                        <div class="col-lg-4 col-md-6">
                            <div class="lq-diff-card">
                                <div class="lq-diff-icon">✅</div>
                                <h3>Conformidade Regulatória</h3>
                                <p>Laudos alinhados às exigências da ANVISA (RDC 665/2022), MTE (NR13) e normas ABNT aplicáveis.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- ── EQUIPAMENTOS ──────────────────────────────────── -->
            <section class="lq-equip" id="lq-equip">
                <div class="container">
                    <div class="text-center mb-5">
                        <span class="lq-section-tag" style="color:#0A3D62;">Equipamentos Atendidos</span>
                        <h2 class="lq-section-title">Expertise em equipamentos <span>críticos</span></h2>
                        <p class="text-muted mt-2" style="font-size:1rem;">Trabalhamos com todo o parque de equipamentos de esterilização e controle de temperatura de hospitais, farmácias e indústrias.</p>
                    </div>
                    <div class="row g-3">
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🔩</div><span>Autoclaves a Vapor</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🔥</div><span>Estufas de Esterilização</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🌡️</div><span>Câmaras de Estabilidade</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">❄️</div><span>Câmaras Frias</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🧫</div><span>Incubadoras</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">💊</div><span>Geladeiras Farmacêuticas</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">⚙️</div><span>Vasos de Pressão</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🏭</div><span>Caldeiras</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🧊</div><span>Liofilizadores</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">♨️</div><span>Túneis de Calor</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">🔊</div><span>Lavadoras Ultrassônicas</span></div></div>
                        <div class="col-lg-2 col-md-3 col-6"><div class="lq-equip-item"><div class="lq-equip-icon">📡</div><span>Termômetros e Sondas</span></div></div>
                    </div>
                </div>
            </section>

            <!-- ── CLIENTES ──────────────────────────────────────── -->
            <section class="lq-clients" id="lq-clients">
                <div class="container">
                    <div class="text-center mb-4">
                        <span class="lq-section-tag">Quem confia na LabQuali</span>
                        <h2 class="lq-section-title">Clientes e <span>Parceiros</span></h2>
                        <p class="text-muted mt-2" style="font-size:1rem;">Hospitais, farmácias, indústrias e laboratórios em todo o Brasil.</p>
                    </div>
                    <div class="row g-3">
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">HOSPITAL A</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">FARMÁCIA B</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">LAB C</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">INDÚSTRIA D</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">HOSPITAL E</div></div>
                    </div>
                    <div class="row g-3 mt-1">
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">CLÍNICA F</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">GRUPO G</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">UNIMED H</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">PHARMA I</div></div>
                        <div class="col-lg col-md-4 col-6"><div class="lq-client-logo">SAÚDE J</div></div>
                    </div>
                </div>
            </section>

            <!-- ── CTA FINAL ─────────────────────────────────────── -->
            <section class="lq-cta" id="lq-contact">
                <div class="container position-relative" style="z-index:1;">
                    <h2>Pronto para estar em conformidade?</h2>
                    <p class="mx-auto" style="max-width:540px;">Solicite um orçamento sem compromisso. Nossa equipe técnica entra em contato em até 24 horas úteis para entender suas necessidades.</p>
                    <a href="/contactus" class="lq-cta-btn">Solicitar Orçamento Gratuito →</a>
                </div>
            </section>

        </t>
    </template>
</odoo>
```

---

### Task 3: Footer override + website.page record

**Files:**
- Create: `addons/afr_labquali_website/views/website_layout_override.xml`
- Create: `addons/afr_labquali_website/data/website_data.xml`

**Interfaces:**
- Consumes: template `afr_labquali_website.labquali_homepage` (Task 2); SCSS `.lq-footer` (Task 1)
- Produces: footer customizado em todas as páginas; homepage em URL `/`

- [ ] **Step 1: Criar `views/website_layout_override.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="labquali_footer" inherit_id="website.footer_custom" name="LabQuali Footer">
        <xpath expr="." position="replace">
            <div id="footer" class="lq-footer oe_structure oe_structure_solo">
                <div class="container">
                    <div class="row">
                        <div class="col-lg-4 col-md-6 mb-4 mb-lg-0">
                            <span class="lq-footer-brand-name">Lab<span>Quali</span></span>
                            <p>Qualificação e calibração de equipamentos críticos com rastreabilidade metrológica e conformidade regulatória.</p>
                        </div>
                        <div class="col-lg-2 col-md-3 col-6 mb-4 mb-lg-0">
                            <h4>Serviços</h4>
                            <ul>
                                <li><a href="/contactus">Qualificação IQ/OQ/PQ</a></li>
                                <li><a href="/contactus">Calibração de Sensores</a></li>
                                <li><a href="/contactus">Inspeção NR13</a></li>
                                <li><a href="/contactus">Mapeamento Térmico</a></li>
                            </ul>
                        </div>
                        <div class="col-lg-2 col-md-3 col-6 mb-4 mb-lg-0">
                            <h4>Empresa</h4>
                            <ul>
                                <li><a href="/">Sobre a LabQuali</a></li>
                                <li><a href="/contactus">Certificações</a></li>
                                <li><a href="/web#action=login">Portal do Cliente</a></li>
                                <li><a href="/contactus">Contato</a></li>
                            </ul>
                        </div>
                        <div class="col-lg-4 col-md-6 mb-4 mb-lg-0">
                            <h4>Contato</h4>
                            <ul>
                                <t t-if="res_company.phone">
                                    <li>📞 <t t-esc="res_company.phone"/></li>
                                </t>
                                <t t-if="res_company.email">
                                    <li>✉ <a t-attf-href="mailto:#{res_company.email}"><t t-esc="res_company.email"/></a></li>
                                </t>
                                <t t-if="res_company.city">
                                    <li>📍 <t t-esc="res_company.city"/><t t-if="res_company.state_id">, <t t-esc="res_company.state_id.name"/></t></li>
                                </t>
                                <li>Atendimento nacional</li>
                            </ul>
                        </div>
                    </div>
                    <div class="lq-footer-divider">
                        <span>© <t t-esc="datetime.date.today().year"/> <t t-esc="res_company.name"/>. Todos os direitos reservados.</span>
                        <div>
                            <a href="/privacy">Política de Privacidade</a>
                            <a href="/terms" class="ms-3">Termos de Uso</a>
                        </div>
                    </div>
                </div>
            </div>
        </xpath>
    </template>
</odoo>
```

- [ ] **Step 2: Criar `data/website_data.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="labquali_home_page" model="website.page">
        <field name="name">LabQuali — Qualificação e Calibração de Equipamentos</field>
        <field name="url">/</field>
        <field name="view_id" ref="labquali_homepage"/>
        <field name="is_published">True</field>
        <field name="website_indexed">True</field>
    </record>
</odoo>
```

- [ ] **Step 3: Instalar módulo**

```bash
docker exec odoo-labquali odoo --db_host db --db_port 5432 --db_user odoo --db_password odoo -d odoo-labquali -i afr_labquali_website --stop-after-init
```

Expected output: sem erros Python, sem `ParseError`, sem `UserError`. Aceita warnings de tradução.

Se já instalado (re-instalação): trocar `-i` por `-u`.

- [ ] **Step 4: Commit**

Commitar do monorepo (NÃO submodule):

```bash
cd /home/afonso/docker/odoo_engenapp
git add addons/afr_labquali_website/
git commit -m "feat: add afr_labquali_website landing page institucional

Módulo novo com homepage completa: hero/serviços/diferenciais/
equipamentos/clientes/CTA/footer. Estilo impactante navy+laranja,
tipografia Inter, SCSS brand-first."
git push
```

---

### Task 4: Browser validation + ajustes

**Files:**
- Modify: arquivos de Task 1-3 conforme necessário para corrigir rendering issues

**Interfaces:**
- Consumes: site em `http://localhost:8083`

- [ ] **Step 1: Navegar para homepage**

```bash
agent-browser open http://localhost:8083
agent-browser snapshot
```

Verificar: navbar navy visível, hero dark com headline.

- [ ] **Step 2: Screenshot das seções**

```bash
agent-browser screenshot --full-page
```

Verificar todas as 7 seções: hero, serviços (4 cards), diferenciais (6 cards navy), equipamentos (12 items), clientes (grid), CTA (gradiente), footer.

- [ ] **Step 3: Verificar CTA link**

```bash
agent-browser click "Solicitar Orçamento"
agent-browser snapshot
```

Expected: navega para `/contactus` com formulário de contato Odoo.

- [ ] **Step 4: Corrigir rendering issues (se houver)**

Problemas comuns e correções:

**Navbar não ficou navy:** Adicionar `!important` mais específico no SCSS:
```scss
header nav.navbar { background-color: #0A3D62 !important; }
```

**Hero não ocupa full height:** Verificar se Odoo injeta padding top para navbar fixed. Ajustar `padding-top` do `.lq-hero`:
```scss
.lq-hero { padding-top: 120px; }  // altura navbar ~70px + margin
```

**Footer não aparece:** Verificar se `website.footer_custom` é o template correto em Odoo 16. Alternativa:
```xml
<template id="labquali_footer" inherit_id="website.layout" name="LabQuali Footer">
    <xpath expr="//div[@id='footer']" position="replace">
        <!-- conteúdo do footer -->
    </xpath>
</template>
```

**website.page conflito com homepage existente:** Se erro de unique constraint, apagar a página existente no Odoo admin antes de instalar, ou usar `noupdate="1"` no record.

- [ ] **Step 5: Upgrade após fixes**

```bash
docker exec odoo-labquali odoo --db_host db --db_port 5432 --db_user odoo --db_password odoo -d odoo-labquali -u afr_labquali_website --stop-after-init
```

- [ ] **Step 6: Commit final com fixes**

```bash
cd /home/afonso/docker/odoo_engenapp
git add addons/afr_labquali_website/
git commit -m "fix: afr_labquali_website rendering adjustments"
git push
```
