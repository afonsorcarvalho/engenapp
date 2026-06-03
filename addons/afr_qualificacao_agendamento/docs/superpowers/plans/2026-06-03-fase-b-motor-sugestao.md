# Fase B — Motor de Sugestão de Visitas — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao `afr_qualificacao_agendamento` um motor assistivo que, dado um técnico e uma data de início, gera as visitas diárias de uma OS distribuindo as horas estimadas (técnico-dias F5.8.0) por dia, respeitando `parallel_group`.

**Architecture:** Método de serviço `_suggest_visitas(tecnico, date_start)` no modelo `afr.qualificacao.os` (via `_inherit` no satélite), invocado por um wizard transient (`afr.qualificacao.os.suggest.wizard`) aberto por um botão "Sugerir visitas" no form da OS. Reusa `sale.order._qualif_schedule_rows()` como fonte de horas/jornada. Nenhum campo novo no modelo de visita (Fase A).

**Tech Stack:** Odoo 16.0 Community, Python (`math.ceil`, `datetime.timedelta`), `unittest.mock.patch` nos testes, XML (wizard form + button).

**Referências:**
- `sale.order._qualif_schedule_rows()` → `[{equipment, hours, work_hours_per_day, days}]` — `afr_qualificacao/models/sale_order.py:524-547`.
- `afr.qualificacao.os.sale_order_id` (M2o, editável) — `afr_qualificacao/models/qualificacao_os.py:52`.
- `afr.qualificacao.parallel_group` (Char) — `afr_qualificacao/models/qualificacao.py:252`.
- `afr.qualificacao.os.qualificacao_ids` (O2m, cada uma com `equipment_id` + `parallel_group`).
- `action_view_visitas()` já existe no satélite (Fase A) — reabre a agenda da OS.
- Spec: `afr_qualificacao_agendamento/docs/superpowers/specs/2026-06-03-fase-b-motor-sugestao-design.md`.

**Execução dos testes:** container `odoo_engenapp-web-1`, DB `odoo_ecm_test`. Comando:
```
docker exec odoo_engenapp-web-1 odoo -d odoo_ecm_test --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --no-http --workers=0 -u afr_qualificacao_agendamento --test-enable --test-tags /afr_qualificacao_agendamento:TestSuggest --stop-after-init
```
(NÃO commitar durante a execução — o usuário testa manualmente antes do commit.)

---

## Estrutura de arquivos

```
afr_qualificacao_agendamento/
├── __init__.py                              # MODIFY: + from . import wizards
├── __manifest__.py                          # MODIFY: + wizard view no data
├── wizards/
│   ├── __init__.py                          # CREATE: from . import suggest_visitas_wizard
│   └── suggest_visitas_wizard.py            # CREATE: afr.qualificacao.os.suggest.wizard
├── models/qualificacao_os.py                # MODIFY: + _suggest_visitas, _visita_parallel_group, action_open_suggest_wizard
├── views/
│   ├── suggest_visitas_wizard_views.xml     # CREATE: form do wizard
│   └── qualificacao_os_views.xml            # MODIFY: + botão "Sugerir visitas" no header
└── tests/test_suggest.py                    # CREATE: TestSuggest
```

---

## Task 1: Método de serviço `_suggest_visitas` (núcleo do motor)

**Files:**
- Modify: `models/qualificacao_os.py`
- Create: `tests/test_suggest.py`
- Modify: `tests/__init__.py` (registrar o novo módulo de teste)

- [ ] **Step 1: Escrever os testes que falham (`tests/test_suggest.py`)**

```python
# -*- coding: utf-8 -*-
from datetime import date, timedelta
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSuggest(TransactionCase):

    def _make_equipment(self, city):
        partner = self.env["res.partner"].create({"name": "Cli " + city, "city": city})
        return self.env["engc.equipment"].create({
            "name": "Equip " + city,
            "category_id": self.cat.id,
            "marca_id": self.marca.id,
            "model": "M1",
            "serial_number": "SN-" + city,
            "client_id": partner.id,
        })

    def _attach_qualif(self, os, equipment, parallel_group=False):
        return self.env["afr.qualificacao"].create({
            "os_id": os.id,
            "equipment_id": equipment.id,
            "qualification_type": "installation",
            "parallel_group": parallel_group or False,
        })

    def setUp(self):
        super().setUp()
        self.env.user.tz = "America/Sao_Paulo"
        self.cat = self.env["engc.equipment.category"].create({"name": "Cat Teste"})
        self.marca = self.env["engc.equipment.marca"].create({"name": "Marca Teste"})
        self.emp = self.env["hr.employee"].create({"name": "Téc 1"})
        self.partner = self.env["res.partner"].create({"name": "Cliente SO"})
        self.so = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.equip_a = self._make_equipment("São Paulo")
        self.os = self.env["afr.qualificacao.os"].create({"name": "OS-SUG-1"})
        self.os.sale_order_id = self.so.id

    def _rows(self, *triples):
        # triples: (equipment, hours, jornada)
        return [
            {"equipment": eq, "hours": h, "work_hours_per_day": j,
             "days": (h / j if j else 0.0)}
            for (eq, h, j) in triples
        ]

    def test_solo_equipment_day_split(self):
        """20h @ 8h/dia → 3 visitas com planned_hours [8, 8, 4] em dias corridos."""
        self._attach_qualif(self.os, self.equip_a)
        rows = self._rows((self.equip_a, 20.0, 8.0))
        with patch.object(type(self.so), "_qualif_schedule_rows", return_value=rows):
            self.os._suggest_visitas(self.emp, date(2026, 6, 10))
        vis = self.os.visita_ids.sorted("sequence")
        self.assertEqual(len(vis), 3)
        self.assertEqual(vis.mapped("planned_hours"), [8.0, 8.0, 4.0])
        self.assertEqual(vis.mapped("date"),
                         [date(2026, 6, 10), date(2026, 6, 11), date(2026, 6, 12)])
        self.assertTrue(all(v.tecnico_id == self.emp for v in vis))
        self.assertTrue(all(v.equipment_ids == self.equip_a for v in vis))

    def test_exact_multiple(self):
        """16h @ 8h → 2 visitas [8, 8]."""
        self._attach_qualif(self.os, self.equip_a)
        rows = self._rows((self.equip_a, 16.0, 8.0))
        with patch.object(type(self.so), "_qualif_schedule_rows", return_value=rows):
            self.os._suggest_visitas(self.emp, date(2026, 6, 10))
        vis = self.os.visita_ids.sorted("sequence")
        self.assertEqual(len(vis), 2)
        self.assertEqual(vis.mapped("planned_hours"), [8.0, 8.0])

    def test_parallel_group_shares_days(self):
        """2 equips mesmo parallel_group (16h e 8h @8h) → 2 visitas, cada uma com os 2 equips."""
        equip_b = self._make_equipment("Campinas")
        self._attach_qualif(self.os, self.equip_a, parallel_group="A")
        self._attach_qualif(self.os, equip_b, parallel_group="A")
        rows = self._rows((self.equip_a, 16.0, 8.0), (equip_b, 8.0, 8.0))
        with patch.object(type(self.so), "_qualif_schedule_rows", return_value=rows):
            self.os._suggest_visitas(self.emp, date(2026, 6, 10))
        vis = self.os.visita_ids.sorted("sequence")
        self.assertEqual(len(vis), 2)  # block_days = max(2, 1) = 2
        for v in vis:
            self.assertEqual(set(v.equipment_ids.ids), {self.equip_a.id, equip_b.id})

    def test_sequential_blocks_dates(self):
        """2 equips solo (8h cada) → blocos consecutivos: dia 10 (A), dia 11 (B)."""
        equip_b = self._make_equipment("Campinas")
        self._attach_qualif(self.os, self.equip_a)
        self._attach_qualif(self.os, equip_b)
        rows = self._rows((self.equip_a, 8.0, 8.0), (equip_b, 8.0, 8.0))
        with patch.object(type(self.so), "_qualif_schedule_rows", return_value=rows):
            self.os._suggest_visitas(self.emp, date(2026, 6, 10))
        vis = self.os.visita_ids.sorted("sequence")
        self.assertEqual(len(vis), 2)
        self.assertEqual(vis[0].date, date(2026, 6, 10))
        self.assertEqual(vis[0].equipment_ids, self.equip_a)
        self.assertEqual(vis[1].date, date(2026, 6, 11))
        self.assertEqual(vis[1].equipment_ids, equip_b)

    def test_rerun_replaces_planned_preserves_done(self):
        """Re-run apaga planejadas e recria; preserva visitas done."""
        self._attach_qualif(self.os, self.equip_a)
        done = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id, "tecnico_id": self.emp.id,
            "date": date(2026, 1, 1), "state": "done",
        })
        rows = self._rows((self.equip_a, 8.0, 8.0))
        with patch.object(type(self.so), "_qualif_schedule_rows", return_value=rows):
            self.os._suggest_visitas(self.emp, date(2026, 6, 10))
            self.os._suggest_visitas(self.emp, date(2026, 6, 10))  # 2x
        self.assertTrue(done.exists())
        planned = self.os.visita_ids.filtered(lambda v: v.state == "planned")
        self.assertEqual(len(planned), 1)  # não duplicou

    def test_no_sale_order_raises(self):
        os2 = self.env["afr.qualificacao.os"].create({"name": "OS-SUG-NOSO"})
        with self.assertRaises(UserError):
            os2._suggest_visitas(self.emp, date(2026, 6, 10))
```

`tests/__init__.py` — adicione a linha:
```python
from . import test_suggest
```

- [ ] **Step 2: Rodar e confirmar que falha**

`--test-tags /afr_qualificacao_agendamento:TestSuggest`.
Esperado: FALHA — `AttributeError: ... has no attribute '_suggest_visitas'`.

- [ ] **Step 3: Implementar os métodos em `models/qualificacao_os.py`**

Adicione os imports no topo (se faltarem):
```python
import math
from datetime import timedelta
```
(`_`, `api`, `fields`, `models` e `UserError` já estão importados da Fase A.)

Adicione à classe `AfrQualificacaoOs`:
```python
    def _visita_parallel_group(self, equipment):
        """Rótulo de grupo paralelo do equipamento (primeiro não-vazio entre suas qualifs)."""
        quals = self.qualificacao_ids.filtered(lambda q: q.equipment_id == equipment)
        for q in quals:
            if q.parallel_group:
                return q.parallel_group
        return False

    def _suggest_visitas(self, tecnico, date_start):
        """Gera visitas diárias distribuindo as horas estimadas (F5.8.0) por dia.

        - Apaga visitas 'planned' (preserva 'done').
        - Agrupa equipamentos por parallel_group; solo em sequência, paralelo junto.
        - Dias corridos a partir de date_start.
        """
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_(
                "OS sem pedido de venda; não há horas estimadas para sugerir visitas."
            ))
        self.visita_ids.filtered(lambda v: v.state == "planned").unlink()
        rows = self.sale_order_id._qualif_schedule_rows()

        # Monta blocos preservando a ordem de aparição.
        blocks = []
        seen_groups = {}
        for row in rows:
            equip = row.get("equipment")
            if not equip or (row.get("hours") or 0.0) <= 0.0:
                continue
            group = self._visita_parallel_group(equip)
            if group and group in seen_groups:
                seen_groups[group]["members"].append(row)
                continue
            block = {"group": group, "members": [row]}
            if group:
                seen_groups[group] = block
            blocks.append(block)

        Visita = self.env["afr.qualificacao.os.visita"]
        day_offset = 0
        seq = 0
        for block in blocks:
            members = block["members"]
            member_days = [
                math.ceil((m["hours"] or 0.0) / (m["work_hours_per_day"] or 8.0))
                for m in members
            ]
            n_days = max(member_days) if member_days else 0
            if n_days <= 0:
                continue
            equipment_ids = [m["equipment"].id for m in members]
            is_solo = len(members) == 1
            jornada_b = max((m["work_hours_per_day"] or 8.0) for m in members)
            for d in range(n_days):
                seq += 10
                if is_solo:
                    H = members[0]["hours"] or 0.0
                    J = members[0]["work_hours_per_day"] or 8.0
                    remaining = H - d * J
                    planned = J if remaining >= J else remaining
                else:
                    planned = jornada_b
                Visita.create({
                    "os_id": self.id,
                    "tecnico_id": tecnico.id,
                    "date": date_start + timedelta(days=day_offset + d),
                    "equipment_ids": [(6, 0, equipment_ids)],
                    "planned_hours": planned,
                    "sequence": seq,
                    "state": "planned",
                })
            day_offset += n_days
        return True

    def action_open_suggest_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sugerir visitas"),
            "res_model": "afr.qualificacao.os.suggest.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_os_id": self.id,
                "default_tecnico_id": self.tecnico_default_id.id,
            },
        }
```

- [ ] **Step 4: Rodar e confirmar que passa**

`--test-tags /afr_qualificacao_agendamento:TestSuggest`.
Esperado: PASS (6 testes).

- [ ] **Step 5: Rodar a suíte completa do módulo (regressão Fase A)**

`--test-tags /afr_qualificacao_agendamento`.
Esperado: PASS (11 da Fase A + 6 da Fase B = 17). Não commitar.

---

## Task 2: Wizard transient

**Files:**
- Create: `wizards/__init__.py`, `wizards/suggest_visitas_wizard.py`
- Modify: `__init__.py` (raiz)

- [ ] **Step 1: Criar `wizards/suggest_visitas_wizard.py`**

```python
# -*- coding: utf-8 -*-
from odoo import fields, models


class AfrQualificacaoOsSuggestWizard(models.TransientModel):
    _name = "afr.qualificacao.os.suggest.wizard"
    _description = "Assistente de sugestão de visitas"

    os_id = fields.Many2one(
        "afr.qualificacao.os", string="OS", required=True, ondelete="cascade"
    )
    tecnico_id = fields.Many2one(
        "hr.employee", string="Técnico", required=True
    )
    date_start = fields.Date(
        string="Data de início", required=True, default=fields.Date.context_today
    )

    def action_generate(self):
        self.ensure_one()
        self.os_id._suggest_visitas(self.tecnico_id, self.date_start)
        return self.os_id.action_view_visitas()
```

- [ ] **Step 2: Criar `wizards/__init__.py`**

```python
# -*- coding: utf-8 -*-
from . import suggest_visitas_wizard
```

- [ ] **Step 3: Atualizar `__init__.py` (raiz)**

```python
# -*- coding: utf-8 -*-
from . import models
from . import wizards
```

- [ ] **Step 4: Adicionar teste do wizard a `tests/test_suggest.py`**

Acrescente à classe `TestSuggest`:
```python
    def test_wizard_action_generate(self):
        """O wizard gera as visitas via _suggest_visitas."""
        self._attach_qualif(self.os, self.equip_a)
        rows = self._rows((self.equip_a, 8.0, 8.0))
        wiz = self.env["afr.qualificacao.os.suggest.wizard"].create({
            "os_id": self.os.id, "tecnico_id": self.emp.id,
            "date_start": date(2026, 6, 10),
        })
        with patch.object(type(self.so), "_qualif_schedule_rows", return_value=rows):
            action = wiz.action_generate()
        self.assertEqual(len(self.os.visita_ids), 1)
        self.assertEqual(action["res_model"], "afr.qualificacao.os.visita")
```

- [ ] **Step 5: Rodar e confirmar que passa**

`--test-tags /afr_qualificacao_agendamento:TestSuggest`.
Esperado: PASS (7 testes). Não commitar.

---

## Task 3: Views (wizard form + botão na OS)

**Files:**
- Create: `views/suggest_visitas_wizard_views.xml`
- Modify: `views/qualificacao_os_views.xml` (botão no header)
- Modify: `__manifest__.py` (registrar o view do wizard)

> Task de UI; validação = `-u` carrega sem erro + os testes do módulo continuam verdes.

- [ ] **Step 1: Criar `views/suggest_visitas_wizard_views.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_suggest_visitas_wizard_form" model="ir.ui.view">
        <field name="name">afr.qualificacao.os.suggest.wizard.form</field>
        <field name="model">afr.qualificacao.os.suggest.wizard</field>
        <field name="arch" type="xml">
            <form string="Sugerir visitas">
                <p class="text-muted">
                    Gera as visitas diárias da OS distribuindo as horas estimadas
                    pela jornada. Substitui as visitas planejadas; preserva as realizadas.
                </p>
                <group>
                    <field name="os_id" invisible="1"/>
                    <field name="tecnico_id"/>
                    <field name="date_start"/>
                </group>
                <footer>
                    <button name="action_generate" type="object"
                            string="Gerar visitas" class="btn-primary"/>
                    <button string="Cancelar" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
```

- [ ] **Step 2: Adicionar o botão no header do form da OS (`views/qualificacao_os_views.xml`)**

Dentro do `<field name="arch" type="xml">` do record `view_afr_qualificacao_os_form_agendamento` (o herdado da Fase A), acrescente mais um xpath:
```xml
            <xpath expr="//header" position="inside">
                <button name="action_open_suggest_wizard" type="object"
                        string="Sugerir visitas" class="btn-secondary"
                        attrs="{'invisible': [('state', 'not in', ['draft', 'scheduled'])]}"/>
            </xpath>
```

- [ ] **Step 3: Registrar o view do wizard no `__manifest__.py`**

No `data`, acrescente (antes ou depois das views existentes — após `security` e antes/junto das outras views):
```python
        "views/suggest_visitas_wizard_views.xml",
```
Ordem final do `data`:
```python
    "data": [
        "security/ir.model.access.csv",
        "views/suggest_visitas_wizard_views.xml",
        "views/os_visita_views.xml",
        "views/qualificacao_os_views.xml",
    ],
```
> Nota: o wizard transient não precisa de regra `ir.model.access` para usuários internos? Precisa sim de acesso de create/write. Adicione no `security/ir.model.access.csv` uma linha para o wizard (grupo técnico), pois `base.group_user` não cobre o modelo novo:
> ```csv
> access_suggest_wizard,afr.qualificacao.os.suggest.wizard,model_afr_qualificacao_os_suggest_wizard,afr_qualificacao.group_afr_qualificacao_user,1,1,1,1
> ```
> (TransientModel exige acesso; sem ele o wizard falha ao abrir para não-admin.)

- [ ] **Step 4: Atualizar o módulo e validar**

```
docker exec odoo_engenapp-web-1 odoo -d odoo_ecm_test --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --no-http --workers=0 -u afr_qualificacao_agendamento --test-enable --test-tags /afr_qualificacao_agendamento --stop-after-init
```
Esperado: módulo carrega sem ParseError; 17 testes (11 Fase A + 6 Fase B) + 1 wizard = 18 PASS. Não commitar.

No navegador (porta 8083): abrir uma OS com SO e qualificações → botão "Sugerir visitas" no header → wizard → Gerar → visitas aparecem na aba/calendar.

---

## Self-Review (cobertura do spec Fase B)

| Requisito do spec | Task |
|---|---|
| Método `_suggest_visitas(tecnico, date_start)` | Task 1 |
| Limpa planned / preserva done | Task 1 (test_rerun) |
| Fonte `_qualif_schedule_rows` + sem SO → UserError | Task 1 (test_no_sale_order) |
| Agrupa por parallel_group; solo sequencial, paralelo junto | Task 1 (test_parallel, test_sequential) |
| Split por jornada (dias cheios + resto), dias corridos | Task 1 (test_solo, test_exact) |
| Wizard transient (técnico, data início) | Task 2 |
| Botão "Sugerir visitas" na OS | Task 3 |
| Acesso do wizard (security) | Task 3 Step 3 |
| Reusa modelo visita (sem campo novo) | (todas — nenhum campo adicionado) |
| Testes TDD | Tasks 1-3 |

**Placeholder scan:** sem TBD/TODO de implementação.

**Type consistency:** `_suggest_visitas`, `_visita_parallel_group`, `action_open_suggest_wizard`, `action_generate`, modelo `afr.qualificacao.os.suggest.wizard`, `model_afr_qualificacao_os_suggest_wizard` (xmlid do access) — consistentes entre tasks.

**Nota de risco:** bloco paralelo usa `planned_hours = jornada_b` em todos os dias (aproximação consciente; humano ajusta). Os testes de paralelo não assertam `planned_hours` exato, só `equipment_ids` e contagem de dias.
