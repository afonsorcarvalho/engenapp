# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVisita(TransactionCase):

    def _make_equipment(self, city):
        # category/marca compartilhados (self.cat/self.marca em setUp):
        # engc.equipment.marca tem unique(name); recriar a cada chamada
        # violaria a constraint quando um teste cria 2+ equipamentos.
        # (category é compartilhada por conveniência; não tem constraint SQL.)
        partner = self.env["res.partner"].create({"name": "Cli " + city, "city": city})
        return self.env["engc.equipment"].create({
            "name": "Equip " + city,
            "category_id": self.cat.id,
            "marca_id": self.marca.id,
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
        self.env.user.tz = "America/Sao_Paulo"
        self._os_seq = 0
        self.cat = self.env["engc.equipment.category"].create({"name": "Cat Teste"})
        self.marca = self.env["engc.equipment.marca"].create({"name": "Marca Teste"})
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
