# Agendamento de Visitas (Fase A) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o módulo satélite `afr_qualificacao_agendamento` com a fundação do agendamento de visitas de campo: modelo `afr.qualificacao.os.visita` (OS × dia × técnico), rollup das datas planejadas da OS, gate de agendamento por visita, detecção de conflito de técnico e de deslocamento, e views (tree/form/calendar) com a calendar nativa de agenda.

**Architecture:** Módulo novo `depends: ['afr_qualificacao']`. Tudo é adição pura, exceto o único acoplamento invasivo (opção X): redefinir `afr.qualificacao.os.date_planned_start/end` como `computed store` rollup das visitas, via `_inherit`. Conflitos são avisos **não-bloqueantes** (campo computed + decoração + alerta no form). Datetimes da visita são derivados de `date` + horas opcionais, convertidos local→UTC.

**Tech Stack:** Odoo 16.0 Community, Python, `pytz`, XML views (tree/form/calendar/search), `odoo.tests.common.TransactionCase`.

**Referências do código existente:**
- OS: `addons/afr_qualificacao/models/qualificacao_os.py` — `action_schedule` em `:314-335`; campos `date_planned_start/end` em `:75-82`; `_compute_partner_id` em `:226-229` (partner = 1ª qualificação).
- Form da OS a herdar: xmlid `afr_qualificacao.view_afr_qualificacao_os_form`, `button_box` com `name="button_box"`.
- `afr.qualificacao` requer: `equipment_id` (engc.equipment), `qualification_type` (default `installation`); `partner_id` deriva de `equipment_id.client_id`.
- `engc.equipment` requer: `category_id`, `marca_id`, `model`, `serial_number` (state default `in_use`, company default).

**Execução dos testes (convenção do projeto):** rodar via subagente `test-runner` (model sonnet) com `test-tags /afr_qualificacao_agendamento`. Container: `odoo_engenapp-web-1` (porta host 8083). **Não** usar `odoo-bin` direto (entrypoint custom intercepta args `-*`). Primeiro install do módulo: o agente usa `-i afr_qualificacao_agendamento`; reinstalações `-u afr_qualificacao_agendamento`.

---

## Estrutura de arquivos

```
addons/afr_qualificacao_agendamento/
├── __init__.py                       # from . import models
├── __manifest__.py                   # depends afr_qualificacao; data: security + 2 views
├── models/
│   ├── __init__.py                   # from . import os_visita, qualificacao_os
│   ├── os_visita.py                  # NOVO modelo afr.qualificacao.os.visita
│   └── qualificacao_os.py            # _inherit: visita_ids + rollup (X) + action_schedule
├── security/
│   └── ir.model.access.csv           # acesso ao novo modelo
├── views/
│   ├── os_visita_views.xml           # tree / form / calendar / search / action / menu
│   └── qualificacao_os_views.xml     # herda form da OS: stat button + aba Visitas
└── tests/
    ├── __init__.py                   # from . import test_visita
    └── test_visita.py                # TransactionCase
```

Responsabilidade por arquivo: `os_visita.py` = o registro agendável e toda a lógica de derivação de datetime + conflito; `qualificacao_os.py` = só as extensões da OS (rollup, gate, contagem, ação). Views separadas por modelo. Testes num só arquivo (Fase A é pequena).

---

## Task 1: Esqueleto do módulo (instalável vazio)

**Files:**
- Create: `addons/afr_qualificacao_agendamento/__init__.py`
- Create: `addons/afr_qualificacao_agendamento/__manifest__.py`
- Create: `addons/afr_qualificacao_agendamento/models/__init__.py`
- Create: `addons/afr_qualificacao_agendamento/security/ir.model.access.csv`

- [ ] **Step 1: Criar `__manifest__.py`**

```python
# -*- coding: utf-8 -*-
{
    "name": "AFR Qualificação - Agendamento de Visitas",
    "version": "16.0.1.0.0",
    "category": "Services/Qualificação",
    "summary": "Agendamento de visitas de campo das OS de qualificação",
    "author": "AFR",
    "license": "LGPL-3",
    "depends": ["afr_qualificacao"],
    "data": [
        "security/ir.model.access.csv",
        # views/*.xml são adicionados na Task 6 (não existem antes disso —
        # listá-los aqui faria o -i/-u das Tasks 2-5 crashar com FileNotFoundError).
    ],
    "installable": True,
    "application": False,
}
```

- [ ] **Step 2: Criar `__init__.py` (raiz)**

```python
# -*- coding: utf-8 -*-
from . import models
```

- [ ] **Step 3: Criar `models/__init__.py`**

```python
# -*- coding: utf-8 -*-
from . import os_visita
from . import qualificacao_os
```

> NOTA: nas Tasks 2-3 os arquivos `os_visita.py` e `qualificacao_os.py` são criados. Até lá, o módulo não instala (import falha). A instalação é validada só ao fim da Task 3. Crie `models/os_visita.py` e `models/qualificacao_os.py` vazios com apenas `# -*- coding: utf-8 -*-` se quiser instalar antes (opcional).

- [ ] **Step 4: Criar `security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_afr_qualificacao_os_visita_user,afr.qualificacao.os.visita.user,model_afr_qualificacao_os_visita,base.group_user,1,1,1,1
```

- [ ] **Step 5: Commit**

```bash
cd /home/afonso/docker/odoo_engenapp/addons
git add afr_qualificacao_agendamento/__init__.py afr_qualificacao_agendamento/__manifest__.py afr_qualificacao_agendamento/models/__init__.py afr_qualificacao_agendamento/security/ir.model.access.csv
git commit -m "feat(agendamento): esqueleto do módulo afr_qualificacao_agendamento"
```

---

## Task 2: Modelo `afr.qualificacao.os.visita`

**Files:**
- Create/replace: `addons/afr_qualificacao_agendamento/models/os_visita.py`
- Create: `addons/afr_qualificacao_agendamento/tests/__init__.py`
- Create: `addons/afr_qualificacao_agendamento/tests/test_visita.py`

- [ ] **Step 1: Escrever o teste que falha (`tests/__init__.py` + `tests/test_visita.py`)**

`tests/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import test_visita
```

`tests/test_visita.py`:
```python
# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVisita(TransactionCase):

    def _make_equipment(self, city):
        partner = self.env["res.partner"].create({"name": "Cli " + city, "city": city})
        cat = self.env["engc.equipment.category"].create({"name": "Cat Teste"})
        marca = self.env["engc.equipment.marca"].create({"name": "Marca Teste"})
        return self.env["engc.equipment"].create({
            "name": "Equip " + city,
            "category_id": cat.id,
            "marca_id": marca.id,
            "model": "M1",
            "serial_number": "SN-" + city,
            "client_id": partner.id,
        })

    def _make_os(self, equipment):
        # name explícito = determinístico e imune ao unique(name, company_id);
        # passar name pula o ir.sequence do create() da OS.
        self._os_seq += 1
        os = self.env["afr.qualificacao.os"].create(
            {"name": "OS-TEST-%d" % self._os_seq}
        )
        self.env["afr.qualificacao"].create({
            "os_id": os.id,
            "equipment_id": equipment.id,
            "qualification_type": "installation",
        })
        return os

    def setUp(self):
        super().setUp()
        self._os_seq = 0
        self.emp = self.env["hr.employee"].create({"name": "Téc 1"})
        self.equip_sp = self._make_equipment("São Paulo")
        self.os = self._make_os(self.equip_sp)

    def test_datetimes_day_mode(self):
        """Sem horas: date_start no início e date_stop no fim do dia."""
        v = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id,
            "tecnico_id": self.emp.id,
            "date": date(2026, 6, 10),
        })
        self.assertTrue(v.date_start)
        self.assertTrue(v.date_stop)
        self.assertLess(v.date_start, v.date_stop)
        # date_stop deve cair no mesmo dia civil (margem de fuso)
        self.assertEqual(v.date_start.date(), date(2026, 6, 10))

    def test_name_compute(self):
        v = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id,
            "tecnico_id": self.emp.id,
            "date": date(2026, 6, 10),
        })
        self.assertIn("Téc 1", v.name)
        self.assertIn("2026-06-10", v.name)

    def test_related_city(self):
        v = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id,
            "tecnico_id": self.emp.id,
            "date": date(2026, 6, 10),
        })
        self.assertEqual(v.partner_id, self.equip_sp.client_id)
        self.assertEqual(v.city, "São Paulo")
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Via subagente `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita`.
Esperado: FALHA — `KeyError`/`ValueError` "Invalid model name 'afr.qualificacao.os.visita'" (modelo ainda não existe).

- [ ] **Step 3: Implementar o modelo (`models/os_visita.py`)**

```python
# -*- coding: utf-8 -*-
"""Visita de campo de uma OS de Qualificação (afr.qualificacao.os.visita).

Unidade agendável = OS × dia × técnico. Fase A: modelo base, datetimes
computados para a calendar, e detecção de conflito de técnico/deslocamento
(avisos não-bloqueantes — Task 5).
"""
from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import _, api, fields, models


class AfrQualificacaoOsVisita(models.Model):
    _name = "afr.qualificacao.os.visita"
    _description = "Visita de OS de Qualificação"
    _order = "date, time_start, id"

    name = fields.Char(string="Visita", compute="_compute_name", store=True)
    os_id = fields.Many2one(
        "afr.qualificacao.os",
        string="OS de Qualificação",
        required=True,
        ondelete="cascade",
        index=True,
    )
    tecnico_id = fields.Many2one(
        "hr.employee",
        string="Técnico",
        required=True,
        index=True,
        help="Técnico desta visita. Editável para reatribuir grupos paralelos.",
    )
    date = fields.Date(string="Data", required=True, index=True)
    time_start = fields.Float(
        string="Hora início", help="Opcional. Vazio = início do dia (00:00)."
    )
    time_stop = fields.Float(
        string="Hora fim", help="Opcional. Vazio = fim do dia (23:59)."
    )
    date_start = fields.Datetime(
        string="Início",
        compute="_compute_datetimes",
        store=True,
        help="date + time_start convertido p/ UTC (fonte da calendar).",
    )
    date_stop = fields.Datetime(
        string="Fim", compute="_compute_datetimes", store=True
    )
    equipment_ids = fields.Many2many(
        "engc.equipment",
        string="Equipamentos",
        help="Equipamentos trabalhados nesta visita.",
    )
    planned_hours = fields.Float(
        string="Horas previstas",
        help="Horas de trabalho previstas no dia (≤ jornada do equipamento).",
    )
    travel_buffer_hours = fields.Float(
        string="Deslocamento (h)",
        help="Tempo de deslocamento até esta visita (manual).",
    )
    partner_id = fields.Many2one(
        related="os_id.partner_id", string="Cliente", store=True, readonly=True
    )
    city = fields.Char(
        related="partner_id.city", string="Cidade", store=True, readonly=True
    )
    company_id = fields.Many2one(
        related="os_id.company_id", store=True, readonly=True
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [("planned", "Planejada"), ("done", "Realizada")],
        default="planned",
        required=True,
    )
    note = fields.Text(string="Observações")

    # Campos de conflito — implementados na Task 5
    tecnico_conflict = fields.Boolean(
        string="Conflito de técnico", compute="_compute_conflicts"
    )
    tecnico_conflict_msg = fields.Char(compute="_compute_conflicts")
    travel_conflict = fields.Boolean(
        string="Conflito de deslocamento", compute="_compute_conflicts"
    )
    travel_conflict_msg = fields.Char(compute="_compute_conflicts")

    # ───────── helpers ─────────
    def _local_to_utc(self, naive_dt):
        """Datetime naive local (tz do usuário) → naive UTC p/ armazenar."""
        tz = timezone(self.env.user.tz or "UTC")
        return tz.localize(naive_dt).astimezone(utc).replace(tzinfo=None)

    @api.depends("os_id.name", "date", "tecnico_id")
    def _compute_name(self):
        for r in self:
            parts = []
            if r.os_id.name:
                parts.append(r.os_id.name)
            if r.date:
                parts.append(fields.Date.to_string(r.date))
            if r.tecnico_id:
                parts.append(r.tecnico_id.name)
            r.name = " / ".join(parts) or _("Visita")

    @api.depends("date", "time_start", "time_stop")
    def _compute_datetimes(self):
        for r in self:
            if not r.date:
                r.date_start = r.date_stop = False
                continue
            base = datetime.combine(r.date, time.min)
            start_h = r.time_start or 0.0
            stop_h = r.time_stop if r.time_stop else 23.9833  # ~23:59
            r.date_start = r._local_to_utc(base + timedelta(hours=start_h))
            r.date_stop = r._local_to_utc(base + timedelta(hours=stop_h))

    # Implementado na Task 5 (placeholder mínimo p/ o modelo carregar agora).
    @api.depends("tecnico_id", "date_start", "date_stop", "city",
                 "travel_buffer_hours")
    def _compute_conflicts(self):
        for r in self:
            r.tecnico_conflict = False
            r.tecnico_conflict_msg = False
            r.travel_conflict = False
            r.travel_conflict_msg = False
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita`. (Primeiro run instala o módulo com `-i`.)
Esperado: PASS (3 testes: `test_datetimes_day_mode`, `test_name_compute`, `test_related_city`).

- [ ] **Step 5: Commit**

```bash
cd /home/afonso/docker/odoo_engenapp/addons
git add afr_qualificacao_agendamento/models/os_visita.py afr_qualificacao_agendamento/tests/
git commit -m "feat(agendamento): modelo afr.qualificacao.os.visita + datetimes"
```

---

## Task 3: OS — `visita_ids`, rollup das datas (opção X), contagem

**Files:**
- Create/replace: `addons/afr_qualificacao_agendamento/models/qualificacao_os.py`
- Modify: `addons/afr_qualificacao_agendamento/tests/test_visita.py` (adicionar testes)

- [ ] **Step 1: Adicionar o teste que falha em `tests/test_visita.py`**

Acrescente ao final da classe `TestVisita`:
```python
    def test_rollup_planned_dates(self):
        """date_planned_start/end da OS = min/max das visitas."""
        V = self.env["afr.qualificacao.os.visita"]
        v1 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 10)})
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 12)})
        self.assertEqual(self.os.date_planned_start, v1.date_start)
        self.assertEqual(self.os.date_planned_end, v2.date_stop)
        self.assertEqual(self.os.visita_count, 2)

    def test_rollup_empty(self):
        """Sem visitas: datas planejadas vazias."""
        self.assertFalse(self.os.date_planned_start)
        self.assertFalse(self.os.date_planned_end)
        self.assertEqual(self.os.visita_count, 0)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita.test_rollup_planned_dates`.
Esperado: FALHA — `AttributeError`/`ValueError` em `visita_count` (campo não existe) e datas planejadas não atualizam.

- [ ] **Step 3: Implementar `models/qualificacao_os.py`**

```python
# -*- coding: utf-8 -*-
"""Extensões da OS de Qualificação para o agendamento de visitas.

Adiciona visita_ids; transforma date_planned_start/end em rollup das visitas
(opção X — redefinição de campo herdado como computed store); expõe contagem
e ação de visitas. O gate do action_schedule fica na Task 4.
"""
from odoo import api, fields, models


class AfrQualificacaoOs(models.Model):
    _inherit = "afr.qualificacao.os"

    visita_ids = fields.One2many(
        "afr.qualificacao.os.visita", "os_id", string="Visitas"
    )
    visita_count = fields.Integer(
        string="Nº de visitas", compute="_compute_visita_count"
    )

    # Opção X: rollup — redefine campos herdados como computed store.
    date_planned_start = fields.Datetime(
        compute="_compute_planned_dates_rollup",
        store=True,
        readonly=True,
        tracking=True,
    )
    date_planned_end = fields.Datetime(
        compute="_compute_planned_dates_rollup",
        store=True,
        readonly=True,
        tracking=True,
    )

    @api.depends("visita_ids.date_start", "visita_ids.date_stop")
    def _compute_planned_dates_rollup(self):
        for r in self:
            starts = [d for d in r.visita_ids.mapped("date_start") if d]
            stops = [d for d in r.visita_ids.mapped("date_stop") if d]
            r.date_planned_start = min(starts) if starts else False
            r.date_planned_end = max(stops) if stops else False

    @api.depends("visita_ids")
    def _compute_visita_count(self):
        for r in self:
            r.visita_count = len(r.visita_ids)

    def action_view_visitas(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Visitas",
            "res_model": "afr.qualificacao.os.visita",
            "view_mode": "calendar,tree,form",
            "domain": [("os_id", "=", self.id)],
            "context": {
                "default_os_id": self.id,
                "default_tecnico_id": self.tecnico_default_id.id,
            },
        }
```

- [ ] **Step 4: Rodar e confirmar que passa**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita` (com `-u afr_qualificacao_agendamento` para aplicar a redefinição de campo).
Esperado: PASS (5 testes).

- [ ] **Step 5: Commit**

```bash
cd /home/afonso/docker/odoo_engenapp/addons
git add afr_qualificacao_agendamento/models/qualificacao_os.py afr_qualificacao_agendamento/tests/test_visita.py
git commit -m "feat(agendamento): OS visita_ids + rollup datas planejadas (opção X)"
```

---

## Task 4: Gate do `action_schedule` (exige ≥1 visita)

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/qualificacao_os.py`
- Modify: `addons/afr_qualificacao_agendamento/tests/test_visita.py`

- [ ] **Step 1: Adicionar o teste que falha**

Acrescente à classe `TestVisita`:
```python
    def test_schedule_requires_visita(self):
        """Sem visita, action_schedule levanta a mensagem específica do gate."""
        from odoo.exceptions import UserError
        self.os.tecnico_default_id = self.emp.id
        with self.assertRaisesRegex(UserError, "pelo menos uma visita"):
            self.os.action_schedule()

    def test_schedule_ok_with_visita(self):
        """Com ≥1 visita + técnico padrão: draft → scheduled (regressão)."""
        self.os.tecnico_default_id = self.emp.id
        self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id, "tecnico_id": self.emp.id,
            "date": date(2026, 6, 10),
        })
        self.os.action_schedule()
        self.assertEqual(self.os.state, "scheduled")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita.test_schedule_requires_visita`.
Esperado: FALHA — sem o override, o `super()` do pai levanta `UserError` com mensagem **"Preencha datas planejadas antes de agendar."** (datas vazias pelo rollup), que NÃO casa com o regex `"pelo menos uma visita"` → `assertRaisesRegex` falha. Isso prova que é o nosso gate, não o do pai, que precisa existir.

> Por que o regex: como `date_planned_*` agora derivam das visitas, "sem visita" ⟺ "sem datas". Um `assertRaises(UserError)` genérico passaria por acaso (o pai já levanta). O regex na mensagem do gate é o que força red→green. `test_schedule_ok_with_visita` é regressão (passa antes e depois — guarda o happy-path).

- [ ] **Step 3: Adicionar o override em `models/qualificacao_os.py`**

Acrescente os imports e o método à classe `AfrQualificacaoOs`:
```python
from odoo import _, api, fields, models
from odoo.exceptions import UserError
```
```python
    def action_schedule(self):
        for r in self:
            if r.state == "draft" and not r.visita_ids:
                raise UserError(_(
                    "Agende pelo menos uma visita antes de agendar a OS."
                ))
        return super().action_schedule()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita`.
Esperado: PASS (7 testes).

- [ ] **Step 5: Commit**

```bash
cd /home/afonso/docker/odoo_engenapp/addons
git add afr_qualificacao_agendamento/models/qualificacao_os.py afr_qualificacao_agendamento/tests/test_visita.py
git commit -m "feat(agendamento): action_schedule exige ≥1 visita"
```

---

## Task 5: Detecção de conflito (técnico + deslocamento)

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py` (corpo de `_compute_conflicts`)
- Modify: `addons/afr_qualificacao_agendamento/tests/test_visita.py`

- [ ] **Step 1: Adicionar os testes que falham**

Acrescente à classe `TestVisita`:
```python
    def test_tecnico_conflict_same_day(self):
        """Mesmo técnico, duas visitas no mesmo dia → conflito de técnico."""
        V = self.env["afr.qualificacao.os.visita"]
        v1 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 10)})
        os2 = self._make_os(self._make_equipment("Santos"))
        v2 = V.create({"os_id": os2.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 10)})
        self.assertTrue(v1.tecnico_conflict)
        self.assertTrue(v2.tecnico_conflict)

    def test_no_tecnico_conflict_diff_days(self):
        V = self.env["afr.qualificacao.os.visita"]
        v1 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 10)})
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 12)})
        self.assertFalse(v1.tecnico_conflict)
        self.assertFalse(v2.tecnico_conflict)

    def test_travel_conflict(self):
        """Dias seguidos, cidades diferentes, buffer alto → conflito viagem."""
        V = self.env["afr.qualificacao.os.visita"]
        os_camp = self._make_os(self._make_equipment("Campinas"))
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                  "date": date(2026, 6, 10)})  # São Paulo
        v2 = V.create({"os_id": os_camp.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 11), "travel_buffer_hours": 10.0})
        self.assertTrue(v2.travel_conflict)

    def test_no_travel_conflict_zero_buffer(self):
        V = self.env["afr.qualificacao.os.visita"]
        os_camp = self._make_os(self._make_equipment("Campinas"))
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                  "date": date(2026, 6, 10)})
        v2 = V.create({"os_id": os_camp.id, "tecnico_id": self.emp.id,
                       "date": date(2026, 6, 11), "travel_buffer_hours": 0.0})
        self.assertFalse(v2.travel_conflict)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita.test_tecnico_conflict_same_day`.
Esperado: FALHA — `_compute_conflicts` ainda retorna sempre False.

- [ ] **Step 3: Implementar o corpo de `_compute_conflicts` em `models/os_visita.py`**

Substitua o método placeholder da Task 2 por:
```python
    @api.depends("tecnico_id", "date_start", "date_stop", "city",
                 "travel_buffer_hours")
    def _compute_conflicts(self):
        for r in self:
            r.tecnico_conflict = False
            r.tecnico_conflict_msg = False
            r.travel_conflict = False
            r.travel_conflict_msg = False
            if not r.tecnico_id or not r.date_start or not r.date_stop:
                continue
            exclude = [("id", "!=", r._origin.id)] if r._origin.id else []
            # Técnico em dois lugares: sobreposição de janela.
            overlap = self.search(exclude + [
                ("tecnico_id", "=", r.tecnico_id.id),
                ("date_start", "<", r.date_stop),
                ("date_stop", ">", r.date_start),
            ], limit=1)
            if overlap:
                r.tecnico_conflict = True
                r.tecnico_conflict_msg = _(
                    "%s já tem outra visita sobreposta: %s."
                ) % (r.tecnico_id.name, overlap.os_id.name or _("(sem OS)"))
            # Deslocamento: visita anterior do técnico em outra cidade.
            prev = self.search(exclude + [
                ("tecnico_id", "=", r.tecnico_id.id),
                ("date_stop", "<=", r.date_start),
                ("city", "!=", False),
            ], order="date_stop desc", limit=1)
            if prev and r.city and prev.city != r.city:
                gap_h = (r.date_start - prev.date_stop).total_seconds() / 3600.0
                need = r.travel_buffer_hours or 0.0
                if gap_h < need:
                    r.travel_conflict = True
                    r.travel_conflict_msg = _(
                        "Deslocamento %s → %s: %.1f h livres < %.1f h necessárias."
                    ) % (prev.city, r.city, gap_h, need)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Via `test-runner`, test-tags `/afr_qualificacao_agendamento:TestVisita`.
Esperado: PASS (11 testes).

- [ ] **Step 5: Commit**

```bash
cd /home/afonso/docker/odoo_engenapp/addons
git add afr_qualificacao_agendamento/models/os_visita.py afr_qualificacao_agendamento/tests/test_visita.py
git commit -m "feat(agendamento): conflito de técnico + deslocamento (não-bloqueante)"
```

---

## Task 6: Views (tree / form / calendar + aba na OS)

**Files:**
- Create: `addons/afr_qualificacao_agendamento/views/os_visita_views.xml`
- Create: `addons/afr_qualificacao_agendamento/views/qualificacao_os_views.xml`
- Modify: `addons/afr_qualificacao_agendamento/__manifest__.py` (registrar as views em `data`)

> Esta task é de UI; não há teste unitário. Validação = instalar e inspecionar no navegador (porta 8083). Use a skill `verify` ou o MCP chrome-devtools se quiser automatizar.

- [ ] **Step 0: Registrar as views no `__manifest__.py`**

Substitua o bloco `data` (que só tinha o csv) por:
```python
    "data": [
        "security/ir.model.access.csv",
        "views/os_visita_views.xml",
        "views/qualificacao_os_views.xml",
    ],
```

- [ ] **Step 1: Criar `views/os_visita_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Tree -->
    <record id="view_os_visita_tree" model="ir.ui.view">
        <field name="name">afr.qualificacao.os.visita.tree</field>
        <field name="model">afr.qualificacao.os.visita</field>
        <field name="arch" type="xml">
            <tree decoration-danger="tecnico_conflict or travel_conflict">
                <field name="sequence" widget="handle"/>
                <field name="date"/>
                <field name="time_start" widget="float_time"/>
                <field name="time_stop" widget="float_time"/>
                <field name="tecnico_id"/>
                <field name="partner_id"/>
                <field name="city"/>
                <field name="equipment_ids" widget="many2many_tags"/>
                <field name="planned_hours" sum="Horas"/>
                <field name="travel_buffer_hours"/>
                <field name="state"/>
                <field name="tecnico_conflict" invisible="1"/>
                <field name="travel_conflict" invisible="1"/>
            </tree>
        </field>
    </record>

    <!-- Form -->
    <record id="view_os_visita_form" model="ir.ui.view">
        <field name="name">afr.qualificacao.os.visita.form</field>
        <field name="model">afr.qualificacao.os.visita</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <div class="alert alert-warning" role="alert"
                         attrs="{'invisible': [('tecnico_conflict', '=', False)]}">
                        <field name="tecnico_conflict_msg" nolabel="1"/>
                    </div>
                    <div class="alert alert-warning" role="alert"
                         attrs="{'invisible': [('travel_conflict', '=', False)]}">
                        <field name="travel_conflict_msg" nolabel="1"/>
                    </div>
                    <group>
                        <group>
                            <field name="os_id"/>
                            <field name="tecnico_id"/>
                            <field name="date"/>
                            <field name="time_start" widget="float_time"/>
                            <field name="time_stop" widget="float_time"/>
                        </group>
                        <group>
                            <field name="partner_id"/>
                            <field name="city"/>
                            <field name="planned_hours"/>
                            <field name="travel_buffer_hours"/>
                            <field name="state"/>
                        </group>
                    </group>
                    <group string="Equipamentos">
                        <field name="equipment_ids" widget="many2many_tags" nolabel="1"/>
                    </group>
                    <group string="Observações">
                        <field name="note" nolabel="1"/>
                    </group>
                    <field name="tecnico_conflict" invisible="1"/>
                    <field name="travel_conflict" invisible="1"/>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Calendar (agenda nativa) -->
    <record id="view_os_visita_calendar" model="ir.ui.view">
        <field name="name">afr.qualificacao.os.visita.calendar</field>
        <field name="model">afr.qualificacao.os.visita</field>
        <field name="arch" type="xml">
            <calendar string="Agenda de Visitas"
                      date_start="date_start" date_stop="date_stop"
                      color="tecnico_id" mode="month"
                      quick_add="false" event_open_popup="true">
                <field name="os_id"/>
                <field name="tecnico_id" filters="1" avatar_field="image_128"/>
                <field name="partner_id" filters="1"/>
                <field name="city"/>
                <field name="state" filters="1" invisible="1"/>
            </calendar>
        </field>
    </record>

    <!-- Search -->
    <record id="view_os_visita_search" model="ir.ui.view">
        <field name="name">afr.qualificacao.os.visita.search</field>
        <field name="model">afr.qualificacao.os.visita</field>
        <field name="arch" type="xml">
            <search>
                <field name="os_id"/>
                <field name="tecnico_id"/>
                <field name="partner_id"/>
                <field name="city"/>
                <!-- Sem filtro por conflito: tecnico_conflict/travel_conflict são
                     computed non-stored (sem método search), não podem ir em domínio.
                     A decoração vermelha na tree já os surfa. -->
                <filter name="planejada" string="Planejada"
                        domain="[('state', '=', 'planned')]"/>
                <group expand="0" string="Agrupar por">
                    <filter name="g_tecnico" string="Técnico"
                            context="{'group_by': 'tecnico_id'}"/>
                    <filter name="g_data" string="Data"
                            context="{'group_by': 'date'}"/>
                    <filter name="g_cliente" string="Cliente"
                            context="{'group_by': 'partner_id'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Action + menu -->
    <record id="action_os_visita" model="ir.actions.act_window">
        <field name="name">Agenda de Visitas</field>
        <field name="res_model">afr.qualificacao.os.visita</field>
        <field name="view_mode">calendar,tree,form</field>
        <field name="search_view_id" ref="view_os_visita_search"/>
    </record>

    <menuitem id="menu_os_visita"
              name="Agenda de Visitas"
              action="action_os_visita"
              parent="afr_qualificacao.menu_afr_qualificacao_os"
              sequence="15"/>
</odoo>
```

> NOTA sobre o `parent` do menuitem: confirme o xmlid do menu pai de OS em `afr_qualificacao` (procure por `menu_afr_qualificacao_os` em `addons/afr_qualificacao/views/*.xml`). Se o id real diferir, ajuste o `parent=`. Se não houver menu adequado, troque por `parent="afr_qualificacao.menu_afr_qualificacao_root"` ou o menu raiz existente.

- [ ] **Step 2: Criar `views/qualificacao_os_views.xml` (herda o form da OS)**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_afr_qualificacao_os_form_agendamento" model="ir.ui.view">
        <field name="name">afr.qualificacao.os.form.agendamento</field>
        <field name="model">afr.qualificacao.os</field>
        <field name="inherit_id" ref="afr_qualificacao.view_afr_qualificacao_os_form"/>
        <field name="arch" type="xml">
            <!-- Stat button -->
            <xpath expr="//div[@name='button_box']" position="inside">
                <button type="object" name="action_view_visitas"
                        class="oe_stat_button" icon="fa-calendar">
                    <field name="visita_count" widget="statinfo" string="Visitas"/>
                </button>
            </xpath>
            <!-- Aba Visitas -->
            <xpath expr="//notebook" position="inside">
                <page string="Visitas" name="visitas">
                    <field name="visita_ids" context="{'default_tecnico_id': tecnico_default_id}">
                        <tree editable="bottom"
                              decoration-danger="tecnico_conflict or travel_conflict">
                            <field name="sequence" widget="handle"/>
                            <field name="date"/>
                            <field name="time_start" widget="float_time"/>
                            <field name="time_stop" widget="float_time"/>
                            <field name="tecnico_id"/>
                            <field name="equipment_ids" widget="many2many_tags"/>
                            <field name="planned_hours"/>
                            <field name="travel_buffer_hours"/>
                            <field name="state"/>
                            <field name="tecnico_conflict" invisible="1"/>
                            <field name="travel_conflict" invisible="1"/>
                        </tree>
                    </field>
                </page>
            </xpath>
        </field>
    </record>
</odoo>
```

> NOTA: confirme que o form da OS possui um `<notebook>`. Se não houver, envolva a `<page>` num `<notebook>` novo inserido no `<sheet>` via xpath apropriado.

- [ ] **Step 3: Atualizar o módulo e validar no navegador**

Via `test-runner` (ou comando do agente) rode `-u afr_qualificacao_agendamento` para carregar as views. Depois, no navegador (porta 8083):
- Abrir menu "Agenda de Visitas" → ver calendar por técnico.
- Abrir uma OS → stat button "Visitas" + aba "Visitas"; criar 2 visitas mesmo dia/técnico → linha fica vermelha (conflito).
- Confirmar que `date_planned_start/end` da OS refletem as visitas.

Esperado: sem erros de carga de view; conflitos destacados; rollup visível.

- [ ] **Step 4: Commit**

```bash
cd /home/afonso/docker/odoo_engenapp/addons
git add afr_qualificacao_agendamento/views/
git commit -m "feat(agendamento): views tree/form/calendar + aba Visitas na OS"
```

---

## Self-Review (cobertura do spec Fase A)

| Requisito do spec (Fase A) | Task |
|---|---|
| Módulo satélite `afr_qualificacao_agendamento` (depends afr_qualificacao) | Task 1 |
| Modelo `afr.qualificacao.os.visita` + campos (§4.1) | Task 2 |
| `date_start/date_stop` computados de date+hora | Task 2 |
| `partner_id`/`city` related | Task 2 |
| `visita_ids` na OS | Task 3 |
| Rollup `date_planned_*` (opção X) | Task 3 |
| `action_schedule` exige ≥1 visita | Task 4 |
| Conflito técnico-duplo (modo dia e hora via janela) | Task 5 |
| Conflito de deslocamento (buffer manual) | Task 5 |
| Conflitos não-bloqueantes (warning) | Task 5 (campos) + Task 6 (alertas/decoração) |
| Calendar nativa sobre visitas | Task 6 |
| Tree/form da visita + aba/stat na OS | Task 6 |
| Testes TDD (criação, rollup, schedule, conflitos, cascade) | Tasks 2-5 |

**Fora de escopo (fases futuras, não neste plano):** motor `action_suggest_visitas` (B); alocação instrumento↔visita + conflito de recurso/calibração (C); board OWL (D).

**Notas de risco herdadas do spec:**
- `date_planned_*` viram readonly (computed). Auditar relatórios/wizards que escreviam nesses campos antes de instalar em base com dados. Ambiente labquali está em DESENVOLVIMENTO (sem produção) — risco baixo agora.
- OS legadas em `scheduled` sem visitas: o gate só roda em transições novas (`state == 'draft'`); não revalida retroativo.
- Cascade ao deletar OS: `ondelete="cascade"` em `os_id` (testar manualmente ou adicionar teste em execução).

**Placeholder scan:** nenhum TBD/TODO de implementação. Os dois `> NOTA` na Task 6 são checagens de xmlid (menu pai e existência de `<notebook>`) que o implementer confirma no código existente — não são lacunas de design.

**Type consistency:** nomes de campos/métodos batem entre tasks (`visita_ids`, `visita_count`, `date_start/date_stop`, `tecnico_conflict(_msg)`, `travel_conflict(_msg)`, `action_view_visitas`, `_compute_conflicts`, `_compute_datetimes`, `_compute_planned_dates_rollup`).
