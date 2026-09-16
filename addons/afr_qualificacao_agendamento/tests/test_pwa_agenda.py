# -*- coding: utf-8 -*-
"""Agenda de visitas no PWA Técnico — papéis, serializer e mutações `pwa_*`.

Técnico é leitor; só o Gestor cria, edita e apaga. O guard vive no servidor
porque o proxy `/api/odoo` do PWA repassa `call_kw` sem allowlist de método:
esconder o botão não protege nada.
"""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("afr_qualificacao_agendamento", "pwa_agenda", "post_install", "-at_install")
class PwaAgendaCommon(TransactionCase):
    """Base compartilhada: três usuários (um por papel) e duas visitas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = "America/Sao_Paulo"
        Users = cls.env["res.users"]
        base_group = cls.env.ref("base.group_user").id
        cls.user_tec = Users.create({
            "name": "Téc Agenda", "login": "tec.agenda.pwa",
            "groups_id": [(6, 0, [
                base_group,
                cls.env.ref(
                    "afr_qualificacao.group_afr_qualificacao_technician").id,
            ])],
        })
        cls.user_usr = Users.create({
            "name": "Usuário Agenda", "login": "usr.agenda.pwa",
            "groups_id": [(6, 0, [
                base_group,
                cls.env.ref("afr_qualificacao.group_afr_qualificacao_user").id,
            ])],
        })
        cls.user_gestor = Users.create({
            "name": "Gestor Agenda", "login": "gestor.agenda.pwa",
            "groups_id": [(6, 0, [
                base_group,
                cls.env.ref(
                    "afr_qualificacao.group_afr_qualificacao_manager").id,
            ])],
        })
        # Mesmo fuso do admin (`cls.env.user.tz` acima): sem isto, um write
        # feito `with_user(user_gestor)` recomputa date_start/date_stop num
        # relógio diferente do usado para criar os registros de comparação
        # (ex. `_check_equipment_overlap`), mascarando sobreposições reais.
        (cls.user_tec | cls.user_usr | cls.user_gestor).write(
            {"tz": "America/Sao_Paulo"})
        cls.emp_tec = cls.env["hr.employee"].create({
            "name": "Téc Agenda", "user_id": cls.user_tec.id,
        })
        cls.emp_outro = cls.env["hr.employee"].create({"name": "Téc Outro"})
        cls.Visita = cls.env["afr.qualificacao.os.visita"]
        # Datas futuras: `_check_date_not_past` proíbe programar no passado,
        # e uma suíte com data fixa envelheceria.
        cls.hoje = fields.Date.context_today(cls.Visita)
        cls.d1 = cls.hoje + timedelta(days=3)
        cls.d2 = cls.hoje + timedelta(days=4)
        cls.d_fora = cls.hoje + timedelta(days=40)
        cls._seq = 0

    @classmethod
    def _make_os(cls, state="scheduled"):
        cls._seq += 1
        os = cls.env["afr.qualificacao.os"].create({
            "name": "OS-PWA-%d" % cls._seq,
        })
        os.state = state
        return os

    @classmethod
    def _make_visita(cls, os, day, employee, **extra):
        vals = {"os_id": os.id, "tecnico_id": employee.id, "date": day}
        vals.update(extra)
        return cls.Visita.create(vals)


class TestPwaAgendaAcl(PwaAgendaCommon):

    def test_tecnico_le_visita(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d1, self.emp_tec)
        lido = v.with_user(self.user_tec).read(["date", "os_id"])
        self.assertEqual(len(lido), 1)

    def test_tecnico_nao_escreve_visita(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d1, self.emp_tec)
        with self.assertRaises(AccessError):
            v.with_user(self.user_tec).write({"note": "tentativa"})

    def test_tecnico_nao_apaga_visita(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d1, self.emp_tec)
        with self.assertRaises(AccessError):
            v.with_user(self.user_tec).unlink()

    def test_gestor_escreve_visita(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d1, self.emp_tec)
        v.with_user(self.user_gestor).write({"note": "ok"})
        self.assertEqual(v.note, "ok")

    def test_guard_barra_tecnico(self):
        Visita = self.Visita.with_user(self.user_tec)
        with self.assertRaises(UserError):
            Visita._check_manager_only("testar o guard")

    def test_guard_barra_usuario(self):
        """`manager ⊃ user ⊃ technician`: a implicação desce, então o Usuário
        comum NÃO está no grupo Gestor e o guard o barra. É o oposto do que
        acontece com `ir.rule`, onde a implicação exigiria o par OR'ed."""
        Visita = self.Visita.with_user(self.user_usr)
        with self.assertRaises(UserError):
            Visita._check_manager_only("testar o guard")

    def test_guard_libera_gestor(self):
        Visita = self.Visita.with_user(self.user_gestor)
        self.assertIsNone(Visita._check_manager_only("testar o guard"))


class TestPwaAgendaFetch(PwaAgendaCommon):

    def test_payload_tem_janela_do_servidor(self):
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        self.assertEqual(data["server_today"], fields.Date.to_string(self.hoje))
        self.assertEqual(data["date_from"], fields.Date.to_string(self.hoje))
        self.assertEqual(
            data["date_to"],
            fields.Date.to_string(self.hoje + timedelta(days=13)),
        )

    def test_janela_explicita_respeitada(self):
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        self._make_visita(os1, self.d_fora, self.emp_tec)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            fields.Date.to_string(self.hoje),
            fields.Date.to_string(self.hoje + timedelta(days=10)),
            False,
        )
        ids = {v["id"] for v in data["visitas"]}
        self.assertEqual(len(ids), 1)

    def test_only_mine_filtra_por_empregado(self):
        os1 = self._make_os()
        minha = self._make_visita(os1, self.d1, self.emp_tec)
        self._make_visita(os1, self.d2, self.emp_outro)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            only_mine=True)
        self.assertEqual([v["id"] for v in data["visitas"]], [minha.id])
        self.assertEqual(data["my_employee_id"], self.emp_tec.id)

    def test_only_mine_ignorado_sem_empregado(self):
        """Gestor administrativo não tem hr.employee. Filtrar por ele abriria
        a tela vazia e sem explicação; o servidor devolve tudo e o front
        desabilita o toggle."""
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=True)
        self.assertFalse(data["my_employee_id"])
        self.assertEqual(len(data["visitas"]), 1)

    def test_tecnico_ve_visita_de_colega(self):
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_outro)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            only_mine=False)
        self.assertEqual(len(data["visitas"]), 1)
        self.assertFalse(data["visitas"][0]["is_mine"])

    def test_chaves_do_serializer(self):
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec,
                          time_start=8.0, time_stop=12.0, planned_hours=4.0)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        row = data["visitas"][0]
        for k in ("id", "date", "time_start", "time_stop", "planned_hours",
                  "os_id", "os_name", "os_state", "partner_name", "city",
                  "equipment_list", "instrument_list", "tecnico_id",
                  "tecnico_name", "is_mine", "state", "overflow", "editable",
                  "lock_reason", "conflict", "conflict_msg", "note"):
            self.assertIn(k, row)
        self.assertEqual(row["tecnico_name"], "Téc Agenda")

    def test_tecnico_nunca_edita(self):
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        row = data["visitas"][0]
        self.assertFalse(data["can_manage"])
        self.assertFalse(row["editable"])
        self.assertIn("Gestor", row["lock_reason"])

    def test_gestor_edita_os_agendada(self):
        os1 = self._make_os("scheduled")
        self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = data["visitas"][0]
        self.assertTrue(data["can_manage"])
        self.assertTrue(row["editable"])
        self.assertFalse(row["lock_reason"])

    def test_gestor_travado_em_os_em_execucao(self):
        os1 = self._make_os("scheduled")
        self._make_visita(os1, self.d1, self.emp_tec)
        os1.state = "in_progress"
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = data["visitas"][0]
        self.assertFalse(row["editable"])
        self.assertIn("execução", row["lock_reason"])

    def test_gestor_travado_em_visita_realizada(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        v.state = "done"
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = data["visitas"][0]
        self.assertFalse(row["editable"])
        self.assertIn("realizada", row["lock_reason"])

    def test_conflito_exposto(self):
        os1, os2 = self._make_os(), self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        self._make_visita(os2, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        self.assertTrue(all(v["conflict"] for v in data["visitas"]))
        self.assertTrue(all(v["conflict_msg"] for v in data["visitas"]))

    def test_sem_permissao_hr_nao_estoura(self):
        """Regressão da delegação hr.employee → hr.employee.public. O técnico
        não lê hr.employee; ler `tecnico_id.name` sem sudo quebra a chamada
        inteira. Já mordeu `is_tecnico` neste módulo e o `engc_os`."""
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        self.assertFalse(self.user_tec.has_group("hr.group_hr_user"))
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        self.assertEqual(data["visitas"][0]["tecnico_name"], "Téc Agenda")


class TestPwaAgendaUpdate(PwaAgendaCommon):

    def _visita_editavel(self):
        os1 = self._make_os("scheduled")
        return self._make_visita(os1, self.d1, self.emp_tec,
                                 time_start=8.0, time_stop=12.0,
                                 planned_hours=4.0)

    def test_tecnico_barrado(self):
        v = self._visita_editavel()
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_tec).pwa_visita_update(
                v.id, {"note": "x"})

    def test_usuario_barrado(self):
        v = self._visita_editavel()
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_usr).pwa_visita_update(
                v.id, {"note": "x"})

    def test_gestor_move_data(self):
        v = self._visita_editavel()
        row = self.Visita.with_user(self.user_gestor).pwa_visita_update(
            v.id, {"date": fields.Date.to_string(self.d2)})
        self.assertEqual(v.date, self.d2)
        self.assertEqual(row["date"], fields.Date.to_string(self.d2))

    def test_horas_recalculadas(self):
        v = self._visita_editavel()
        self.Visita.with_user(self.user_gestor).pwa_visita_update(
            v.id, {"time_start": 9.0, "time_stop": 15.0})
        self.assertEqual(v.planned_hours, 6.0)

    def test_repasse_para_colega(self):
        v = self._visita_editavel()
        self.Visita.with_user(self.user_gestor).pwa_visita_update(
            v.id, {"tecnico_id": self.emp_outro.id})
        self.assertEqual(v.tecnico_id, self.emp_outro)

    def test_campo_fora_da_whitelist(self):
        v = self._visita_editavel()
        for vals in ({"os_id": self._make_os().id}, {"state": "done"},
                     {"planned_hours": 99.0}):
            with self.assertRaises(UserError):
                self.Visita.with_user(self.user_gestor).pwa_visita_update(
                    v.id, vals)

    def test_visita_realizada_recusa(self):
        v = self._visita_editavel()
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"note": "x"})

    def test_os_em_execucao_recusa_agendamento(self):
        v = self._visita_editavel()
        v.os_id.state = "in_progress"
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"date": fields.Date.to_string(self.d2)})

    def test_data_passada_recusa(self):
        v = self._visita_editavel()
        ontem = fields.Date.to_string(self.hoje - timedelta(days=1))
        with self.assertRaises(ValidationError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"date": ontem})

    def test_sobreposicao_de_equipamento_dispara_por_hora(self):
        """`_check_equipment_overlap` observa `date_start`/`date_stop`, que são
        computed stored derivados de `time_start`/`time_stop`. Mexer só na
        hora precisa disparar a constraint — se não disparar, a promessa de
        'travas preservadas' da spec é falsa."""
        os1 = self._make_os("scheduled")
        cat = self.env["engc.equipment.category"].create({"name": "Cat PWA"})
        marca = self.env["engc.equipment.marca"].create({"name": "Marca PWA"})
        equip = self.env["engc.equipment"].create({
            "name": "Autoclave PWA", "category_id": cat.id,
            "marca_id": marca.id, "model": "M1",
            "serial_number": "SN-PWA",
        })
        self._make_visita(os1, self.d1, self.emp_tec, time_start=8.0,
                          time_stop=12.0, equipment_ids=[(6, 0, [equip.id])])
        v2 = self._make_visita(os1, self.d1, self.emp_outro, time_start=14.0,
                               time_stop=16.0,
                               equipment_ids=[(6, 0, [equip.id])])
        with self.assertRaises(ValidationError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v2.id, {"time_start": 10.0, "time_stop": 11.0})
