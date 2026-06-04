# Fase C — Conflito de Recurso e Calibração — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detectar (não-bloqueante) conflito de instrumento metrológico duplo-alocado entre OSes e calibração vencida na data da visita, com instrumentos atribuídos manualmente por visita (+ botão "Puxar do plano F10").

**Architecture:** Estende `afr.qualificacao.os.visita` (satélite) com `instrument_ids` (M2m stored), 4 campos de conflito computados (não-stored, padrão Fases A/B), método `_compute_resource_conflicts`, helper `_instrument_valid_on`, e ação `action_pull_instruments_from_plan`. Views ganham o campo, o botão, 2 alertas e a decoração. Zero mudança no submodule pai.

**Tech Stack:** Odoo 16.0 Community, Python, XML, `TransactionCase`.

**Referências (campos reais confirmados):**
- `engc.calibration.instruments`: `name` (Char), `certificate_ids` (O2m → `engc.calibration.instruments.certificates`). Sem campos required.
- `engc.calibration.instruments.certificates`: `instrument_id` (M2o, **required**), `validate_calibration` (Date, validade).
- `afr.qualificacao.resource.plan.line`: `os_id` (required), `resource_role` (required; valores `validador`/`padrao`), `instrument_id` (M2o), `equipment_ids` (M2m).
- `afr.qualificacao.os.resource_plan_line_ids` (O2m das linhas do plano).
- Visita (Fase A/B): `os_id`, `equipment_ids`, `date`, `date_start`, `date_stop`, padrão `_compute_conflicts` em `os_visita.py`.
- Spec: `afr_qualificacao_agendamento/docs/superpowers/specs/2026-06-03-fase-c-conflito-recurso-design.md`.

**Testes:** container `odoo_engenapp-web-1`, DB `odoo_ecm_test`:
```
docker exec odoo_engenapp-web-1 odoo -d odoo_ecm_test --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --no-http --workers=0 -u afr_qualificacao_agendamento --test-enable --test-tags /afr_qualificacao_agendamento:TestResourceConflict --stop-after-init
```
(NÃO commitar durante a execução.)

---

## Estrutura de arquivos

```
afr_qualificacao_agendamento/
├── models/os_visita.py                  # MODIFY: + instrument_ids, 4 campos conflito, _compute_resource_conflicts, _instrument_valid_on, action_pull_instruments_from_plan
├── views/os_visita_views.xml            # MODIFY: form (campo+botão+2 alertas+invisible) e tree (decoração+coluna+invisible)
├── views/qualificacao_os_views.xml      # MODIFY: tree embed na OS (decoração + invisible)
└── tests/test_resource_conflict.py      # CREATE: TestResourceConflict
└── tests/__init__.py                    # MODIFY: + test_resource_conflict
```

---

## Task 1: Modelo — instrumentos, conflitos, pull-from-plan

**Files:**
- Modify: `models/os_visita.py`
- Create: `tests/test_resource_conflict.py`
- Modify: `tests/__init__.py`

- [ ] **Step 1: Escrever os testes que falham (`tests/test_resource_conflict.py`)**

```python
# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceConflict(TransactionCase):

    def _make_equipment(self, city):
        partner = self.env["res.partner"].create({"name": "Cli " + city, "city": city})
        return self.env["engc.equipment"].create({
            "name": "Equip " + city, "category_id": self.cat.id,
            "marca_id": self.marca.id, "model": "M1",
            "serial_number": "SN-" + city, "client_id": partner.id,
        })

    def _make_instrument(self, name, valid_until=None):
        inst = self.env["engc.calibration.instruments"].create({"name": name})
        if valid_until:
            self.env["engc.calibration.instruments.certificates"].create({
                "instrument_id": inst.id, "validate_calibration": valid_until,
            })
        return inst

    def _make_os(self):
        self._n += 1
        return self.env["afr.qualificacao.os"].create({"name": "OS-RC-%d" % self._n})

    def _make_visita(self, os, day, instruments=None):
        return self.env["afr.qualificacao.os.visita"].create({
            "os_id": os.id, "tecnico_id": self.emp.id, "date": day,
            "instrument_ids": [(6, 0, [i.id for i in (instruments or [])])],
        })

    def setUp(self):
        super().setUp()
        self.env.user.tz = "America/Sao_Paulo"
        self._n = 0
        self.cat = self.env["engc.equipment.category"].create({"name": "Cat"})
        self.marca = self.env["engc.equipment.marca"].create({"name": "Marca"})
        self.emp = self.env["hr.employee"].create({"name": "Téc 1"})

    def test_instrument_conflict_overlap(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        os1, os2 = self._make_os(), self._make_os()
        v1 = self._make_visita(os1, date(2026, 6, 10), [inst])
        v2 = self._make_visita(os2, date(2026, 6, 10), [inst])
        self.assertTrue(v1.instrument_conflict)
        self.assertTrue(v2.instrument_conflict)

    def test_no_instrument_conflict_diff_dates(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        os1, os2 = self._make_os(), self._make_os()
        self._make_visita(os1, date(2026, 6, 10), [inst])
        v2 = self._make_visita(os2, date(2026, 6, 12), [inst])
        self.assertFalse(v2.instrument_conflict)

    def test_no_instrument_conflict_same_os(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        os1 = self._make_os()
        v1 = self._make_visita(os1, date(2026, 6, 10), [inst])
        v2 = self._make_visita(os1, date(2026, 6, 10), [inst])
        self.assertFalse(v1.instrument_conflict)
        self.assertFalse(v2.instrument_conflict)

    def test_calibration_expired(self):
        inst = self._make_instrument("Logger A", date(2026, 1, 1))  # vencido antes de jun/26
        v = self._make_visita(self._make_os(), date(2026, 6, 10), [inst])
        self.assertTrue(v.calibration_conflict)

    def test_calibration_valid(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        v = self._make_visita(self._make_os(), date(2026, 6, 10), [inst])
        self.assertFalse(v.calibration_conflict)

    def test_calibration_no_certificate(self):
        inst = self._make_instrument("Logger A")  # sem certificado
        v = self._make_visita(self._make_os(), date(2026, 6, 10), [inst])
        self.assertTrue(v.calibration_conflict)

    def test_pull_instruments_from_plan(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        equip = self._make_equipment("São Paulo")
        os1 = self._make_os()
        self.env["afr.qualificacao.resource.plan.line"].create({
            "os_id": os1.id, "resource_role": "validador",
            "instrument_id": inst.id, "equipment_ids": [(6, 0, [equip.id])],
        })
        v = self._make_visita(os1, date(2026, 6, 10))
        v.equipment_ids = [(6, 0, [equip.id])]
        v.action_pull_instruments_from_plan()
        self.assertEqual(v.instrument_ids, inst)
```

`tests/__init__.py` — adicione:
```python
from . import test_resource_conflict
```

- [ ] **Step 2: Rodar e confirmar que falha**

`--test-tags /afr_qualificacao_agendamento:TestResourceConflict`.
Esperado: FALHA — `ValueError: Invalid field 'instrument_ids' on model 'afr.qualificacao.os.visita'` (campo ainda não existe).

- [ ] **Step 3: Implementar em `models/os_visita.py`**

Adicione os campos (junto aos demais campos do modelo, perto de `equipment_ids`):
```python
    instrument_ids = fields.Many2many(
        "engc.calibration.instruments",
        "afr_visita_instrument_rel", "visita_id", "instrument_id",
        string="Instrumentos (validador/padrão)",
        help="Instrumentos metrológicos usados nesta visita (atribuição manual).",
    )
    instrument_conflict = fields.Boolean(
        string="Conflito de instrumento", compute="_compute_resource_conflicts"
    )
    instrument_conflict_msg = fields.Char(compute="_compute_resource_conflicts")
    calibration_conflict = fields.Boolean(
        string="Calibração vencida", compute="_compute_resource_conflicts"
    )
    calibration_conflict_msg = fields.Char(compute="_compute_resource_conflicts")
```

Adicione os métodos à classe:
```python
    def _instrument_valid_on(self, instrument, day):
        """True se o instrumento tem certificado válido na data `day`."""
        return any(
            c.validate_calibration and c.validate_calibration >= day
            for c in instrument.certificate_ids
        )

    @api.depends("instrument_ids", "date", "date_start", "date_stop")
    def _compute_resource_conflicts(self):
        for r in self:
            r.instrument_conflict = False
            r.instrument_conflict_msg = False
            r.calibration_conflict = False
            r.calibration_conflict_msg = False
            if not r.instrument_ids:
                continue
            # Conflito de recurso: instrumento em OS diferente, janela sobreposta.
            if r.date_start and r.date_stop:
                exclude = [("id", "!=", r._origin.id)] if r._origin.id else []
                clash = self.search(exclude + [
                    ("os_id", "!=", r.os_id.id),
                    ("instrument_ids", "in", r.instrument_ids.ids),
                    ("date_start", "<", r.date_stop),
                    ("date_stop", ">", r.date_start),
                ], limit=1)
                if clash:
                    shared = clash.instrument_ids & r.instrument_ids
                    r.instrument_conflict = True
                    r.instrument_conflict_msg = _(
                        "Instrumento(s) %s já em uso na OS %s no período."
                    ) % (", ".join(shared.mapped("display_name")),
                         clash.os_id.name or _("(sem OS)"))
            # Conflito de calibração: instrumento sem certificado válido na data.
            if r.date:
                expired = r.instrument_ids.filtered(
                    lambda inst: not r._instrument_valid_on(inst, r.date)
                )
                if expired:
                    r.calibration_conflict = True
                    r.calibration_conflict_msg = _(
                        "Calibração vencida/ausente em: %s (data %s)."
                    ) % (", ".join(expired.mapped("display_name")),
                         fields.Date.to_string(r.date))

    def action_pull_instruments_from_plan(self):
        """Pré-preenche instrument_ids a partir do plano de recursos (F10) da OS,
        pelas linhas cujos equipamentos batem com os da visita."""
        self.ensure_one()
        lines = self.os_id.resource_plan_line_ids.filtered(
            lambda l: l.instrument_id and (l.equipment_ids & self.equipment_ids)
        )
        self.instrument_ids = [(6, 0, lines.mapped("instrument_id").ids)]
        return True
```
(`_`, `api`, `fields`, `models` já importados da Fase A.)

- [ ] **Step 4: Rodar e confirmar que passa**

`--test-tags /afr_qualificacao_agendamento:TestResourceConflict`.
Esperado: PASS (7 testes).

- [ ] **Step 5: Suíte completa do módulo (regressão A/B)**

`--test-tags /afr_qualificacao_agendamento`.
Esperado: PASS (18 anteriores + 7 = 25). Não commitar.

---

## Task 2: Views (campo, botão, alertas, decoração)

**Files:**
- Modify: `views/os_visita_views.xml`
- Modify: `views/qualificacao_os_views.xml`

> UI; validação = `-u` carrega sem erro + testes do módulo verdes.

- [ ] **Step 1: Form da visita (`views/os_visita_views.xml`, record `view_os_visita_form`)**

(a) Após os 2 blocos de alerta existentes (técnico/deslocamento), adicione 2 alertas:
```xml
                    <div class="alert alert-warning" role="alert"
                         attrs="{'invisible': [('instrument_conflict', '=', False)]}">
                        <field name="instrument_conflict_msg" nolabel="1"/>
                    </div>
                    <div class="alert alert-warning" role="alert"
                         attrs="{'invisible': [('calibration_conflict', '=', False)]}">
                        <field name="calibration_conflict_msg" nolabel="1"/>
                    </div>
```

(b) No grupo "Equipamentos", após `equipment_ids`, adicione o campo + botão:
```xml
                    <group string="Instrumentos">
                        <field name="instrument_ids" widget="many2many_tags" nolabel="1"/>
                        <button name="action_pull_instruments_from_plan" type="object"
                                string="Puxar do plano F10" class="btn-link"/>
                    </group>
```

(c) Junto aos campos invisíveis existentes (`tecnico_conflict`/`travel_conflict` invisible="1"), acrescente:
```xml
                    <field name="instrument_conflict" invisible="1"/>
                    <field name="calibration_conflict" invisible="1"/>
```

- [ ] **Step 2: Tree da visita (`views/os_visita_views.xml`, record `view_os_visita_tree`)**

(a) Estenda a decoração:
```xml
            <tree decoration-danger="tecnico_conflict or travel_conflict or instrument_conflict or calibration_conflict">
```
(b) Adicione a coluna (após `equipment_ids`):
```xml
                <field name="instrument_ids" widget="many2many_tags" optional="hide"/>
```
(c) Adicione os campos invisíveis (junto aos existentes):
```xml
                <field name="instrument_conflict" invisible="1"/>
                <field name="calibration_conflict" invisible="1"/>
```

- [ ] **Step 3: Tree embed na OS (`views/qualificacao_os_views.xml`, dentro da página "Visitas")**

(a) Estenda a decoração do `<tree editable="bottom" ...>`:
```xml
                        <tree editable="bottom"
                              decoration-danger="tecnico_conflict or travel_conflict or instrument_conflict or calibration_conflict">
```
(b) Acrescente os campos invisíveis junto aos existentes:
```xml
                            <field name="instrument_conflict" invisible="1"/>
                            <field name="calibration_conflict" invisible="1"/>
```

- [ ] **Step 4: Atualizar e validar**

```
docker exec odoo_engenapp-web-1 odoo -d odoo_ecm_test --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --no-http --workers=0 -u afr_qualificacao_agendamento --test-enable --test-tags /afr_qualificacao_agendamento --stop-after-init
```
Esperado: carrega sem ParseError; 25 testes PASS. Não commitar.

No navegador (8083): visita → campo "Instrumentos" + botão "Puxar do plano F10"; instrumento com calibração vencida ou duplo-alocado → linha vermelha + alerta.

---

## Self-Review (cobertura do spec Fase C)

| Requisito do spec | Task |
|---|---|
| `instrument_ids` M2m manual (stored) | Task 1 |
| Conflito de recurso (OS diferente, janela sobreposta, exclui mesma OS) | Task 1 (test_overlap, diff_dates, same_os) |
| Conflito de calibração (validate_calibration >= data; sem cert = vencido) | Task 1 (expired, valid, no_certificate) |
| `action_pull_instruments_from_plan` | Task 1 (test_pull) |
| Não-bloqueante (alertas + decoração) | Task 2 |
| Campo + botão + coluna nas views | Task 2 |
| Zero mudança no submodule pai | (todas — só satélite) |
| Sem novo `ir.model.access` (modelo existente) | (nenhum modelo novo) |

**Placeholder scan:** sem TBD/TODO.

**Type consistency:** `instrument_ids`, `instrument_conflict(_msg)`, `calibration_conflict(_msg)`, `_compute_resource_conflicts`, `_instrument_valid_on`, `action_pull_instruments_from_plan`, relation `afr_visita_instrument_rel` — consistentes entre tasks. Campo `validate_calibration` e `certificate_ids` confirmados no modelo real.

**Nota:** conflito de recurso não filtra estado da OS (consistente com Fases A/B); refinamento futuro possível.
