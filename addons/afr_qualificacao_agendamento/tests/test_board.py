# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
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
        # Datas relativas a hoje (futuras) — suite não envelhece com a regra
        # de "não programar no passado".
        base = fields.Date.context_today(self.Visita) + timedelta(days=30)
        self.d10 = base                         # dia base (antigo 2026-06-10)
        self.d11 = base + timedelta(days=1)      # antigo 2026-06-11
        self.d12 = base + timedelta(days=2)      # antigo 2026-06-12
        self.d_out = base + timedelta(days=21)   # fora do range (antigo 07-01)
        self.r_from = (base - timedelta(days=2)).isoformat()  # antigo 06-08
        self.r_to = (base + timedelta(days=4)).isoformat()    # antigo 06-14

    def test_board_fetch_structure(self):
        os1 = self._make_os()
        self._make_visita(os1, self.d10, self.t1)
        self._make_visita(os1, self.d11, self.t2)
        data = self.Visita.board_fetch(self.r_from, self.r_to)
        self.assertEqual({t["id"] for t in data["technicians"]},
                         {self.t1.id, self.t2.id})
        self.assertEqual(len(data["visitas"]), 2)
        keys = ("id", "tecnico_id", "date", "os_id", "os_name",
                "partner_name", "planned_hours", "state",
                "equipment_names", "equipment_list",
                "instrument_names", "instrument_list",
                "conflict", "conflict_msg")
        for k in keys:
            self.assertIn(k, data["visitas"][0])

    def test_board_fetch_range(self):
        os1 = self._make_os()
        self._make_visita(os1, self.d10, self.t1)
        self._make_visita(os1, self.d_out, self.t1)  # fora do range
        data = self.Visita.board_fetch(self.r_from, self.r_to)
        self.assertEqual(len(data["visitas"]), 1)

    def test_board_fetch_conflict_flag(self):
        os1, os2 = self._make_os(), self._make_os()
        self._make_visita(os1, self.d10, self.t1)
        self._make_visita(os2, self.d10, self.t1)  # mesmo téc/dia
        data = self.Visita.board_fetch(self.r_from, self.r_to)
        self.assertTrue(all(v["conflict"] for v in data["visitas"]))
        self.assertTrue(all(v["conflict_msg"] for v in data["visitas"]))

    def test_board_reschedule(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        self.Visita.board_reschedule(v.id, self.d12.isoformat(), self.t2.id)
        self.assertEqual(v.date, self.d12)
        self.assertEqual(v.tecnico_id, self.t2)

    def test_board_delete_visita(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        self.Visita.board_delete_visita(v.id)
        self.assertFalse(v.exists())

    def test_board_set_hours(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        self.Visita.board_set_hours(v.id, 8.0, 12.0)
        self.assertEqual(v.time_start, 8.0)
        self.assertEqual(v.time_stop, 12.0)
        self.assertEqual(v.planned_hours, 4.0)  # fim - início

    def test_board_reschedule_done_blocked(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.board_reschedule(v.id, self.d12.isoformat(), self.t2.id)

    def test_board_delete_done_blocked(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.board_delete_visita(v.id)
        self.assertTrue(v.exists())

    def test_board_set_hours_done_blocked(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.board_set_hours(v.id, 8.0, 12.0)

    def test_board_split_overflow_done_blocked(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d10, self.t1)
        v.write({"time_start": 0.0, "planned_hours": 30.0})  # transborda
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.board_split_overflow(v.id)

    def test_board_technician_options(self):
        self.t1.is_tecnico = True
        # t2 fica False
        opts = self.Visita.board_technician_options()
        ids = {o["id"] for o in opts}
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)
        for o in opts:
            self.assertIn("id", o)
            self.assertIn("name", o)

    def test_board_os_options_excludes_closed(self):
        os_open = self._make_os()
        os_open.state = "in_progress"
        os_done = self._make_os()
        os_done.state = "done"
        os_cancel = self._make_os()
        os_cancel.state = "cancelled"
        opts = self.Visita.board_os_options()
        ids = {o["id"] for o in opts}
        self.assertIn(os_open.id, ids)
        self.assertNotIn(os_done.id, ids)
        self.assertNotIn(os_cancel.id, ids)

    def test_board_os_options_name_format(self):
        os1 = self._make_os()
        partner = self.env["res.partner"].create({"name": "Cliente X"})
        os1.partner_id = partner
        opts = self.Visita.board_os_options()
        match = [o for o in opts if o["id"] == os1.id]
        self.assertEqual(len(match), 1)
        self.assertIn("Cliente X", match[0]["name"])
        self.assertIn(os1.name, match[0]["name"])

    def test_board_create_visita(self):
        os1 = self._make_os()
        self.Visita.board_create_visita(os1.id, self.t1.id, self.d10.isoformat())
        v = self.Visita.search([
            ("os_id", "=", os1.id), ("tecnico_id", "=", self.t1.id),
            ("date", "=", self.d10),
        ])
        self.assertEqual(len(v), 1)
        self.assertEqual(v.date, self.d10)
