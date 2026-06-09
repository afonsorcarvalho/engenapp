# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
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
        # Datas-base relativas a hoje (futuras) — evitam que a regra de
        # "não programar no passado" quebre o suite quando o calendário avança.
        base = fields.Date.context_today(
            self.env["afr.qualificacao.os.visita"]) + timedelta(days=30)
        self.d0 = base                        # dia base
        self.d1 = base + timedelta(days=1)    # base + 1
        self.d2 = base + timedelta(days=2)    # base + 2

    def test_datetimes_day_mode(self):
        """Sem horas: date_start no início e date_stop no fim do dia."""
        v = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id,
            "tecnico_id": self.emp.id,
            "date": self.d0,
        })
        self.assertTrue(v.date_start)
        self.assertTrue(v.date_stop)
        self.assertLess(v.date_start, v.date_stop)
        # date_stop deve cair no mesmo dia civil (margem de fuso)
        self.assertEqual(v.date_start.date(), self.d0)

    def test_name_compute(self):
        v = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id,
            "tecnico_id": self.emp.id,
            "date": self.d0,
        })
        self.assertIn("Téc 1", v.name)
        self.assertIn(fields.Date.to_string(self.d0), v.name)

    def test_related_city(self):
        v = self.env["afr.qualificacao.os.visita"].create({
            "os_id": self.os.id,
            "tecnico_id": self.emp.id,
            "date": self.d0,
        })
        self.assertEqual(v.partner_id, self.equip_sp.client_id)
        self.assertEqual(v.city, "São Paulo")

    def test_rollup_planned_dates(self):
        """date_planned_start/end da OS = min/max das visitas."""
        V = self.env["afr.qualificacao.os.visita"]
        v1 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": self.d0})
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": self.d2})
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
            "date": self.d0,
        })
        self.os.action_schedule()
        self.assertEqual(self.os.state, "scheduled")

    def test_overflow_flag(self):
        """time_start + planned_hours > 24 → overflow_next_day."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self.d0,
                      "time_start": 20.0, "planned_hours": 8.0})
        self.assertTrue(v.overflow_next_day)
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": self.d0,
                       "time_start": 8.0, "planned_hours": 8.0})
        self.assertFalse(v2.overflow_next_day)

    def test_split_overflow_creates_continuation(self):
        """Dividir: dia atual fica com o que cabe; resto vira visita no dia +1."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self.d0,
                      "time_start": 20.0, "planned_hours": 8.0})
        action = v.action_split_overflow()
        # fits = 24 - 20 = 4; rest = 8 - 4 = 4
        self.assertEqual(v.planned_hours, 4.0)
        cont = V.browse(action["res_id"])
        self.assertEqual(cont.date, self.d1)
        self.assertEqual(cont.planned_hours, 4.0)
        # continuação mantém o MESMO horário de início da origem
        self.assertEqual(cont.time_start, 20.0)
        self.assertEqual(cont.tecnico_id, v.tecnico_id)
        self.assertEqual(cont.os_id, v.os_id)

    def test_board_split_overflow_reapplies(self):
        """board_split_overflow divide; a continuação que ainda transborda
        mantém overflow=True (botão reaparece)."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self.d0,
                      "time_start": 8.0, "planned_hours": 40.0})
        # fits = 16; rest = 24 → continuação 8h + 24h = 32 > 24 → ainda transborda
        V.board_split_overflow(v.id)
        self.assertEqual(v.planned_hours, 16.0)
        cont = V.search([("os_id", "=", self.os.id),
                         ("date", "=", self.d1)], limit=1)
        self.assertTrue(cont)
        self.assertEqual(cont.time_start, 8.0)
        self.assertEqual(cont.planned_hours, 24.0)
        self.assertTrue(cont.overflow_next_day)

    def test_split_overflow_no_overflow_raises(self):
        from odoo.exceptions import UserError
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self.d0,
                      "time_start": 8.0, "planned_hours": 4.0})
        with self.assertRaises(UserError):
            v.action_split_overflow()

    def test_tecnico_conflict_same_day(self):
        """Mesmo técnico, duas visitas no mesmo dia → conflito de técnico."""
        V = self.env["afr.qualificacao.os.visita"]
        v1 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": self.d0})
        os2 = self._make_os(self._make_equipment("Santos"))
        v2 = V.create({"os_id": os2.id, "tecnico_id": self.emp.id,
                       "date": self.d0})
        self.assertTrue(v1.tecnico_conflict)
        self.assertTrue(v2.tecnico_conflict)

    def test_no_tecnico_conflict_diff_days(self):
        V = self.env["afr.qualificacao.os.visita"]
        v1 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": self.d0})
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": self.d2})
        self.assertFalse(v1.tecnico_conflict)
        self.assertFalse(v2.tecnico_conflict)

    def test_travel_conflict(self):
        """Dias seguidos, cidades diferentes, buffer alto → conflito viagem."""
        V = self.env["afr.qualificacao.os.visita"]
        os_camp = self._make_os(self._make_equipment("Campinas"))
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                  "date": self.d0})  # São Paulo
        v2 = V.create({"os_id": os_camp.id, "tecnico_id": self.emp.id,
                       "date": self.d1, "travel_buffer_hours": 10.0})
        self.assertTrue(v2.travel_conflict)

    def test_no_travel_conflict_zero_buffer(self):
        V = self.env["afr.qualificacao.os.visita"]
        os_camp = self._make_os(self._make_equipment("Campinas"))
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                  "date": self.d0})
        v2 = V.create({"os_id": os_camp.id, "tecnico_id": self.emp.id,
                       "date": self.d1, "travel_buffer_hours": 0.0})
        self.assertFalse(v2.travel_conflict)

    # ───────── Regra: não programar no passado ─────────
    def _today(self):
        # Mesmo "hoje" que a constraint usa (fuso do usuário), evita
        # off-by-one entre date.today() (UTC) e context_today.
        return fields.Date.context_today(
            self.env["afr.qualificacao.os.visita"])

    def test_block_create_past_date(self):
        """Criar visita com data passada → ValidationError."""
        V = self.env["afr.qualificacao.os.visita"]
        with self.assertRaises(ValidationError):
            V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self._today() - timedelta(days=1)})

    def test_allow_create_today(self):
        """Hoje é permitido (só o passado é bloqueado)."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self._today()})
        self.assertTrue(v.exists())

    def test_block_reschedule_to_past(self):
        """Mover visita futura para o passado via write → ValidationError."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": self._today() + timedelta(days=3)})
        with self.assertRaises(ValidationError):
            v.write({"date": self._today() - timedelta(days=1)})

    # ───────── Regra: OS em execução trava a visita ─────────
    def test_os_lock_blocks_schedule_edit(self):
        """OS in_progress → editar campo de agenda da visita é bloqueado."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": date.today() + timedelta(days=2)})
        self.os.state = "in_progress"
        with self.assertRaises(UserError):
            v.write({"time_start": 9.0})

    def test_os_lock_allows_done(self):
        """OS travada ainda permite marcar a visita como Realizada."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": date.today() + timedelta(days=2)})
        self.os.state = "in_progress"
        v.write({"state": "done"})
        self.assertEqual(v.state, "done")

    def test_os_lock_blocks_unlink(self):
        """OS travada → apagar a visita é bloqueado."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": date.today() + timedelta(days=2)})
        self.os.state = "in_progress"
        with self.assertRaises(UserError):
            v.unlink()

    def test_os_unlocked_allows_edit(self):
        """OS scheduled (não travada) → editar agenda é permitido."""
        V = self.env["afr.qualificacao.os.visita"]
        v = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": date.today() + timedelta(days=2)})
        self.os.state = "scheduled"
        v.write({"time_start": 9.0})
        self.assertEqual(v.time_start, 9.0)

    # ───────── Regra: mesmo equipamento, horário sobreposto ─────────
    def test_equipment_overlap_blocks(self):
        """Mesmo equipamento, mesmo dia, horários sobrepostos → bloqueado."""
        V = self.env["afr.qualificacao.os.visita"]
        day = date.today() + timedelta(days=5)
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id, "date": day,
                  "time_start": 8.0, "time_stop": 12.0, "planned_hours": 4.0,
                  "equipment_ids": [(6, 0, [self.equip_sp.id])]})
        with self.assertRaises(ValidationError):
            V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                      "date": day, "time_start": 10.0, "time_stop": 14.0,
                      "planned_hours": 4.0,
                      "equipment_ids": [(6, 0, [self.equip_sp.id])]})

    def test_equipment_no_overlap_ok(self):
        """Mesmo equipamento, mesmo dia, sem sobreposição → permitido."""
        V = self.env["afr.qualificacao.os.visita"]
        day = date.today() + timedelta(days=5)
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id, "date": day,
                  "time_start": 8.0, "time_stop": 12.0, "planned_hours": 4.0,
                  "equipment_ids": [(6, 0, [self.equip_sp.id])]})
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": day, "time_start": 14.0, "time_stop": 18.0,
                       "planned_hours": 4.0,
                       "equipment_ids": [(6, 0, [self.equip_sp.id])]})
        self.assertTrue(v2.exists())

    def test_equipment_overlap_diff_day_ok(self):
        """Mesmo equipamento em dias diferentes → sem conflito."""
        V = self.env["afr.qualificacao.os.visita"]
        d1 = date.today() + timedelta(days=5)
        V.create({"os_id": self.os.id, "tecnico_id": self.emp.id, "date": d1,
                  "time_start": 8.0, "time_stop": 12.0, "planned_hours": 4.0,
                  "equipment_ids": [(6, 0, [self.equip_sp.id])]})
        v2 = V.create({"os_id": self.os.id, "tecnico_id": self.emp.id,
                       "date": d1 + timedelta(days=1), "time_start": 8.0,
                       "time_stop": 12.0, "planned_hours": 4.0,
                       "equipment_ids": [(6, 0, [self.equip_sp.id])]})
        self.assertTrue(v2.exists())

    def test_onchange_fill_time_stop(self):
        """time_start + planned_hours preenche time_stop."""
        from odoo.tests.common import Form
        with Form(self.env["afr.qualificacao.os.visita"]) as f:
            f.os_id = self.os
            f.tecnico_id = self.emp
            f.date = self.d0
            f.time_start = 8.0
            f.planned_hours = 3.0
            self.assertEqual(f.time_stop, 11.0)

    def test_onchange_time_stop_grows_hours(self):
        """Alongar time_stop aumenta planned_hours (grow-only)."""
        from odoo.tests.common import Form
        with Form(self.env["afr.qualificacao.os.visita"]) as f:
            f.os_id = self.os
            f.tecnico_id = self.emp
            f.date = self.d0
            f.time_start = 8.0
            f.planned_hours = 2.0   # time_stop -> 10.0
            f.time_stop = 13.0      # +3h além do previsto
            self.assertEqual(f.planned_hours, 5.0)

    def test_onchange_time_stop_shrink_keeps_hours(self):
        """Encurtar time_stop NÃO reduz planned_hours (grow-only)."""
        from odoo.tests.common import Form
        with Form(self.env["afr.qualificacao.os.visita"]) as f:
            f.os_id = self.os
            f.tecnico_id = self.emp
            f.date = self.d0
            f.time_start = 8.0
            f.planned_hours = 5.0   # time_stop -> 13.0
            f.time_stop = 10.0      # encurta
            self.assertEqual(f.planned_hours, 5.0)
