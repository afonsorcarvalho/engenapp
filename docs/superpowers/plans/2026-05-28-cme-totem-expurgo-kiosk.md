# Piloto Expurgo kiosk (afr_cme_rastreabilidade) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesenhar a estação **Expurgo** do cliente OWL `cme_totem` em modo kiosk (full-bleed, paleta teal cirúrgico, layout split landscape, atalhos, modais, idle, indicador de conexão). Mantém o back-office actual intacto. Outras estações ficam pra fase posterior.

**Architecture:** Approach B híbrido — mesma `ir.actions.client` (tag `cme_totem`) e mesmo `CmeTotem` OWL component. Flag `isKiosk` derivada de (a) `context.cme_totem_kiosk`, (b) query param `?kiosk=1`, (c) ICP `cme.totem.kiosk_default`. Quando `true`, root recebe classe `cme_totem--kiosk` que aplica `position:fixed; inset:0; z-index:1030` cobrindo `.o_main_navbar`, paleta teal via CSS vars, sub-templates de kiosk (Topbar/Stepper/ScanHero/MaterialsList/ActionFooter/ConfirmModal/IdleOverlay). Body recebe classe auxiliar `cme-totem-kiosk-active` para regras CSS de apoio. Comportamento back-office fica idêntico quando flag está `false`.

**Tech Stack:** Odoo 16.0 · OWL (Bootstrap 5 backend) · Python 3.9 · QWeb templates · SCSS · Web Audio API (sem assets externos).

**Spec:** `docs/superpowers/specs/2026-05-28-cme-totem-expurgo-kiosk-design.md`

**Regra do projeto:** commits NÃO são feitos no fim de cada task automaticamente. Cada task termina com "**Mostra ao user no Odoo running e aguarda OK explícito**" antes do passo "**Commit**". Esta regra existe a pedido do user (memória `feedback_commit_after_test.md`).

**Restart do Odoo:** o container ouve em `8083` (host). Mudanças em SCSS/JS/XML precisam de `Update Module` (Apps → afr_cme_rastreabilidade → Upgrade) no Odoo OU `docker compose restart web` + hard refresh (`Ctrl+Shift+R`). Para verificar com `odoo-mcp`: `mcp__plugin_odoo-mcp_odoo__odoo_modules_list` antes/depois.

---

## File Structure

| Path | Responsibility |
|---|---|
| `addons/afr_cme/afr_cme_rastreabilidade/data/cme_totem_kiosk_icps.xml` | **NOVO** · 3 `ir.config_parameter` records com defaults |
| `addons/afr_cme/afr_cme_rastreabilidade/models/cme_dirty_receipt.py` | **MOD** · estende `totem_get_app_config` (linha 288) para devolver `kiosk_default`, `sound_enabled`, `idle_timeout_min` |
| `addons/afr_cme/afr_cme_rastreabilidade/__manifest__.py` | **MOD** · adiciona o XML novo a `data`, lista `tests/__init__.py` |
| `addons/afr_cme/afr_cme_rastreabilidade/tests/__init__.py` | **NOVO** · `from . import test_totem_kiosk_config` |
| `addons/afr_cme/afr_cme_rastreabilidade/tests/test_totem_kiosk_config.py` | **NOVO** · smoke test dos 3 ICPs + payload do `totem_get_app_config` |
| `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss` | **MOD** · adiciona bloco `.cme_totem--kiosk { … }` com vars, full-bleed, paleta, tipografia, drawer, flash, modal |
| `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml` | **MOD** · adiciona `t-name` sub-templates (KioskTopbar, KioskStepper, ScanHero, MaterialsList, ActionFooter, ConfirmModal, IdleOverlay, SetupPanelPill). Mantém estrutura existente para back-office. |
| `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js` | **MOD** · adiciona `isKiosk` computed, useExternalListener keyboard, helper Web Audio, useState dos modais kiosk, refocus scan input, idle timer, ping conexão, body class side-effect |
| `docs/cme_totem_kiosk_manual_check.md` | **NOVO** · checklist manual para validar piloto em monitor real |

Tudo no submodule `addons/afr_cme/` exceto `docs/`. Commits do submodule rodam **de dentro de `/home/afonso/docker/odoo_engenapp/addons/afr_cme/`**, depois bump do pointer no monorepo. Ver `feedback_submodule_workflow` na memória.

---

## Task 1: ICPs + smoke test (backend mínimo)

**Files:**
- Create: `addons/afr_cme/afr_cme_rastreabilidade/data/cme_totem_kiosk_icps.xml`
- Create: `addons/afr_cme/afr_cme_rastreabilidade/tests/__init__.py`
- Create: `addons/afr_cme/afr_cme_rastreabilidade/tests/test_totem_kiosk_config.py`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/models/cme_dirty_receipt.py` (método `totem_get_app_config`, linha 288)
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/__manifest__.py` (adicionar XML a `data`)

- [ ] **Step 1: Cria o XML dos ICPs**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="cme_totem_kiosk_default" model="ir.config_parameter">
        <field name="key">cme.totem.kiosk_default</field>
        <field name="value">False</field>
    </record>
    <record id="cme_totem_sound_enabled" model="ir.config_parameter">
        <field name="key">cme.totem.sound_enabled</field>
        <field name="value">True</field>
    </record>
    <record id="cme_totem_idle_timeout_min" model="ir.config_parameter">
        <field name="key">cme.totem.idle_timeout_min</field>
        <field name="value">5</field>
    </record>
</odoo>
```

- [ ] **Step 2: Registra o XML no manifest**

Edita `__manifest__.py`, adiciona logo após `data/cme_cron_data.xml`:

```python
        "data/cme_totem_kiosk_icps.xml",
```

- [ ] **Step 3: Cria pasta `tests/` e `__init__.py`**

```bash
mkdir -p addons/afr_cme/afr_cme_rastreabilidade/tests
```

Conteúdo de `tests/__init__.py`:

```python
# -*- coding: utf-8 -*-
from . import test_totem_kiosk_config
```

- [ ] **Step 4: Escreve smoke test (falha primeiro)**

Conteúdo de `tests/test_totem_kiosk_config.py`:

```python
# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "afr_cme")
class TestTotemKioskConfig(TransactionCase):
    def test_icps_exist_with_defaults(self):
        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(icp.get_param("cme.totem.kiosk_default"), "False")
        self.assertEqual(icp.get_param("cme.totem.sound_enabled"), "True")
        self.assertEqual(icp.get_param("cme.totem.idle_timeout_min"), "5")

    def test_totem_get_app_config_exposes_kiosk_fields(self):
        cfg = self.env["cme.dirty.receipt"].sudo().totem_get_app_config()
        self.assertIn("kiosk_default", cfg)
        self.assertIn("sound_enabled", cfg)
        self.assertIn("idle_timeout_min", cfg)
        self.assertIs(cfg["kiosk_default"], False)
        self.assertIs(cfg["sound_enabled"], True)
        self.assertEqual(cfg["idle_timeout_min"], 5)
```

- [ ] **Step 5: Estende `totem_get_app_config`**

Em `models/cme_dirty_receipt.py`, dentro do método `totem_get_app_config` (linha 288), antes do `return` final, ler os 3 ICPs e adicionar ao dict de retorno:

```python
        ICP = self.env["ir.config_parameter"].sudo()

        def _bool(v, default=False):
            return str(v).strip().lower() in ("1", "true", "t", "yes", "y") if v else default

        def _int(v, default=0):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default

        kiosk_default = _bool(ICP.get_param("cme.totem.kiosk_default"), False)
        sound_enabled = _bool(ICP.get_param("cme.totem.sound_enabled"), True)
        idle_timeout_min = _int(ICP.get_param("cme.totem.idle_timeout_min"), 5)
```

Depois inclui no dict final retornado:

```python
            "kiosk_default": kiosk_default,
            "sound_enabled": sound_enabled,
            "idle_timeout_min": idle_timeout_min,
```

- [ ] **Step 6: Aplica módulo no DB de dev e roda teste**

```bash
docker exec odoo-engenapp odoo -d odoo-steriliza -u afr_cme_rastreabilidade --test-tags=afr_cme --stop-after-init
```

Esperado: 2 testes passam. Se falhar com "module not in known DB", instalar com `-i afr_cme_rastreabilidade` em DB fresh; ou aplicar `Update` via UI.

- [ ] **Step 7: Verifica via odoo-mcp**

```
mcp__plugin_odoo-mcp_odoo__odoo_execute_kw model="cme.dirty.receipt" method="totem_get_app_config" args=[]
```

Esperado: payload inclui as 3 chaves novas.

- [ ] **Step 8: Mostra ao user e aguarda OK explícito**

User abre o totem actual (back-office) e confirma que não houve regressão (config carrega, sem erro no console).

- [ ] **Step 9: Commit (apenas após OK do user)**

```bash
cd addons/afr_cme
git add afr_cme_rastreabilidade/data/cme_totem_kiosk_icps.xml \
        afr_cme_rastreabilidade/tests/__init__.py \
        afr_cme_rastreabilidade/tests/test_totem_kiosk_config.py \
        afr_cme_rastreabilidade/models/cme_dirty_receipt.py \
        afr_cme_rastreabilidade/__manifest__.py
git commit -m "feat(afr_cme_rastreabilidade): 3 ICPs kiosk + smoke tests + expose em totem_get_app_config"
git push origin main
cd /home/afonso/docker/odoo_engenapp
git add addons/afr_cme
git commit -m "chore: bump afr_cme submodule (kiosk ICPs base)"
git push
```

Commit pelo agent `git-commit-push` (memória `feedback_commit_via_agent`).

---

## Task 2: Detecção kiosk + classe root + body side-effect

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`

- [ ] **Step 1: Adiciona getter `isKiosk` no `CmeTotem`**

Em `cme_totem.js`, dentro da classe (após `setup()`), adiciona:

```javascript
    /**
     * Modo kiosk activado por qualquer de:
     * 1) context.cme_totem_kiosk: true (passado pela action no menu)
     * 2) query param `?kiosk=1` na URL
     * 3) ICP `cme.totem.kiosk_default` (lido em totem_get_app_config -> state.appConfig.kiosk_default)
     */
    get isKiosk() {
        const ctx = this.props.action?.context || {};
        if (ctx.cme_totem_kiosk === true) {
            return true;
        }
        try {
            const search = new URLSearchParams(window.location.search);
            const qp = search.get("kiosk");
            if (qp === "1" || qp === "true") {
                return true;
            }
        } catch (e) {
            // ignore
        }
        return Boolean(this.state.appConfig?.kiosk_default);
    }
```

- [ ] **Step 2: Body class side-effect (mount/unmount)**

Em `setup()`, no fim, adiciona side-effect que aplica/remove a classe no `document.body`:

```javascript
        // body class auxiliar para regras CSS apoio (regras dentro de .cme_totem--kiosk já cobrem o root)
        const applyBodyClass = () => {
            if (this.isKiosk) {
                document.body.classList.add("cme-totem-kiosk-active");
            } else {
                document.body.classList.remove("cme-totem-kiosk-active");
            }
        };
        owl.onMounted(applyBodyClass);
        owl.onPatched(applyBodyClass);
        owl.onWillUnmount(() => document.body.classList.remove("cme-totem-kiosk-active"));
```

Garante que `owl` está importado no topo do arquivo. Se já existir `import { Component, useState, onMounted } from "@odoo/owl";`, expande para também importar `onPatched, onWillUnmount`.

- [ ] **Step 3: Aplica classe no template root**

Em `cme_totem.xml`, no `<div class="o_action cme_totem cme_totem--touch h-100 d-flex flex-column overflow-hidden">` (linha 8), adiciona binding:

```xml
<div t-attf-class="o_action cme_totem cme_totem--touch h-100 d-flex flex-column overflow-hidden {{ isKiosk ? 'cme_totem--kiosk' : '' }}">
```

- [ ] **Step 4: SCSS base do kiosk root (full-bleed)**

Em `cme_totem.scss`, no final do arquivo, adiciona bloco kiosk com vars + full-bleed:

```scss
/* ============================================================
 * Modo kiosk — activado quando o componente recebe a classe
 * `.cme_totem--kiosk`. Cobre `.o_main_navbar` via empilhamento
 * `position: fixed + z-index`, sem hacks de :has().
 * ============================================================ */

.cme_totem--kiosk {
    --kiosk-primary:    #134e4a;
    --kiosk-primary-fg: #ffffff;
    --kiosk-accent:     #0f766e;
    --kiosk-hero-bg:    #f0fdfa;
    --kiosk-hero-bd:    #14b8a6;
    --kiosk-hero-fg:    #134e4a;
    --kiosk-ok-bg:      #ecfdf5;
    --kiosk-ok-bd:      #34d399;
    --kiosk-ok-fg:      #065f46;
    --kiosk-err-bg:     #fef2f2;
    --kiosk-err-bd:     #fca5a5;
    --kiosk-err-fg:     #991b1b;
    --kiosk-surface:    #ffffff;
    --kiosk-surface-2:  #f8fafc;
    --kiosk-border:     #cbd5e1;

    /* estados RDC 15 */
    --rdc-sujo:     #92400e;
    --rdc-processo: #d97706;
    --rdc-critico:  #dc2626;
    --rdc-seguro:   #0f766e;
    --rdc-usado:    #475569;

    /* tipografia */
    --kiosk-fs-base: 1.125rem;   /* 18px → 20px em monitor 1080p */
    --kiosk-fs-hero: 1.75rem;
    --kiosk-fs-num:  1.5rem;

    /* Full-bleed: sobrepõe topbar (`.o_main_navbar` tem z-index ~1030). */
    position: fixed !important;
    inset: 0 !important;
    z-index: 1031 !important;
    background: var(--kiosk-surface);
    max-width: none;
    margin: 0;
    padding: 0;
    font-size: var(--kiosk-fs-base);
    overflow: hidden;
}

/* Auxiliar no body — útil se quisermos escurecer ou esconder algum global. */
body.cme-totem-kiosk-active {
    overflow: hidden;
}
```

- [ ] **Step 5: Restart Odoo + valida visual**

```bash
docker compose -f /home/afonso/docker/odoo_engenapp/docker-compose.yml restart web
```

Abre Odoo (host:8083) → menu CME → totem com `?kiosk=1` na URL. Esperado: tela ocupa viewport inteira, topbar Odoo escondida.

- [ ] **Step 6: Mostra ao user e aguarda OK explícito**

Confirma: kiosk ativa via `?kiosk=1`, desativa sem query param.

- [ ] **Step 7: Commit (apenas após OK)**

Submodule + monorepo bump (igual Task 1). Mensagem:

```
feat(afr_cme_rastreabilidade): kiosk flag + root class + full-bleed CSS base
```

---

## Task 3: KioskTopbar + KioskStepper

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`

- [ ] **Step 1: Adiciona getter `kioskStepperState` no JS**

```javascript
    /**
     * Estado do stepper em kiosk:
     *   1. Setup    — sem sessionId
     *   2. Scan     — sessionId presente, possivelmente linhas
     *   3. Concluir — sempre disponível assim que houver ≥ 1 linha
     */
    get kioskStepperState() {
        const hasSession = Boolean(this.state.sessionId);
        const hasLines = Boolean(this.state.summary?.lines?.length);
        return {
            setup: hasSession ? "done" : "active",
            scan: !hasSession ? "pending" : (hasLines ? "active" : "active"),
            concluir: hasLines ? "active" : "pending",
        };
    }
```

- [ ] **Step 2: Adiciona getter `kioskClockText` (relógio)**

```javascript
    /**
     * Texto do relógio mostrado no topbar.
     * O setInterval que actualiza fica em Task 10 (idle/ping).
     * Aqui retornamos um valor inicial — `state.clockText` é actualizado
     * por um timer instalado em Task 10.
     */
    get kioskClockText() {
        return this.state.clockText || this._formatClock(new Date());
    }

    _formatClock(d) {
        const hh = String(d.getHours()).padStart(2, "0");
        const mm = String(d.getMinutes()).padStart(2, "0");
        return `${hh}:${mm}`;
    }
```

E em `state` inicial (no `useState`), adiciona `clockText: ""` (não causa render extra; só placeholder).

- [ ] **Step 3: Adiciona getter `setupPillText`**

```javascript
    /**
     * Resumo do setup quando a sessão já foi criada — mostrado no topbar como pill.
     * Ex.: "UTI 3º · Vapor · próprio".
     */
    get setupPillText() {
        if (!this.state.summary) return "";
        const parts = [];
        const dept = this.state.depts?.find((d) => String(d.id) === String(this.state.deptId));
        if (dept) parts.push(dept.name);
        if (this.state.summary.sterilization_method) parts.push(this.state.summary.sterilization_method);
        if (this.state.summary.material_owner_name) parts.push(this.state.summary.material_owner_name);
        return parts.join(" · ");
    }
```

- [ ] **Step 4: Sub-template `cme_totem.KioskTopbar`**

Em `cme_totem.xml`, no topo (depois do `<templates>` abrir), adiciona:

```xml
    <t t-name="cme_totem.KioskTopbar" owl="1">
        <div class="cme_totem-kiosk-topbar d-flex align-items-center justify-content-between flex-wrap gap-2 px-3 py-2">
            <div class="d-flex align-items-center gap-3 flex-wrap">
                <span class="cme_totem-kiosk-station">
                    <span class="cme_totem-kiosk-station-icon">🧼</span>
                    <span class="cme_totem-kiosk-station-name" t-esc="stationLabel()"/>
                </span>
                <span class="cme_totem-kiosk-pill" t-if="state.summary and state.summary.process_lot_name">
                    <t t-esc="state.summary.process_lot_name"/>
                </span>
                <span class="cme_totem-kiosk-setup-pill" t-if="setupPillText">
                    <t t-esc="setupPillText"/>
                </span>
            </div>
            <div class="d-flex align-items-center gap-3">
                <span class="cme_totem-kiosk-clock" t-esc="kioskClockText"/>
                <span t-attf-class="cme_totem-kiosk-conn cme_totem-kiosk-conn--{{ state.connOk ? 'ok' : 'down' }}"
                      t-attf-title="{{ state.connOk ? 'Conectado a Odoo' : 'Sem conexão Odoo' }}">●</span>
            </div>
        </div>
    </t>
```

- [ ] **Step 5: Sub-template `cme_totem.KioskStepper`**

Logo a seguir ao KioskTopbar no arquivo XML:

```xml
    <t t-name="cme_totem.KioskStepper" owl="1">
        <div class="cme_totem-kiosk-stepper px-3 pb-2 d-flex gap-2">
            <div t-attf-class="cme_totem-kiosk-step cme_totem-kiosk-step--{{ kioskStepperState.setup }}">
                <span class="cme_totem-kiosk-step-num">1</span> Setup
            </div>
            <div t-attf-class="cme_totem-kiosk-step cme_totem-kiosk-step--{{ kioskStepperState.scan }}">
                <span class="cme_totem-kiosk-step-num">2</span> Scan + materiais
            </div>
            <div t-attf-class="cme_totem-kiosk-step cme_totem-kiosk-step--{{ kioskStepperState.concluir }}">
                <span class="cme_totem-kiosk-step-num">3</span> Concluir
            </div>
        </div>
    </t>
```

- [ ] **Step 6: Renderiza topbar + stepper no root (apenas em kiosk e apenas na expurgo)**

No template `cme_totem.CmeTotem`, logo após o root `<div ... cme_totem--kiosk>` abrir, antes da `.cme_totem-scroll`, adiciona:

```xml
        <t t-if="isKiosk and state.station === 'expurgo'">
            <t t-call="cme_totem.KioskTopbar"/>
            <t t-call="cme_totem.KioskStepper"/>
        </t>
```

(Esconder em outras estações no piloto — fora do escopo conforme spec.)

- [ ] **Step 7: SCSS dos novos componentes**

Em `cme_totem.scss`, dentro do bloco `.cme_totem--kiosk { ... }` (ou logo após), adiciona:

```scss
.cme_totem--kiosk .cme_totem-kiosk-topbar {
    background: var(--kiosk-primary);
    color: var(--kiosk-primary-fg);
    font-weight: 600;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 56px;
}

.cme_totem--kiosk .cme_totem-kiosk-station {
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.cme_totem--kiosk .cme_totem-kiosk-pill,
.cme_totem--kiosk .cme_totem-kiosk-setup-pill {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}

.cme_totem--kiosk .cme_totem-kiosk-setup-pill {
    background: rgba(255, 255, 255, 0.18);
}

.cme_totem--kiosk .cme_totem-kiosk-clock {
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    font-size: 1.1rem;
}

.cme_totem--kiosk .cme_totem-kiosk-conn {
    font-size: 1.5rem;
    line-height: 1;
}
.cme_totem--kiosk .cme_totem-kiosk-conn--ok   { color: #34d399; }
.cme_totem--kiosk .cme_totem-kiosk-conn--down { color: #fca5a5; }

.cme_totem--kiosk .cme_totem-kiosk-stepper {
    background: var(--kiosk-primary);
    padding-bottom: 0.5rem;
}

.cme_totem--kiosk .cme_totem-kiosk-step {
    flex: 1;
    background: rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.7);
    padding: 6px 10px;
    border-radius: 4px;
    font-weight: 600;
    text-align: center;
    font-size: 0.95rem;
}
.cme_totem--kiosk .cme_totem-kiosk-step--done    { background: #065f46; color: #fff; }
.cme_totem--kiosk .cme_totem-kiosk-step--active  { background: #fde68a; color: #78350f; }
.cme_totem--kiosk .cme_totem-kiosk-step--pending { background: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.5); }
.cme_totem--kiosk .cme_totem-kiosk-step-num {
    display: inline-block;
    width: 1.4em;
    height: 1.4em;
    line-height: 1.4em;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.15);
    text-align: center;
    margin-right: 0.4em;
    font-weight: 700;
}
```

- [ ] **Step 8: Inicializa `state.connOk = true`** (placeholder, será actualizado em Task 10)

No `useState` inicial, adiciona `connOk: true`.

- [ ] **Step 9: Restart + valida**

`docker compose restart web` + hard refresh. Esperado: topbar teal aparece em kiosk com nome da estação, stepper visível com passo "1 Setup" activo, relógio mostra HH:MM inicial.

- [ ] **Step 10: Mostra ao user e aguarda OK**

- [ ] **Step 11: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): KioskTopbar + KioskStepper na Expurgo`.

---

## Task 4: Layout split 60/40 + ScanHero + último resultado

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`

- [ ] **Step 1: Estado `lastScan`**

No `useState`:

```javascript
            /** Último resultado de scan/pick (kiosk feedback "+1"). */
            lastScan: null,           // { name, qty, kind: 'ok'|'err', ts }
            lastScanTimer: null,
```

- [ ] **Step 2: Helper `flashLastScan(name, qty, kind)`**

Adiciona método:

```javascript
    /**
     * Mostra o painel "+N <nome>" no ScanHero. Auto-fade em 1.5s.
     * Som e flash overlay ficam em Task 5.
     */
    flashLastScan(name, qty, kind) {
        if (this.state.lastScanTimer) {
            clearTimeout(this.state.lastScanTimer);
        }
        this.state.lastScan = { name, qty, kind, ts: Date.now() };
        this.state.lastScanTimer = setTimeout(() => {
            this.state.lastScan = null;
            this.state.lastScanTimer = null;
        }, 1500);
    }
```

- [ ] **Step 3: Chama `flashLastScan` quando linhas são adicionadas (expurgo)**

Localiza o método `onPickResult` (catálogo) e `onScanKey` (Enter no scan). Após sucesso de adicionar linha no expurgo (`station === "expurgo"`), invoca:

```javascript
        this.flashLastScan(picked.name || picked.internal_code || "", qty, "ok");
```

Para erro, `kind = "err"` e `name = e.message?.slice(0, 60) || "Falha"`.

- [ ] **Step 4: Sub-template `cme_totem.ScanHero`**

Em `cme_totem.xml`:

```xml
    <t t-name="cme_totem.ScanHero" owl="1">
        <div class="cme_totem-kiosk-hero">
            <div class="cme_totem-kiosk-hero-label">📷 LEIA A ETIQUETA</div>
            <input type="text"
                   t-ref="kioskScanInput"
                   class="form-control form-control-lg cme_totem-kiosk-hero-input"
                   placeholder="Digite ou leia código · Enter confirma"
                   t-model="state.scanInput"
                   t-on-keydown="onScanKey"
                   autocomplete="off"
                   autocorrect="off"
                   spellcheck="false"/>
            <div class="cme_totem-kiosk-hero-search">
                <input type="text"
                       class="form-control form-control-lg"
                       placeholder="Buscar material (nome ou código)"
                       t-model="state.search"
                       t-on-input="scheduleCatalogSearch"/>
            </div>
            <ul class="cme_totem-kiosk-hero-results" t-if="state.results.length">
                <t t-foreach="state.results" t-as="r" t-key="r.id">
                    <li class="cme_totem-kiosk-hero-result-row"
                        t-on-click="() => this.onPickResult(r)">
                        <span class="cme_totem-kiosk-hero-result-name">
                            <t t-esc="r.internal_code"/> — <t t-esc="r.name"/>
                        </span>
                    </li>
                </t>
            </ul>
            <div t-if="state.lastScan"
                 t-attf-class="cme_totem-kiosk-last cme_totem-kiosk-last--{{ state.lastScan.kind }}">
                <span class="cme_totem-kiosk-last-check">✓</span>
                <span class="cme_totem-kiosk-last-qty">+<t t-esc="state.lastScan.qty || 1"/></span>
                <span class="cme_totem-kiosk-last-name" t-esc="state.lastScan.name"/>
            </div>
        </div>
    </t>
```

- [ ] **Step 5: Renderiza split 60/40 em kiosk**

No template `cme_totem.CmeTotem`, **em paralelo** à estrutura existente, adiciona um bloco que só renderiza em kiosk + expurgo, e envolve o conteúdo existente do main. Estratégia: na seção `.cme_totem-scroll`, dentro de `.row`, condicionalmente trocar layout:

```xml
            <div class="cme_totem-scroll flex-grow-1 overflow-auto">
                <t t-if="isKiosk and state.station === 'expurgo' and state.sessionId">
                    <div class="cme_totem-kiosk-split">
                        <div class="cme_totem-kiosk-col-scan">
                            <t t-call="cme_totem.ScanHero"/>
                        </div>
                        <div class="cme_totem-kiosk-col-list">
                            <!-- MaterialsList vai aqui em Task 6 — placeholder por agora -->
                            <div class="text-muted small">Lista materiais (Task 6)</div>
                        </div>
                    </div>
                </t>
                <t t-else="">
                    <!-- estrutura back-office original mantida intacta -->
                    <div class="container-fluid cme_totem-layout px-1 px-sm-2 pb-2">
                        ... (tudo que estava aqui antes — wrap o conteúdo original com este t-else)
                    </div>
                </t>
            </div>
```

(Atenção: durante a edição, **envolver** o `<div class="container-fluid cme_totem-layout ...">` original com o `<t t-else="">` sem perder nada do conteúdo dentro. Sugestão: criar a estrutura nova primeiro num arquivo de trabalho, depois Edit cirúrgico.)

- [ ] **Step 6: SCSS do split + hero + last scan**

```scss
.cme_totem--kiosk .cme_totem-kiosk-split {
    display: grid;
    grid-template-columns: 60% 40%;
    gap: 0.75rem;
    padding: 0.75rem;
    height: calc(100vh - 56px - 44px - 64px);   /* topbar + stepper + footer */
    overflow: hidden;
}
@media (max-width: 991.98px) {
    .cme_totem--kiosk .cme_totem-kiosk-split {
        grid-template-columns: 1fr;
        height: auto;
    }
}

.cme_totem--kiosk .cme_totem-kiosk-col-scan,
.cme_totem--kiosk .cme_totem-kiosk-col-list {
    background: var(--kiosk-surface-2);
    border: 1px solid var(--kiosk-border);
    border-radius: 8px;
    padding: 1rem;
    overflow-y: auto;
    min-height: 0;
}

.cme_totem--kiosk .cme_totem-kiosk-hero {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.cme_totem--kiosk .cme_totem-kiosk-hero-label {
    font-size: var(--kiosk-fs-hero);
    font-weight: 800;
    color: var(--kiosk-hero-fg);
    text-align: center;
}

.cme_totem--kiosk .cme_totem-kiosk-hero-input {
    font-size: 1.5rem !important;
    font-weight: 700;
    height: 64px;
    padding: 0 1rem;
    background: var(--kiosk-hero-bg);
    border: 2px dashed var(--kiosk-hero-bd);
    color: var(--kiosk-hero-fg);
    text-align: center;
}

.cme_totem--kiosk .cme_totem-kiosk-hero-search {
    margin-top: 0.5rem;
}
.cme_totem--kiosk .cme_totem-kiosk-hero-search .form-control {
    font-size: 1.1rem;
}

.cme_totem--kiosk .cme_totem-kiosk-hero-results {
    list-style: none;
    margin: 0;
    padding: 0;
}
.cme_totem--kiosk .cme_totem-kiosk-hero-result-row {
    padding: 10px 12px;
    border-bottom: 1px solid var(--kiosk-border);
    cursor: pointer;
    font-size: 1.05rem;
}
.cme_totem--kiosk .cme_totem-kiosk-hero-result-row:hover {
    background: var(--kiosk-ok-bg);
}

.cme_totem--kiosk .cme_totem-kiosk-last {
    margin-top: 0.5rem;
    padding: 12px 14px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    animation: cme-kiosk-pulse 1.5s ease-out;
}
.cme_totem--kiosk .cme_totem-kiosk-last--ok {
    background: var(--kiosk-ok-bg);
    border: 1px solid var(--kiosk-ok-bd);
    color: var(--kiosk-ok-fg);
}
.cme_totem--kiosk .cme_totem-kiosk-last--err {
    background: var(--kiosk-err-bg);
    border: 1px solid var(--kiosk-err-bd);
    color: var(--kiosk-err-fg);
}
.cme_totem--kiosk .cme_totem-kiosk-last-check { font-size: 1.5rem; }
.cme_totem--kiosk .cme_totem-kiosk-last-qty { font-size: 1.4rem; font-variant-numeric: tabular-nums; }
.cme_totem--kiosk .cme_totem-kiosk-last-name { font-size: 1.1rem; }

@keyframes cme-kiosk-pulse {
    0%   { transform: scale(0.96); opacity: 0; }
    20%  { transform: scale(1.02); opacity: 1; }
    100% { transform: scale(1.0);  opacity: 1; }
}
```

- [ ] **Step 7: Restart + testa scan**

`docker compose restart web` + hard refresh. Cria sessão expurgo (via setup atual), lê uma etiqueta válida ou clica num resultado de busca catálogo. Esperado: split 60/40, hero scan grande, "+1 ✓ nome" aparece e some em 1.5s.

- [ ] **Step 8: Mostra ao user e aguarda OK**

- [ ] **Step 9: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): split 60/40 + ScanHero + flash último resultado`.

---

## Task 5: Web Audio beep + flash overlay 200ms

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`

- [ ] **Step 1: Helper Web Audio**

No `cme_totem.js`, adiciona métodos privados:

```javascript
    _ensureAudioContext() {
        if (!this._audioCtx && this.state.appConfig?.sound_enabled) {
            try {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                this._audioCtx = Ctx ? new Ctx() : null;
            } catch (e) {
                this._audioCtx = null;
            }
        }
        return this._audioCtx;
    }

    _beep(kind) {
        if (!this.isKiosk || !this.state.appConfig?.sound_enabled) return;
        const ctx = this._ensureAudioContext();
        if (!ctx) return;
        try {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            const freq = kind === "err" ? 220 : 880;
            const dur = kind === "err" ? 0.18 : 0.07;
            osc.type = "sine";
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.001, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
            osc.connect(gain).connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + dur + 0.02);
        } catch (e) {
            // browser pode exigir gesto do user antes de tocar; em kiosk fixo um scan/click resolve
        }
    }

    _flashOverlay(kind) {
        if (!this.isKiosk) return;
        this.state.flash = kind;   // 'ok' | 'err'
        setTimeout(() => { this.state.flash = null; }, 200);
    }
```

- [ ] **Step 2: Estado `flash`**

No `useState` inicial: `flash: null,`.

- [ ] **Step 3: Hook em `flashLastScan`**

Modifica `flashLastScan` (Task 4) para também chamar beep+flash:

```javascript
    flashLastScan(name, qty, kind) {
        if (this.state.lastScanTimer) clearTimeout(this.state.lastScanTimer);
        this.state.lastScan = { name, qty, kind, ts: Date.now() };
        this._beep(kind);
        this._flashOverlay(kind);
        this.state.lastScanTimer = setTimeout(() => {
            this.state.lastScan = null;
            this.state.lastScanTimer = null;
        }, 1500);
    }
```

- [ ] **Step 4: Overlay de flash no template**

No root do template, logo antes do `</div>` de fecho, adiciona:

```xml
        <div t-if="isKiosk and state.flash"
             t-attf-class="cme_totem-kiosk-flash cme_totem-kiosk-flash--{{ state.flash }}"/>
```

- [ ] **Step 5: SCSS flash**

```scss
.cme_totem--kiosk .cme_totem-kiosk-flash {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 1040;
    animation: cme-kiosk-flash 200ms ease-out;
}
.cme_totem--kiosk .cme_totem-kiosk-flash--ok  { background: rgba(52, 211, 153, 0.35); }
.cme_totem--kiosk .cme_totem-kiosk-flash--err { background: rgba(252, 165, 165, 0.45); }

@keyframes cme-kiosk-flash {
    from { opacity: 1; }
    to   { opacity: 0; }
}
```

- [ ] **Step 6: Restart + testa**

Scan válido → beep agudo + flash verde. Scan inválido → beep grave + flash vermelho.

- [ ] **Step 7: Mostra ao user e aguarda OK**

Atenção: Web Audio em browsers exige primeiro gesto do user — em kiosk dedicado isto não é problema; mas em teste local, o primeiro click activa.

- [ ] **Step 8: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): Web Audio beep + flash overlay (kiosk)`.

---

## Task 6: MaterialsList na coluna direita

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`

- [ ] **Step 1: Sub-template `cme_totem.MaterialsList`**

Em `cme_totem.xml`:

```xml
    <t t-name="cme_totem.MaterialsList" owl="1">
        <div class="cme_totem-kiosk-list">
            <div class="cme_totem-kiosk-list-header">
                <span>Materiais no recebimento</span>
                <span class="cme_totem-kiosk-list-count">
                    <t t-esc="(state.summary and state.summary.lines and state.summary.lines.length) or 0"/>
                </span>
            </div>
            <div class="cme_totem-kiosk-list-empty"
                 t-if="!state.summary or !state.summary.lines or !state.summary.lines.length">
                <div class="cme_totem-kiosk-list-empty-icon">📭</div>
                <div>Leia uma etiqueta ou busque um material para começar.</div>
            </div>
            <table class="cme_totem-kiosk-list-table" t-if="state.summary and state.summary.lines and state.summary.lines.length">
                <tbody>
                    <t t-foreach="state.summary.lines" t-as="row" t-key="row.line_id or row.trace_unit_id or row_index">
                        <tr>
                            <td class="cme_totem-kiosk-list-name">
                                <div class="cme_totem-kiosk-list-mat-code" t-esc="row.internal_code or ''"/>
                                <div class="cme_totem-kiosk-list-mat-name" t-esc="row.name"/>
                            </td>
                            <td class="cme_totem-kiosk-list-qty">
                                <input t-if="row.line_editable" type="number"
                                       class="form-control form-control-sm text-end"
                                       t-att-step="1"
                                       t-att-min="0"
                                       t-att-value="row.quantity"
                                       t-on-change="(ev) => this.onSummaryLineQtyChange(row, ev)"/>
                                <span t-if="!row.line_editable" t-esc="row.quantity"/>
                            </td>
                        </tr>
                    </t>
                </tbody>
            </table>
            <div class="cme_totem-kiosk-list-total" t-if="state.summary and state.summary.total_quantity !== undefined">
                <span>Total</span>
                <span class="cme_totem-kiosk-list-total-num" t-esc="state.summary.total_quantity"/>
            </div>
        </div>
    </t>
```

- [ ] **Step 2: Substitui o placeholder na coluna direita (Task 4)**

No bloco `cme_totem-kiosk-col-list`:

```xml
                        <div class="cme_totem-kiosk-col-list">
                            <t t-call="cme_totem.MaterialsList"/>
                        </div>
```

- [ ] **Step 3: SCSS lista**

```scss
.cme_totem--kiosk .cme_totem-kiosk-list {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.cme_totem--kiosk .cme_totem-kiosk-list-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--kiosk-primary);
    margin-bottom: 0.5rem;
}

.cme_totem--kiosk .cme_totem-kiosk-list-count {
    background: var(--kiosk-accent);
    color: #fff;
    padding: 1px 10px;
    border-radius: 999px;
    font-size: 0.95rem;
}

.cme_totem--kiosk .cme_totem-kiosk-list-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    text-align: center;
    font-size: 0.95rem;
    gap: 0.5rem;
}
.cme_totem--kiosk .cme_totem-kiosk-list-empty-icon {
    font-size: 2.5rem;
    opacity: 0.5;
}

.cme_totem--kiosk .cme_totem-kiosk-list-table {
    width: 100%;
    border-collapse: collapse;
    flex: 1;
}
.cme_totem--kiosk .cme_totem-kiosk-list-table tr {
    border-bottom: 1px solid var(--kiosk-border);
}
.cme_totem--kiosk .cme_totem-kiosk-list-table td {
    padding: 10px 6px;
    vertical-align: middle;
}
.cme_totem--kiosk .cme_totem-kiosk-list-mat-code {
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 700;
}
.cme_totem--kiosk .cme_totem-kiosk-list-mat-name {
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
}
.cme_totem--kiosk .cme_totem-kiosk-list-qty input {
    width: 80px;
    font-size: var(--kiosk-fs-num);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.cme_totem--kiosk .cme_totem-kiosk-list-qty span {
    font-size: var(--kiosk-fs-num);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}

.cme_totem--kiosk .cme_totem-kiosk-list-total {
    border-top: 2px solid var(--kiosk-primary);
    padding-top: 0.5rem;
    margin-top: 0.5rem;
    display: flex;
    justify-content: space-between;
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--kiosk-primary);
}
.cme_totem--kiosk .cme_totem-kiosk-list-total-num {
    font-size: var(--kiosk-fs-num);
    font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 4: Restart + valida**

Cria sessão → scaneia 2-3 itens → lista direita actualiza em tempo real com count, qty editável e total.

- [ ] **Step 5: Mostra ao user e aguarda OK**

- [ ] **Step 6: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): MaterialsList na coluna direita (kiosk)`.

---

## Task 7: ActionFooter + atalhos teclado (F1–F5, Esc)

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`

- [ ] **Step 1: Listener global de teclado**

No `setup()` do `CmeTotem`:

```javascript
        owl.useExternalListener(window, "keydown", (ev) => {
            if (!this.isKiosk) return;
            // Ignora se utilizador está a digitar num input que NÃO é o scan principal e não é uma F-key.
            const tag = (ev.target?.tagName || "").toLowerCase();
            const isTypingTarget = ["input", "textarea", "select"].includes(tag);
            const isFnKey = /^F\d+$/.test(ev.key);
            if (isTypingTarget && !isFnKey && ev.key !== "Escape") return;

            switch (ev.key) {
                case "F1":  ev.preventDefault(); this.onKioskHelp(); break;
                case "F2":  ev.preventDefault(); this.onKioskRetrabalho(); break;
                case "F3":  ev.preventDefault(); this.onKioskTogglePendings(); break;
                case "F4":  ev.preventDefault(); this.onKioskConcluir(); break;
                case "F5":  ev.preventDefault(); this.refreshPipelineLists(); break;
                case "Escape": this.onKioskEscape(); break;
                default: return;
            }
        });
```

- [ ] **Step 2: Handlers — versão piloto (Expurgo)**

```javascript
    onKioskHelp() {
        this.state.kioskHelpOpen = !this.state.kioskHelpOpen;
    }
    onKioskRetrabalho() {
        if (this.state.station === "expurgo") {
            this.openReworkModal();   // já existe
        }
    }
    onKioskTogglePendings() {
        this.state.kioskPendingsOpen = !this.state.kioskPendingsOpen;
    }
    onKioskConcluir() {
        if (this.state.station === "expurgo" && this.state.sessionId) {
            this.state.kioskConfirmOpen = true;
        }
    }
    onKioskEscape() {
        this.state.kioskHelpOpen = false;
        this.state.kioskPendingsOpen = false;
        this.state.kioskConfirmOpen = false;
    }
```

Os modais propriamente serão criados em Task 8 (confirm) e Task 9 (drawer pendências). Por agora os flags só ligam/desligam.

- [ ] **Step 3: Estado dos modais kiosk**

No `useState` inicial:

```javascript
            kioskHelpOpen: false,
            kioskPendingsOpen: false,
            kioskConfirmOpen: false,
```

- [ ] **Step 4: Sub-template `cme_totem.ActionFooter`**

```xml
    <t t-name="cme_totem.ActionFooter" owl="1">
        <div class="cme_totem-kiosk-footer">
            <div class="cme_totem-kiosk-footer-hints">
                <span class="cme_totem-kiosk-hint"><kbd>F1</kbd> Ajuda</span>
                <span class="cme_totem-kiosk-hint"><kbd>F2</kbd> Retrabalho</span>
                <span class="cme_totem-kiosk-hint"><kbd>F3</kbd> Pendências</span>
                <span class="cme_totem-kiosk-hint"><kbd>F5</kbd> Atualizar</span>
            </div>
            <button type="button"
                    class="btn cme_totem-kiosk-btn-primary"
                    t-att-disabled="!state.sessionId"
                    t-on-click="onKioskConcluir">
                <kbd>F4</kbd>
                <span class="cme_totem-kiosk-btn-primary-label">Concluir</span>
                <span class="cme_totem-kiosk-btn-primary-arrow">→</span>
            </button>
        </div>
    </t>
```

- [ ] **Step 5: Renderiza footer em kiosk**

No root do template, logo antes do fecho do componente raiz (depois de `.cme_totem-scroll`):

```xml
        <t t-if="isKiosk and state.station === 'expurgo'">
            <t t-call="cme_totem.ActionFooter"/>
        </t>
```

- [ ] **Step 6: SCSS footer**

```scss
.cme_totem--kiosk .cme_totem-kiosk-footer {
    background: var(--kiosk-primary);
    color: #fff;
    padding: 8px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    min-height: 64px;
}

.cme_totem--kiosk .cme_totem-kiosk-footer-hints {
    display: flex;
    gap: 1rem;
    font-size: 0.95rem;
}

.cme_totem--kiosk .cme_totem-kiosk-hint {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    opacity: 0.9;
}
.cme_totem--kiosk .cme_totem-kiosk-hint kbd {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 0.85rem;
}

.cme_totem--kiosk .cme_totem-kiosk-btn-primary {
    background: #fde68a;
    color: #78350f;
    font-weight: 800;
    font-size: 1.15rem;
    padding: 10px 22px;
    border-radius: 6px;
    border: none;
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    min-height: 56px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
}
.cme_totem--kiosk .cme_totem-kiosk-btn-primary:disabled {
    opacity: 0.45;
    box-shadow: none;
}
.cme_totem--kiosk .cme_totem-kiosk-btn-primary kbd {
    background: rgba(120, 53, 15, 0.15);
    color: #78350f;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.95rem;
}
.cme_totem--kiosk .cme_totem-kiosk-btn-primary-arrow { font-size: 1.4rem; }
```

- [ ] **Step 7: Restart + testa atalhos**

Pressiona F1/F2/F3/F4 com sessão e sem sessão. Esperado: F4 abre flag confirm (modal será visual em Task 8 — por agora basta ver `state.kioskConfirmOpen = true` em DevTools/console).

- [ ] **Step 8: Mostra ao user e aguarda OK**

- [ ] **Step 9: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): ActionFooter + atalhos teclado F1-F5 (kiosk)`.

---

## Task 8: ConfirmModal antes "Concluir"

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`

- [ ] **Step 1: Validações `canConcluirExpurgo` + razões**

```javascript
    get canConcluirExpurgo() {
        return this.expurgoBlockReasons.length === 0;
    }

    get expurgoBlockReasons() {
        const reasons = [];
        if (this.state.station !== "expurgo") return reasons;
        const lines = this.state.summary?.lines || [];
        if (!lines.length) reasons.push("Adicione ao menos 1 item antes de concluir.");
        const opMode = this.state.appConfig?.operating_mode;
        if (opMode === "third_party" && !this.state.materialOwnerId) {
            reasons.push("Cliente dono do material é obrigatório (modo CME terceiros).");
        }
        return reasons;
    }
```

- [ ] **Step 2: Handler `confirmConcluirExpurgo`**

```javascript
    async confirmConcluirExpurgo() {
        if (!this.canConcluirExpurgo) return;
        this.state.kioskConfirmOpen = false;
        await this.onDoneExpurgo();   // já existe
    }
```

- [ ] **Step 3: Sub-template `cme_totem.ConfirmModal`**

```xml
    <t t-name="cme_totem.ConfirmModal" owl="1">
        <div class="cme_totem-kiosk-modal-backdrop" t-on-click="onKioskEscape">
            <div class="cme_totem-kiosk-modal" t-on-click.stop="">
                <div class="cme_totem-kiosk-modal-header">Concluir recebimento</div>
                <div class="cme_totem-kiosk-modal-body">
                    <div class="cme_totem-kiosk-modal-resumo">
                        <div><b>Setor:</b> <t t-esc="setupPillText or '—'"/></div>
                        <div><b>Lote:</b> <t t-esc="(state.summary and state.summary.process_lot_name) or '—'"/></div>
                        <div><b>Itens:</b> <t t-esc="(state.summary and state.summary.lines and state.summary.lines.length) or 0"/></div>
                        <div><b>Total:</b> <t t-esc="(state.summary and state.summary.total_quantity) or 0"/></div>
                    </div>
                    <div class="cme_totem-kiosk-modal-block" t-if="expurgoBlockReasons.length">
                        <div class="cme_totem-kiosk-modal-block-title">⚠ Bloqueios:</div>
                        <ul>
                            <t t-foreach="expurgoBlockReasons" t-as="r" t-key="r_index"><li t-esc="r"/></t>
                        </ul>
                    </div>
                </div>
                <div class="cme_totem-kiosk-modal-footer">
                    <button type="button" class="btn btn-secondary" t-on-click="onKioskEscape">
                        Cancelar <kbd>Esc</kbd>
                    </button>
                    <button type="button" class="btn cme_totem-kiosk-btn-ok"
                            t-att-disabled="!canConcluirExpurgo"
                            t-on-click="confirmConcluirExpurgo">
                        Confirmar <kbd>Enter</kbd>
                    </button>
                </div>
            </div>
        </div>
    </t>
```

- [ ] **Step 4: Renderiza modal quando flag activa**

No root, antes do flash overlay (Task 5):

```xml
        <t t-if="isKiosk and state.kioskConfirmOpen">
            <t t-call="cme_totem.ConfirmModal"/>
        </t>
```

- [ ] **Step 5: Atalho Enter dentro do modal**

Estende o `keydown` listener (Task 7) — antes do switch, adiciona:

```javascript
            if (this.state.kioskConfirmOpen) {
                if (ev.key === "Enter") {
                    ev.preventDefault();
                    this.confirmConcluirExpurgo();
                    return;
                }
                if (ev.key === "Escape") {
                    ev.preventDefault();
                    this.state.kioskConfirmOpen = false;
                    return;
                }
                return;   // bloqueia outros atalhos enquanto modal aberto
            }
```

- [ ] **Step 6: SCSS modal**

```scss
.cme_totem--kiosk .cme_totem-kiosk-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.55);
    z-index: 1050;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
}

.cme_totem--kiosk .cme_totem-kiosk-modal {
    background: #fff;
    border-radius: 10px;
    width: 100%;
    max-width: 560px;
    box-shadow: 0 14px 30px rgba(0, 0, 0, 0.35);
    overflow: hidden;
}

.cme_totem--kiosk .cme_totem-kiosk-modal-header {
    background: var(--kiosk-primary);
    color: #fff;
    padding: 14px 20px;
    font-weight: 700;
    font-size: 1.15rem;
}

.cme_totem--kiosk .cme_totem-kiosk-modal-body {
    padding: 18px 20px;
    font-size: 1rem;
    line-height: 1.6;
    color: #0f172a;
}
.cme_totem--kiosk .cme_totem-kiosk-modal-resumo div { padding: 2px 0; }

.cme_totem--kiosk .cme_totem-kiosk-modal-block {
    margin-top: 0.75rem;
    padding: 10px 14px;
    background: var(--kiosk-err-bg);
    border: 1px solid var(--kiosk-err-bd);
    color: var(--kiosk-err-fg);
    border-radius: 6px;
    font-weight: 600;
}
.cme_totem--kiosk .cme_totem-kiosk-modal-block ul { margin: 4px 0 0; padding-left: 18px; }

.cme_totem--kiosk .cme_totem-kiosk-modal-footer {
    background: var(--kiosk-surface-2);
    border-top: 1px solid var(--kiosk-border);
    padding: 12px 20px;
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
}

.cme_totem--kiosk .cme_totem-kiosk-btn-ok {
    background: var(--kiosk-accent);
    color: #fff;
    font-weight: 700;
    padding: 8px 18px;
}
.cme_totem--kiosk .cme_totem-kiosk-btn-ok:disabled {
    opacity: 0.45;
}
```

- [ ] **Step 7: Restart + testa**

- Cria sessão sem linhas, F4 → modal mostra "⚠ Bloqueios: adicione ao menos 1 item", botão Confirmar disabled.
- Adiciona linha, F4 → resumo limpo, Confirmar enabled, Enter conclui.
- Modo `third_party` sem dono → bloqueio.

- [ ] **Step 8: Mostra ao user e aguarda OK**

- [ ] **Step 9: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): ConfirmModal antes concluir (kiosk) + validações`.

---

## Task 9: Setup pill colapsável + sidebar drawer (F3) + auto-foco

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`

- [ ] **Step 1: Setup só visível antes da sessão**

Wrap o bloco existente do setup expurgo (linhas 156–190 do template original) com:

```xml
                    <div class="mb-3" t-if="state.station === 'expurgo' and (!isKiosk or !state.sessionId)">
                        ... (conteúdo actual: setor, dono, método, botão Novo recebimento)
                    </div>
```

(Em kiosk, depois de criar sessão, o setup deixa de aparecer no main — fica representado pelo `setupPillText` no topbar.)

- [ ] **Step 2: Auto-foco scan input**

```javascript
        // ref criada em Task 4 — kioskScanInput
        this.kioskScanInputRef = owl.useRef("kioskScanInput");

        this._scheduleScanFocus = () => {
            if (!this.isKiosk) return;
            if (this.state.kioskConfirmOpen || this.state.kioskHelpOpen || this.state.kioskPendingsOpen) return;
            const el = this.kioskScanInputRef.el;
            if (el && document.activeElement !== el) {
                setTimeout(() => { try { el.focus(); } catch (e) {} }, 50);
            }
        };

        owl.onMounted(() => {
            this._scheduleScanFocus();
            this._visibilityHandler = () => {
                if (!document.hidden) this._scheduleScanFocus();
            };
            document.addEventListener("visibilitychange", this._visibilityHandler);
        });
        owl.onPatched(() => this._scheduleScanFocus());
        owl.onWillUnmount(() => {
            if (this._visibilityHandler) {
                document.removeEventListener("visibilitychange", this._visibilityHandler);
            }
        });
```

Imports adicionais: `useRef`.

- [ ] **Step 3: Sidebar drawer (F3)**

Em vez de aside fixo, em kiosk transforma o `cme_totem-pipeline-aside` num drawer. No template, condiciona:

```xml
            <aside t-attf-class="col-12 col-lg-3 col-xl-3 order-lg-0 cme_totem-pipeline-aside mb-0 {{ isKiosk ? 'cme_totem-kiosk-drawer' : '' }} {{ isKiosk and state.kioskPendingsOpen ? 'cme_totem-kiosk-drawer--open' : '' }}">
```

E adiciona backdrop quando aberto:

```xml
        <t t-if="isKiosk and state.kioskPendingsOpen">
            <div class="cme_totem-kiosk-drawer-backdrop" t-on-click="() => this.state.kioskPendingsOpen = false"/>
        </t>
```

- [ ] **Step 4: SCSS drawer**

```scss
.cme_totem--kiosk .cme_totem-kiosk-drawer {
    position: fixed;
    top: 56px;       /* abaixo do topbar */
    left: 0;
    bottom: 64px;    /* acima do footer */
    width: min(420px, 90vw);
    z-index: 1045;
    background: #fff;
    border-right: 1px solid var(--kiosk-border);
    transform: translateX(-105%);
    transition: transform 200ms ease-out;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
    overflow-y: auto;
}
.cme_totem--kiosk .cme_totem-kiosk-drawer--open {
    transform: translateX(0);
}
.cme_totem--kiosk .cme_totem-kiosk-drawer-backdrop {
    position: fixed;
    inset: 56px 0 64px 0;
    background: rgba(15, 23, 42, 0.4);
    z-index: 1044;
}
```

- [ ] **Step 5: Help modal mínimo (F1)**

Sub-template e estilo simples — mostra mapa de atalhos:

```xml
    <t t-name="cme_totem.KioskHelp" owl="1">
        <div class="cme_totem-kiosk-modal-backdrop" t-on-click="onKioskEscape">
            <div class="cme_totem-kiosk-modal" t-on-click.stop="">
                <div class="cme_totem-kiosk-modal-header">Atalhos do totem</div>
                <div class="cme_totem-kiosk-modal-body">
                    <div><kbd>F1</kbd> esta ajuda</div>
                    <div><kbd>F2</kbd> abrir retrabalho</div>
                    <div><kbd>F3</kbd> abrir/fechar pendências</div>
                    <div><kbd>F4</kbd> concluir recebimento</div>
                    <div><kbd>F5</kbd> atualizar listas</div>
                    <div><kbd>Esc</kbd> fechar modal aberto</div>
                    <div><kbd>Enter</kbd> confirmar scan / modal</div>
                </div>
                <div class="cme_totem-kiosk-modal-footer">
                    <button type="button" class="btn btn-secondary" t-on-click="onKioskEscape">Fechar</button>
                </div>
            </div>
        </div>
    </t>
```

E render condicional no root:

```xml
        <t t-if="isKiosk and state.kioskHelpOpen">
            <t t-call="cme_totem.KioskHelp"/>
        </t>
```

- [ ] **Step 6: Restart + testa**

- Sessão criada → setup desaparece, pill aparece no topbar.
- F3 abre drawer, F3 ou Esc fecha.
- F1 abre help.
- Foco do scan input retorna após clicar fora (no header, no list).

- [ ] **Step 7: Mostra ao user e aguarda OK**

- [ ] **Step 8: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): setup pill + drawer pendências + help modal + auto-foco scan (kiosk)`.

---

## Task 10: Idle overlay + relógio + ping conexão

**Files:**
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.xml`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.scss`
- Modify: `addons/afr_cme/afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js`

- [ ] **Step 1: Timers no `setup()`**

```javascript
        owl.onMounted(() => {
            this._clockTick = setInterval(() => {
                this.state.clockText = this._formatClock(new Date());
            }, 30 * 1000);
            this.state.clockText = this._formatClock(new Date());

            this._connTick = setInterval(async () => {
                try {
                    await this.rpc("/web/webclient/version_info", {});
                    this.state.connOk = true;
                } catch (e) {
                    this.state.connOk = false;
                }
            }, 30 * 1000);

            this._resetIdleTimer();
            ["mousemove", "keydown", "touchstart", "scroll"].forEach((ev) => {
                window.addEventListener(ev, () => this._resetIdleTimer(), { passive: true });
            });
        });

        owl.onWillUnmount(() => {
            clearInterval(this._clockTick);
            clearInterval(this._connTick);
            clearTimeout(this._idleTimer);
        });
```

- [ ] **Step 2: `_resetIdleTimer`**

```javascript
    _resetIdleTimer() {
        clearTimeout(this._idleTimer);
        if (!this.isKiosk) return;
        const minutes = this.state.appConfig?.idle_timeout_min || 5;
        const ms = minutes * 60 * 1000;
        this._idleTimer = setTimeout(() => {
            if (!this.state.sessionId) {
                this.state.kioskIdleOpen = true;
            }
        }, ms);
        if (this.state.kioskIdleOpen) {
            // qualquer actividade fecha o idle
            this.state.kioskIdleOpen = false;
        }
    }
```

- [ ] **Step 3: Estado**

```javascript
            kioskIdleOpen: false,
```

- [ ] **Step 4: Sub-template `cme_totem.IdleOverlay`**

```xml
    <t t-name="cme_totem.IdleOverlay" owl="1">
        <div class="cme_totem-kiosk-idle" t-on-click="() => this.state.kioskIdleOpen = false">
            <div class="cme_totem-kiosk-idle-content">
                <div class="cme_totem-kiosk-idle-icon">🧼</div>
                <div class="cme_totem-kiosk-idle-title">Totem CME — Expurgo</div>
                <div class="cme_totem-kiosk-idle-cta">Toque ou leia uma etiqueta para começar</div>
                <div class="cme_totem-kiosk-idle-clock" t-esc="kioskClockText"/>
            </div>
        </div>
    </t>
```

Render no root:

```xml
        <t t-if="isKiosk and state.kioskIdleOpen">
            <t t-call="cme_totem.IdleOverlay"/>
        </t>
```

- [ ] **Step 5: SCSS idle**

```scss
.cme_totem--kiosk .cme_totem-kiosk-idle {
    position: fixed;
    inset: 0;
    z-index: 1060;
    background: linear-gradient(135deg, #134e4a 0%, #0f766e 100%);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}
.cme_totem--kiosk .cme_totem-kiosk-idle-content {
    text-align: center;
}
.cme_totem--kiosk .cme_totem-kiosk-idle-icon { font-size: 5rem; }
.cme_totem--kiosk .cme_totem-kiosk-idle-title { font-size: 2rem; font-weight: 800; letter-spacing: 0.05em; margin-top: 0.5rem; }
.cme_totem--kiosk .cme_totem-kiosk-idle-cta { font-size: 1.25rem; opacity: 0.9; margin-top: 0.75rem; }
.cme_totem--kiosk .cme_totem-kiosk-idle-clock { font-size: 3rem; font-weight: 700; margin-top: 1.5rem; font-variant-numeric: tabular-nums; }
```

- [ ] **Step 6: Restart + testa**

- Espera `idle_timeout_min` (configurar para 1 minuto via ICP em dev) sem sessão → overlay aparece.
- Click/touch/scan fecha.
- Indicador conexão muda para vermelho se desligar o Odoo.

- [ ] **Step 7: Mostra ao user e aguarda OK**

- [ ] **Step 8: Commit**

Mensagem: `feat(afr_cme_rastreabilidade): idle overlay + relógio + ping conexão (kiosk)`.

---

## Task 11: Manual checklist doc

**Files:**
- Create: `addons/afr_cme/afr_cme_rastreabilidade/docs/cme_totem_kiosk_manual_check.md`

- [ ] **Step 1: Escreve checklist**

```markdown
# Checklist manual — Piloto Expurgo kiosk

Validar antes de marcar o piloto como concluído.

## Ambiente
- [ ] DB de teste com módulo `afr_cme_rastreabilidade` actualizado
- [ ] Monitor 22" portrait OU landscape (testar ambos)
- [ ] Leitor USB de código de barras configurado
- [ ] Browser Chromium 100+ em modo kiosk (`chromium --kiosk http://host:8083/web?kiosk=1#action=...`)

## Visual
- [ ] Topbar Odoo (logo, user, search) NÃO aparece
- [ ] Paleta teal aplicada (header, footer, hero scan, hint kbd)
- [ ] Tipografia ≥ 18px base, ≥ 28px hero
- [ ] Stepper mostra "1 Setup → 2 Scan + materiais → 3 Concluir"
- [ ] Split 60/40 (scan à esq, lista à dir)
- [ ] Sem barra de scroll horizontal

## Funcional
- [ ] Sem sessão: setup visível, "Novo recebimento" disponível
- [ ] Após criar sessão: setup desaparece, pill no topbar mostra "Setor · Método · Dono"
- [ ] Scan etiqueta válida: beep agudo + flash verde 200ms + "+1 ✓ nome" 1.5s + linha aparece à direita
- [ ] Scan código inexistente: beep grave + flash vermelho + toast erro
- [ ] Busca catálogo (digitação): resultados em até 350ms
- [ ] Edita qty inline na lista: total actualiza
- [ ] F1 abre help modal; Esc fecha
- [ ] F2 abre modal retrabalho; Esc cancela
- [ ] F3 abre drawer "Pendências"; F3 ou Esc fecha
- [ ] F4 abre confirm modal
  - [ ] Sem linhas: botão Confirmar disabled, mensagem clara
  - [ ] Modo third_party sem dono: bloqueio claro
  - [ ] Com linhas válidas: resumo (setor/lote/itens/total), Enter confirma, `totem_done` chama, sessão fecha, stepper retorna a "1 Setup"
- [ ] F5 atualiza listas laterais
- [ ] Foco do scan retorna após clicar fora
- [ ] Após `idle_timeout_min` sem sessão: overlay idle aparece; toque/scan fecha
- [ ] Indicador conexão vermelho ≤ 30s após desligar Odoo; volta verde após religar

## Regressão back-office
- [ ] Abrir totem sem `?kiosk=1`: layout original aparece
- [ ] ICP `cme.totem.kiosk_default = False` mantém back-office
- [ ] Outras estações (preparo/ester/entrega/paciente) sem alteração visual

## Performance
- [ ] Scan → linha visível < 250 ms
- [ ] Foco mantido após RPC durante leitura rápida (3 scans em 5s)
- [ ] Sem leak de memória após 15 min de uso contínuo (DevTools heap snapshot)
```

- [ ] **Step 2: Mostra ao user e aguarda OK**

- [ ] **Step 3: Commit**

```bash
cd addons/afr_cme
git add afr_cme_rastreabilidade/docs/cme_totem_kiosk_manual_check.md
git commit -m "docs(afr_cme_rastreabilidade): checklist manual kiosk (piloto Expurgo)"
git push origin main
cd /home/afonso/docker/odoo_engenapp
git add addons/afr_cme TODO.md
# Mover TODO entry "Em curso" → "Feito" com data ISO
git commit -m "chore: bump afr_cme submodule (kiosk piloto concluído) + TODO"
git push
```

---

## Self-Review (lock-in)

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Approach B híbrido (flag kiosk) | Task 2 |
| Layout split 60/40 | Task 4 + 6 |
| Topbar + Stepper | Task 3 |
| ScanHero + último resultado | Task 4 |
| Web Audio beep + flash | Task 5 |
| MaterialsList | Task 6 |
| ActionFooter + atalhos F-keys | Task 7 |
| ConfirmModal + validações | Task 8 |
| Setup pill + sidebar drawer + auto-foco | Task 9 |
| Idle overlay + relógio + ping | Task 10 |
| 3 ICPs + smoke test + extend `totem_get_app_config` | Task 1 |
| Manual checklist | Task 11 |
| Paleta teal cirúrgico | Task 2 (vars) usado em 3-10 |
| Não-objetivos respeitados (outras estações sem mexer) | Tasks 3, 4, 7: blocks só renderizam quando `station === 'expurgo'` |

**QUnit tests:** spec mencionava QUnit. Plan **deferre QUnit para Fase B** porque o projeto não tem infra de QUnit hoje (sem `static/tests/`, sem `web.qunit_suite_tests` no manifest). Smoke Python (Task 1) + manual (Task 11) cobrem piloto. Spec será actualizado em commit posterior se a deferência for confirmada pelo user.

**Placeholder scan:** Nenhum "TODO" ou "TBD" nos passos. Cada step contém código completo ou comando exacto.

**Type consistency:** nomes verificados — `flashLastScan`, `_beep`, `_flashOverlay`, `_resetIdleTimer`, `onKioskConcluir`, `confirmConcluirExpurgo`, `setupPillText`, `kioskStepperState`, `kioskClockText`, `isKiosk`, `canConcluirExpurgo`, `expurgoBlockReasons` — coerentes entre tasks.

**Submodule workflow:** todas as edições de código vivem em `addons/afr_cme/afr_cme_rastreabilidade/` (submodule). Commits devem ser feitos **de dentro de `addons/afr_cme/`** primeiro, depois bump do pointer no monorepo. Memory ref: `feedback_submodule_workflow`.

**Commit rule:** cada task tem o passo "Mostra ao user e aguarda OK" ANTES de "Commit". Memory ref: `feedback_commit_after_test` + `feedback_commit_via_agent` (usa subagent `git-commit-push` model haiku).
