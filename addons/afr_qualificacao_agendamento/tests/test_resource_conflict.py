# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import fields
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
        # Datas de visita relativas a hoje (futuras) — regra de "não programar
        # no passado". Datas de certificado abaixo permanecem fixas.
        base = fields.Date.context_today(
            self.env["afr.qualificacao.os.visita"]) + timedelta(days=30)
        self.d0 = base                       # antigo 2026-06-10
        self.d2 = base + timedelta(days=2)    # antigo 2026-06-12

    def test_instrument_conflict_overlap(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        os1, os2 = self._make_os(), self._make_os()
        v1 = self._make_visita(os1, self.d0, [inst])
        v2 = self._make_visita(os2, self.d0, [inst])
        self.assertTrue(v1.instrument_conflict)
        self.assertTrue(v2.instrument_conflict)

    def test_no_instrument_conflict_diff_dates(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        os1, os2 = self._make_os(), self._make_os()
        self._make_visita(os1, self.d0, [inst])
        v2 = self._make_visita(os2, self.d2, [inst])
        self.assertFalse(v2.instrument_conflict)

    def test_no_instrument_conflict_same_os(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        os1 = self._make_os()
        v1 = self._make_visita(os1, self.d0, [inst])
        v2 = self._make_visita(os1, self.d0, [inst])
        self.assertFalse(v1.instrument_conflict)
        self.assertFalse(v2.instrument_conflict)

    def test_calibration_expired(self):
        inst = self._make_instrument("Logger A", date(2026, 1, 1))  # vencido antes de jun/26
        v = self._make_visita(self._make_os(), self.d0, [inst])
        self.assertTrue(v.calibration_conflict)

    def test_calibration_valid(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        v = self._make_visita(self._make_os(), self.d0, [inst])
        self.assertFalse(v.calibration_conflict)

    def test_calibration_no_certificate(self):
        inst = self._make_instrument("Logger A")  # sem certificado
        v = self._make_visita(self._make_os(), self.d0, [inst])
        self.assertTrue(v.calibration_conflict)

    def test_pull_instruments_from_plan(self):
        inst = self._make_instrument("Logger A", date(2030, 1, 1))
        equip = self._make_equipment("São Paulo")
        os1 = self._make_os()
        self.env["afr.qualificacao.resource.plan.line"].create({
            "os_id": os1.id, "resource_role": "validador",
            "instrument_id": inst.id, "equipment_ids": [(6, 0, [equip.id])],
        })
        v = self._make_visita(os1, self.d0)
        v.equipment_ids = [(6, 0, [equip.id])]
        v.action_pull_instruments_from_plan()
        self.assertEqual(v.instrument_ids, inst)
