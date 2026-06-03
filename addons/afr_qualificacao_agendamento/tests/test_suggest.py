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
