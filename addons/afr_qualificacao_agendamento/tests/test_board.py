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
