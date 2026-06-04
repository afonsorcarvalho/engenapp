# Fase D — Board OWL (Gantt técnico × dia) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um board OWL (client action) com grade técnico×dia das visitas, cor por OS, destaque de conflito, drag pra reagendar (data+técnico) e clique pra abrir o form. Lógica de dados em 2 métodos Python testáveis.

**Architecture:** `ir.actions.client` (tag `afr_qualif_visita_board`) + componente OWL em `static/src/board/`, lendo/gravando via `orm.call` de `afr.qualificacao.os.visita.board_fetch` e `.board_reschedule`. Padrão do CME totem (`afr_cme_rastreabilidade/static/src/cme_totem/`).

**Tech Stack:** Odoo 16.0 Community, OWL 2 (`@odoo/owl`, `@web/core/*`), Python, SCSS, `TransactionCase`.

**Testes (Python):** container `odoo_engenapp-web-1`, DB `odoo_ecm_test`:
```
docker exec odoo_engenapp-web-1 odoo -d odoo_ecm_test --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --no-http --workers=0 -u afr_qualificacao_agendamento --test-enable --test-tags /afr_qualificacao_agendamento:TestBoard --stop-after-init
```
(NÃO commitar durante a execução. O OWL/JS é validado manualmente no navegador.)

**Referências:** visita model `afr_qualificacao_agendamento/models/os_visita.py` (campos `tecnico_id`, `date`, `os_id`, `partner_id`, `planned_hours`, `state`, `equipment_ids`, e os 4 conflitos). Padrão OWL: `afr_cme_rastreabilidade/static/src/cme_totem/cme_totem.js` (registry actions, useService). Menu raiz: `afr_qualificacao.menu_afr_qualificacao_root`.

---

## Estrutura de arquivos

```
afr_qualificacao_agendamento/
├── models/os_visita.py                       # MODIFY: + board_fetch, board_reschedule
├── views/visita_board_action.xml             # CREATE: ir.actions.client + menuitem
├── static/src/board/visita_board.js          # CREATE: componente OWL
├── static/src/board/visita_board.xml         # CREATE: template QWeb-OWL
├── static/src/board/visita_board.scss        # CREATE: estilos
├── __manifest__.py                           # MODIFY: + data(action) + assets
└── tests/test_board.py                       # CREATE: TestBoard
└── tests/__init__.py                         # MODIFY: + test_board
```

---

## Task 1: Backend — `board_fetch` / `board_reschedule` (TDD)

**Files:**
- Modify: `models/os_visita.py`
- Create: `tests/test_board.py`
- Modify: `tests/__init__.py`

- [ ] **Step 1: Escrever os testes que falham (`tests/test_board.py`)**

```python
# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBoard(TransactionCase):

    def _make_os(self):
        self._n += 1
        return self.env["afr.qualificacao.os"].create({"name": "OS-BD-%d" % self._n})

    def _make_visita(self, os, day, tec):
        return self.env["afr.qualificacao.os.visita"].create({
            "os_id": os.id, "tecnico_id": tec.id, "date": day,
        })

    def setUp(self):
        super().setUp()
        self.env.user.tz = "America/Sao_Paulo"
        self._n = 0
        self.t1 = self.env["hr.employee"].create({"name": "Ana"})
        self.t2 = self.env["hr.employee"].create({"name": "Bruno"})
        self.Visita = self.env["afr.qualificacao.os.visita"]

    def test_board_fetch_structure(self):
        os1 = self._make_os()
        self._make_visita(os1, date(2026, 6, 10), self.t1)
        self._make_visita(os1, date(2026, 6, 11), self.t2)
        data = self.Visita.board_fetch("2026-06-08", "2026-06-14")
        self.assertEqual({t["id"] for t in data["technicians"]},
                         {self.t1.id, self.t2.id})
        self.assertEqual(len(data["visitas"]), 2)
        keys = ("id", "tecnico_id", "date", "os_id", "os_name",
                "partner_name", "planned_hours", "state",
                "equipment_names", "conflict", "conflict_msg")
        for k in keys:
            self.assertIn(k, data["visitas"][0])

    def test_board_fetch_range(self):
        os1 = self._make_os()
        self._make_visita(os1, date(2026, 6, 10), self.t1)
        self._make_visita(os1, date(2026, 7, 1), self.t1)  # fora do range
        data = self.Visita.board_fetch("2026-06-08", "2026-06-14")
        self.assertEqual(len(data["visitas"]), 1)

    def test_board_fetch_conflict_flag(self):
        os1, os2 = self._make_os(), self._make_os()
        self._make_visita(os1, date(2026, 6, 10), self.t1)
        self._make_visita(os2, date(2026, 6, 10), self.t1)  # mesmo téc/dia
        data = self.Visita.board_fetch("2026-06-08", "2026-06-14")
        self.assertTrue(all(v["conflict"] for v in data["visitas"]))
        self.assertTrue(all(v["conflict_msg"] for v in data["visitas"]))

    def test_board_reschedule(self):
        os1 = self._make_os()
        v = self._make_visita(os1, date(2026, 6, 10), self.t1)
        self.Visita.board_reschedule(v.id, "2026-06-12", self.t2.id)
        self.assertEqual(v.date, date(2026, 6, 12))
        self.assertEqual(v.tecnico_id, self.t2)

    def test_board_reschedule_done_blocked(self):
        os1 = self._make_os()
        v = self._make_visita(os1, date(2026, 6, 10), self.t1)
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.board_reschedule(v.id, "2026-06-12", self.t2.id)
```

`tests/__init__.py` — adicione:
```python
from . import test_board
```

- [ ] **Step 2: Rodar e confirmar que falha**

`--test-tags /afr_qualificacao_agendamento:TestBoard`.
Esperado: FALHA — `AttributeError: ... has no attribute 'board_fetch'`.

- [ ] **Step 3: Implementar em `models/os_visita.py`**

Adicione à classe (métodos `@api.model`):
```python
    @api.model
    def board_fetch(self, date_from, date_to):
        """Dados do board: técnicos com visita no intervalo + visitas serializadas."""
        visitas = self.search([
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ], order="tecnico_id, date, sequence")
        techs = {}
        rows = []
        for v in visitas:
            if v.tecnico_id and v.tecnico_id.id not in techs:
                techs[v.tecnico_id.id] = v.tecnico_id.name
            msgs = [m for m in (
                v.tecnico_conflict_msg, v.travel_conflict_msg,
                v.instrument_conflict_msg, v.calibration_conflict_msg,
            ) if m]
            rows.append({
                "id": v.id,
                "tecnico_id": v.tecnico_id.id or False,
                "date": fields.Date.to_string(v.date),
                "os_id": v.os_id.id or False,
                "os_name": v.os_id.name or "",
                "partner_name": v.partner_id.name or "",
                "planned_hours": v.planned_hours,
                "state": v.state,
                "equipment_names": ", ".join(v.equipment_ids.mapped("name")),
                "conflict": bool(
                    v.tecnico_conflict or v.travel_conflict
                    or v.instrument_conflict or v.calibration_conflict
                ),
                "conflict_msg": " | ".join(msgs),
            })
        technicians = [
            {"id": tid, "name": name}
            for tid, name in sorted(techs.items(), key=lambda x: (x[1] or ""))
        ]
        return {"technicians": technicians, "visitas": rows}

    @api.model
    def board_reschedule(self, visita_id, new_date, new_tecnico_id):
        """Drag-reschedule: grava nova data + técnico. Bloqueia visita realizada."""
        visita = self.browse(visita_id)
        if visita.state == "done":
            raise UserError(_(
                "Não é possível reagendar uma visita já realizada."
            ))
        visita.write({"date": new_date, "tecnico_id": new_tecnico_id})
        return True
```
(`_`, `api`, `fields`, `models`, `UserError` já importados.)

- [ ] **Step 4: Rodar e confirmar que passa**

`--test-tags /afr_qualificacao_agendamento:TestBoard`.
Esperado: PASS (5 testes).

- [ ] **Step 5: Suíte completa (regressão)**

`--test-tags /afr_qualificacao_agendamento`.
Esperado: PASS (25 anteriores + 5 = 30). Não commitar.

---

## Task 2: Frontend OWL + action + menu + assets

**Files:**
- Create: `static/src/board/visita_board.js`, `.xml`, `.scss`
- Create: `views/visita_board_action.xml`
- Modify: `__manifest__.py`

> UI; validação = `-u` carrega sem erro de asset/XML + abrir o menu "Quadro de Agenda" no navegador (8083) e testar drag/clique manualmente.

- [ ] **Step 1: Criar `static/src/board/visita_board.js`**

```javascript
/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function isoDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}
function parseISO(s) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
}
function addDays(s, n) {
    const d = parseISO(s);
    d.setDate(d.getDate() + n);
    return isoDate(d);
}
function startOfWeek(date) {
    const x = new Date(date);
    const dow = (x.getDay() + 6) % 7; // segunda = 0
    x.setDate(x.getDate() - dow);
    return x;
}

export class VisitaBoard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const monday = startOfWeek(new Date());
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        this.state = useState({
            date_from: isoDate(monday),
            date_to: isoDate(sunday),
            technicians: [],
            visitas: [],
        });
        onWillStart(() => this._fetch());
    }

    async _fetch() {
        const data = await this.orm.call(
            "afr.qualificacao.os.visita", "board_fetch",
            [this.state.date_from, this.state.date_to]
        );
        this.state.technicians = data.technicians;
        this.state.visitas = data.visitas;
    }

    get days() {
        const out = [];
        let cur = this.state.date_from;
        let guard = 0;
        while (cur <= this.state.date_to && guard < 366) {
            out.push(cur);
            cur = addDays(cur, 1);
            guard++;
        }
        return out;
    }

    _span() {
        return Math.round(
            (parseISO(this.state.date_to) - parseISO(this.state.date_from)) / 86400000
        ) + 1;
    }

    cellVisitas(tecnicoId, day) {
        return this.state.visitas.filter(
            (v) => v.tecnico_id === tecnicoId && v.date === day
        );
    }

    colorClass(osId) {
        return "o_vb_color_" + (((osId || 0) % 8) + 1);
    }

    dayLabel(day) {
        return parseISO(day).toLocaleDateString(undefined, {
            weekday: "short", day: "2-digit", month: "2-digit",
        });
    }

    barTitle(v) {
        let t = `${v.os_name} · ${v.partner_name} · ${v.planned_hours}h`;
        if (v.equipment_names) {
            t += ` · ${v.equipment_names}`;
        }
        if (v.conflict && v.conflict_msg) {
            t += ` · ⚠ ${v.conflict_msg}`;
        }
        return t;
    }

    async prevRange() {
        const span = this._span();
        this.state.date_from = addDays(this.state.date_from, -span);
        this.state.date_to = addDays(this.state.date_to, -span);
        await this._fetch();
    }
    async nextRange() {
        const span = this._span();
        this.state.date_from = addDays(this.state.date_from, span);
        this.state.date_to = addDays(this.state.date_to, span);
        await this._fetch();
    }
    async today() {
        const monday = startOfWeek(new Date());
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        this.state.date_from = isoDate(monday);
        this.state.date_to = isoDate(sunday);
        await this._fetch();
    }
    async onChangeFrom(ev) { this.state.date_from = ev.target.value; await this._fetch(); }
    async onChangeTo(ev) { this.state.date_to = ev.target.value; await this._fetch(); }

    onDragStart(ev, visitaId) {
        ev.dataTransfer.setData("text/plain", String(visitaId));
        ev.dataTransfer.effectAllowed = "move";
    }
    onDragOver(ev) { ev.preventDefault(); ev.dataTransfer.dropEffect = "move"; }
    async onDrop(ev, tecnicoId, day) {
        ev.preventDefault();
        const visitaId = parseInt(ev.dataTransfer.getData("text/plain"), 10);
        if (!visitaId) { return; }
        await this.orm.call(
            "afr.qualificacao.os.visita", "board_reschedule",
            [visitaId, day, tecnicoId]
        );
        await this._fetch();
    }

    openVisita(visitaId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "afr.qualificacao.os.visita",
            res_id: visitaId,
            views: [[false, "form"]],
            target: "new",
        });
    }
}
VisitaBoard.template = "afr_qualificacao_agendamento.VisitaBoard";
registry.category("actions").add("afr_qualif_visita_board", VisitaBoard);
```

- [ ] **Step 2: Criar `static/src/board/visita_board.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<templates xml:space="preserve">
    <t t-name="afr_qualificacao_agendamento.VisitaBoard" owl="1">
        <div class="o_vb_board">
            <div class="o_vb_toolbar">
                <button class="btn btn-secondary" t-on-click="prevRange">‹</button>
                <button class="btn btn-secondary" t-on-click="today">Hoje</button>
                <button class="btn btn-secondary" t-on-click="nextRange">›</button>
                <input type="date" class="o_vb_date" t-att-value="state.date_from"
                       t-on-change="onChangeFrom"/>
                <span class="o_vb_sep">até</span>
                <input type="date" class="o_vb_date" t-att-value="state.date_to"
                       t-on-change="onChangeTo"/>
            </div>
            <div class="o_vb_grid_wrap">
                <table class="o_vb_grid">
                    <thead>
                        <tr>
                            <th class="o_vb_corner">Técnico</th>
                            <th t-foreach="days" t-as="day" t-key="day">
                                <t t-esc="dayLabel(day)"/>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr t-if="!state.technicians.length">
                            <td t-att-colspan="days.length + 1" class="o_vb_empty">
                                Sem visitas no intervalo.
                            </td>
                        </tr>
                        <tr t-foreach="state.technicians" t-as="tec" t-key="tec.id">
                            <td class="o_vb_tec"><t t-esc="tec.name"/></td>
                            <td t-foreach="days" t-as="day" t-key="day"
                                class="o_vb_cell"
                                t-on-dragover="onDragOver"
                                t-on-drop="(ev) => this.onDrop(ev, tec.id, day)">
                                <div t-foreach="cellVisitas(tec.id, day)" t-as="v" t-key="v.id"
                                     class="o_vb_bar"
                                     t-att-class="colorClass(v.os_id) + (v.conflict ? ' o_vb_conflict' : '') + (v.state === 'done' ? ' o_vb_done' : '')"
                                     draggable="true"
                                     t-on-dragstart="(ev) => this.onDragStart(ev, v.id)"
                                     t-on-click="() => this.openVisita(v.id)"
                                     t-att-title="barTitle(v)">
                                    <span class="o_vb_bar_os" t-esc="v.os_name"/>
                                    <span class="o_vb_bar_partner" t-esc="v.partner_name"/>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </t>
</templates>
```

- [ ] **Step 3: Criar `static/src/board/visita_board.scss`**

```scss
.o_vb_board {
    padding: 12px;
    height: 100%;
    overflow: auto;

    .o_vb_toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;

        .o_vb_sep { color: #6c757d; }
        .o_vb_date { max-width: 160px; }
    }

    .o_vb_grid_wrap { overflow-x: auto; }

    table.o_vb_grid {
        border-collapse: collapse;
        width: 100%;

        th, td {
            border: 1px solid #dee2e6;
            padding: 4px;
            vertical-align: top;
            min-width: 110px;
        }
        th { background: #f8f9fa; text-align: center; font-size: 12px; }
        .o_vb_corner, .o_vb_tec {
            position: sticky;
            left: 0;
            background: #f8f9fa;
            min-width: 140px;
            font-weight: 600;
            z-index: 1;
        }
        .o_vb_cell { height: 56px; }
        .o_vb_empty { text-align: center; color: #6c757d; padding: 24px; }
    }

    .o_vb_bar {
        display: flex;
        flex-direction: column;
        border-radius: 4px;
        padding: 2px 6px;
        margin-bottom: 3px;
        cursor: grab;
        color: #fff;
        font-size: 11px;
        line-height: 1.2;

        .o_vb_bar_os { font-weight: 600; }
        .o_vb_bar_partner { opacity: .85; }

        &:active { cursor: grabbing; }
        &.o_vb_done { opacity: .55; }
        &.o_vb_conflict {
            outline: 2px solid #dc3545;
            outline-offset: -2px;
        }
    }

    // paleta de 8 cores por OS
    .o_vb_color_1 { background: #1f77b4; }
    .o_vb_color_2 { background: #2ca02c; }
    .o_vb_color_3 { background: #9467bd; }
    .o_vb_color_4 { background: #ff7f0e; }
    .o_vb_color_5 { background: #17a2b8; }
    .o_vb_color_6 { background: #e377c2; }
    .o_vb_color_7 { background: #8c564b; }
    .o_vb_color_8 { background: #7f7f7f; }
}
```

- [ ] **Step 4: Criar `views/visita_board_action.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_visita_board" model="ir.actions.client">
        <field name="name">Quadro de Agenda</field>
        <field name="tag">afr_qualif_visita_board</field>
    </record>

    <menuitem id="menu_visita_board"
              name="Quadro de Agenda"
              parent="afr_qualificacao.menu_afr_qualificacao_root"
              action="action_visita_board"
              sequence="8"/>
</odoo>
```

- [ ] **Step 5: Atualizar `__manifest__.py`**

(a) Adicione `views/visita_board_action.xml` ao `data` (após as outras views):
```python
        "views/visita_board_action.xml",
```
(b) Adicione a chave `assets` (irmã de `data`, não dentro dela):
```python
    "assets": {
        "web.assets_backend": [
            "afr_qualificacao_agendamento/static/src/board/visita_board.scss",
            "afr_qualificacao_agendamento/static/src/board/visita_board.xml",
            "afr_qualificacao_agendamento/static/src/board/visita_board.js",
        ],
    },
```

- [ ] **Step 6: Atualizar e validar**

```
docker exec odoo_engenapp-web-1 odoo -d odoo_ecm_test --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --no-http --workers=0 -u afr_qualificacao_agendamento --test-enable --test-tags /afr_qualificacao_agendamento --stop-after-init
```
Esperado: carrega sem erro (action client + assets registrados); 30 testes PASS. (O JS não roda em `--stop-after-init`; validação visual é manual.)

Validação manual (navegador 8083): menu **Qualificações → Quadro de Agenda** → grade técnico×dia; arrastar visita p/ outra célula → reagenda; clicar → abre form; conflito → barra com contorno vermelho; date pickers + ‹ › Hoje navegam.

---

## Self-Review (cobertura do spec Fase D)

| Requisito do spec | Task |
|---|---|
| `board_fetch(date_from, date_to)` estrutura + range + conflito | Task 1 |
| `board_reschedule` grava data+técnico; bloqueia done | Task 1 |
| Client action OWL técnico×dia | Task 2 (js+xml) |
| Cor por OS + destaque conflito + done | Task 2 (scss + template classes) |
| Drag (data+técnico) → board_reschedule → refetch | Task 2 (onDrop) |
| Clique → form da visita | Task 2 (openVisita) |
| Intervalo configurável + ‹ › Hoje | Task 2 (toolbar + nav) |
| Menu "Quadro de Agenda" | Task 2 (visita_board_action.xml) |
| Assets web.assets_backend | Task 2 (manifest) |
| TDD backend; JS manual | Task 1 testes; Task 2 manual |

**Placeholder scan:** sem TBD/TODO.

**Type consistency:** `board_fetch`/`board_reschedule` (Python) ↔ `orm.call(... "board_fetch"/"board_reschedule" ...)` (JS); template `afr_qualificacao_agendamento.VisitaBoard` ↔ `VisitaBoard.template`; tag `afr_qualif_visita_board` ↔ `registry.actions.add` ↔ `ir.actions.client.tag`. Classes CSS `o_vb_color_1..8` ↔ `colorClass` (`%8 + 1`). Campos lidos no `board_fetch` existem no modelo (Fases A-C).

**Riscos:** JS sem teste automatizado (validação manual); drag-drop HTML5 manual; `colorClass` usa `os_id % 8 + 1` (1..8) casando com a paleta scss.
