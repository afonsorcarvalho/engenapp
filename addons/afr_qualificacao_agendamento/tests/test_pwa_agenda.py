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
            "is_tecnico": True,
        })
        cls.emp_outro = cls.env["hr.employee"].create({
            "name": "Téc Outro", "is_tecnico": True,
        })
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
        v1 = self._make_visita(os1, self.d1, self.emp_tec)
        v2 = self._make_visita(os1, self.d_fora, self.emp_tec)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            fields.Date.to_string(self.hoje),
            fields.Date.to_string(self.hoje + timedelta(days=10)),
            False,
        )
        # Escopado às visitas que este teste criou: `qualificacao-dev` tem
        # outras visitas reais dentro de janelas de 14 dias (dado de dev
        # semeado para o dono do produto testar), então "sou a única linha
        # devolvida" não é uma afirmação verdadeira nem deveria ser.
        ids = {v["id"] for v in data["visitas"]}
        self.assertIn(v1.id, ids)
        self.assertNotIn(v2.id, ids)

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
        v = self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=True)
        self.assertFalse(data["my_employee_id"])
        # Escopado: a prova de que `only_mine` foi ignorado é a visita deste
        # teste aparecer no resultado, não o resultado ter exatamente 1 linha
        # — o banco de dev tem outras visitas reais na mesma janela.
        self.assertIn(v.id, [r["id"] for r in data["visitas"]])

    def test_tecnico_ve_visita_de_colega(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d1, self.emp_outro)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            only_mine=False)
        row = next(r for r in data["visitas"] if r["id"] == v.id)
        self.assertFalse(row["is_mine"])

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
        v = self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = next(r for r in data["visitas"] if r["id"] == v.id)
        self.assertTrue(data["can_manage"])
        self.assertTrue(row["editable"])
        self.assertFalse(row["lock_reason"])

    def test_gestor_travado_em_os_em_execucao(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        os1.state = "in_progress"
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = next(r for r in data["visitas"] if r["id"] == v.id)
        self.assertFalse(row["editable"])
        self.assertIn("execução", row["lock_reason"])

    def test_gestor_travado_em_visita_realizada(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        v.state = "done"
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = next(r for r in data["visitas"] if r["id"] == v.id)
        self.assertFalse(row["editable"])
        self.assertIn("realizada", row["lock_reason"])

    def test_conflito_exposto(self):
        os1, os2 = self._make_os(), self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        self._make_visita(os2, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        self.assertTrue(all(v["conflict"] for v in data["visitas"]))
        self.assertTrue(all(v["conflict_msg"] for v in data["visitas"]))

    def test_janela_gigante_e_clampada(self):
        d_from = fields.Date.to_string(self.hoje)
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            d_from, "2100-01-01", False)
        self.assertEqual(
            data["date_to"],
            fields.Date.to_string(
                self.hoje + timedelta(days=self.Visita._PWA_MAX_SPAN_DAYS)),
        )

    def test_data_final_antes_da_inicial_recusa(self):
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
                fields.Date.to_string(self.d2),
                fields.Date.to_string(self.d1),
                False,
            )

    def test_date_from_sem_date_to_usa_janela_a_partir_do_from(self):
        """`d_from + 13`, não `hoje + 13` — os dois só coincidem quando
        `date_from` é omitido."""
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch(
            fields.Date.to_string(self.d1), None, False)
        self.assertEqual(data["date_from"], fields.Date.to_string(self.d1))
        self.assertEqual(
            data["date_to"],
            fields.Date.to_string(self.d1 + timedelta(days=13)),
        )

    def test_sem_permissao_hr_nao_estoura(self):
        """Regressão da delegação hr.employee → hr.employee.public. O técnico
        não lê hr.employee; ler `tecnico_id.name` sem sudo quebra a chamada
        inteira. Já mordeu `is_tecnico` neste módulo e o `engc_os`."""
        os1 = self._make_os()
        self._make_visita(os1, self.d1, self.emp_tec)
        self.assertFalse(self.user_tec.has_group("hr.group_hr_user"))
        data = self.Visita.with_user(self.user_tec).pwa_agenda_fetch()
        self.assertEqual(data["visitas"][0]["tecnico_name"], "Téc Agenda")

    def test_tecnico_options_sem_permissao_hr_nao_estoura(self):
        """Mesma armadilha de `test_sem_permissao_hr_nao_estoura`, agora em
        `pwa_tecnico_options`: um Gestor sem a caixa de HR marcada à mão não
        pode tomar `AccessError` no seletor de técnico da agenda."""
        emp = self.env["hr.employee"].create({
            "name": "Téc Options PWA", "is_tecnico": True,
        })
        self.assertFalse(self.user_gestor.has_group("hr.group_hr_user"))
        opcoes = self.Visita.with_user(self.user_gestor).pwa_tecnico_options()
        self.assertIn(emp.id, [o["id"] for o in opcoes])


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

    def test_hora_fim_zero_recusa(self):
        """`time_stop=0.0` sozinho é falsy: sem a guarda, `stop <= start`
        nunca é avaliado contra o `time_start` atual e o registro grava com
        `planned_hours` desatualizado enquanto `_compute_datetimes` trata
        `time_stop` falsy como fim do dia (23:59) — 4h viram 16h."""
        v = self._visita_editavel()
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"time_stop": 0.0})

    def test_par_de_hora_invertido_recusa(self):
        v = self._visita_editavel()
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"time_start": 15.0, "time_stop": 9.0})

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


class TestPwaAgendaCreateDelete(PwaAgendaCommon):

    def test_tecnico_nao_cria(self):
        os1 = self._make_os("scheduled")
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_tec).pwa_visita_create(
                os1.id, self.emp_tec.id, fields.Date.to_string(self.d1))

    def test_usuario_nao_cria(self):
        os1 = self._make_os("scheduled")
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_usr).pwa_visita_create(
                os1.id, self.emp_tec.id, fields.Date.to_string(self.d1))

    def test_gestor_cria_e_recebe_linha(self):
        os1 = self._make_os("scheduled")
        row = self.Visita.with_user(self.user_gestor).pwa_visita_create(
            os1.id, self.emp_tec.id, fields.Date.to_string(self.d1))
        self.assertTrue(row["id"])
        self.assertEqual(row["os_id"], os1.id)
        self.assertEqual(row["tecnico_id"], self.emp_tec.id)
        self.assertTrue(row["editable"])

    def test_gestor_nao_cria_em_os_em_execucao(self):
        """`create()` não tem a trava de `write()`/`unlink()`, e
        `board_os_options` oferece OS `in_progress`. Sem este guard, a
        visita nasceria travada para sempre (nem edita, nem apaga)."""
        os1 = self._make_os("in_progress")
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_create(
                os1.id, self.emp_tec.id, fields.Date.to_string(self.d1))

    def test_tecnico_nao_apaga(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_tec).pwa_visita_delete(v.id)

    def test_gestor_apaga(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        self.assertTrue(
            self.Visita.with_user(self.user_gestor).pwa_visita_delete(v.id))
        self.assertFalse(v.exists())

    def test_nao_apaga_visita_realizada(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        v.state = "done"
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_delete(v.id)

    def test_nao_apaga_visita_de_os_em_execucao(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        os1.state = "in_progress"
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_delete(v.id)


class TestPwaAgendaInstrumento(PwaAgendaCommon):

    @classmethod
    def _instrumento(cls, nome, validade=None):
        """Instrumento com, opcionalmente, um certificado válido até `validade`."""
        inst = cls.env["engc.calibration.instruments"].create({"name": nome})
        if validade:
            cls.env["engc.calibration.instruments.certificates"].create({
                "instrument_id": inst.id,
                "validate_calibration": validade,
            })
        return inst

    def test_serializer_devolve_ids_de_instrumento(self):
        os1 = self._make_os()
        i1 = self._instrumento("INS-A")
        i2 = self._instrumento("INS-B")
        v = self._make_visita(os1, self.d1, self.emp_tec,
                              instrument_ids=[(6, 0, [i1.id, i2.id])])
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = next(r for r in data["visitas"] if r["id"] == v.id)
        self.assertIn("instrument_ids", row)
        self.assertEqual(sorted(row["instrument_ids"]), sorted([i1.id, i2.id]))
        # Os nomes continuam vindo; uma chave não substitui a outra.
        self.assertEqual(len(row["instrument_list"]), 2)

    def test_visita_sem_instrumento_devolve_lista_vazia(self):
        os1 = self._make_os()
        v = self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        row = next(r for r in data["visitas"] if r["id"] == v.id)
        self.assertEqual(row["instrument_ids"], [])

    def test_options_traz_maior_validade(self):
        """`validade` é a maior data entre os certificados: se ela não alcança
        o dia, nenhum certificado alcança."""
        inst = self._instrumento("INS-VAL")
        self.env["engc.calibration.instruments.certificates"].create({
            "instrument_id": inst.id, "validate_calibration": "2026-01-31",
        })
        self.env["engc.calibration.instruments.certificates"].create({
            "instrument_id": inst.id, "validate_calibration": "2027-06-30",
        })
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        row = next(o for o in opts if o["id"] == inst.id)
        self.assertEqual(row["validade"], "2027-06-30")

    def test_options_sem_certificado_devolve_validade_falsa(self):
        inst = self._instrumento("INS-SEM-CERT")
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        row = next(o for o in opts if o["id"] == inst.id)
        self.assertFalse(row["validade"])

    def test_options_chaves(self):
        inst = self._instrumento("INS-CHAVES")
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        row = next(o for o in opts if o["id"] == inst.id)
        for k in ("id", "name", "validade"):
            self.assertIn(k, row)

    def test_options_sem_permissao_hr_nao_estoura(self):
        """Espelha `test_tecnico_options_sem_permissao_hr_nao_estoura`. Aqui
        não deve haver `sudo` — `engc.calibration.instruments` é legível por
        `base.group_user` —, mas o teste ancora que a chamada funciona para
        quem não tem HR, que é o caso do Gestor recém-criado."""
        self._instrumento("INS-HR")
        self.assertFalse(self.user_gestor.has_group("hr.group_hr_user"))
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        self.assertTrue(opts)

    def test_options_sem_rotulo_ganha_fallback(self):
        """`tag`, `id_number` e `name` vazios não podem sair `False` — o TS
        declara `name: string`, e `_pwa_serialize` já cobre esse caso no
        `instrument_list` filtrando; aqui não há filtro, então precisa de
        rótulo de fallback legível."""
        inst = self.env["engc.calibration.instruments"].create({"name": False})
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        row = next(o for o in opts if o["id"] == inst.id)
        self.assertEqual(row["name"], "Instrumento #%s" % inst.id)

    def test_options_ordenados_por_tag(self):
        """Sem `_order` no model, `search([])` sairia em ordem de id — a
        lista trocaria de posição a cada instrumento novo. Ordenar por
        `tag, id_number, name` no `search` resolve sem depender do model
        compartilhado (`engc.calibration.instruments`, usado fora desta
        feature)."""
        i_b = self.env["engc.calibration.instruments"].create({
            "name": "N-B", "tag": "B-TAG-ORDER",
        })
        i_a = self.env["engc.calibration.instruments"].create({
            "name": "N-A", "tag": "A-TAG-ORDER",
        })
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        ordem = [o["id"] for o in opts if o["id"] in (i_a.id, i_b.id)]
        self.assertEqual(ordem, [i_a.id, i_b.id])

    def test_options_visivel_ao_tecnico(self):
        """Leitura é global na agenda; o método não tem guard de Gestor."""
        self._instrumento("INS-TEC")
        opts = self.Visita.with_user(self.user_tec).pwa_instrumento_options()
        self.assertTrue(opts)

    def test_gestor_grava_instrumentos(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        i1 = self._instrumento("INS-W1")
        i2 = self._instrumento("INS-W2")
        row = self.Visita.with_user(self.user_gestor).pwa_visita_update(
            v.id, {"instrument_ids": [i1.id, i2.id]})
        self.assertEqual(sorted(v.instrument_ids.ids), sorted([i1.id, i2.id]))
        self.assertEqual(sorted(row["instrument_ids"]), sorted([i1.id, i2.id]))

    def test_lista_vazia_desliga_todos(self):
        os1 = self._make_os("scheduled")
        i1 = self._instrumento("INS-OFF")
        v = self._make_visita(os1, self.d1, self.emp_tec,
                              instrument_ids=[(6, 0, [i1.id])])
        self.Visita.with_user(self.user_gestor).pwa_visita_update(
            v.id, {"instrument_ids": []})
        self.assertFalse(v.instrument_ids)

    def test_recusa_tupla_de_comando(self):
        """Um `(0, 0, {...})` criaria instrumento novo pela porta da agenda."""
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"instrument_ids": [(0, 0, {"name": "FORJADO"})]})

    def test_recusa_valor_nao_lista(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        for ruim in ("abc", 7, {"id": 1}, [1, "dois"]):
            with self.assertRaises(UserError):
                self.Visita.with_user(self.user_gestor).pwa_visita_update(
                    v.id, {"instrument_ids": ruim})

    def test_tecnico_barrado(self):
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        i1 = self._instrumento("INS-BARRA")
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_tec).pwa_visita_update(
                v.id, {"instrument_ids": [i1.id]})

    def test_os_em_execucao_recusa(self):
        """`instrument_ids` está em `_SCHEDULE_FIELDS`, então a trava de estado
        da OS vale de graça — não é código novo, é o `write()` do modelo."""
        os1 = self._make_os("scheduled")
        v = self._make_visita(os1, self.d1, self.emp_tec)
        i1 = self._instrumento("INS-TRAVA")
        v.os_id.state = "in_progress"
        with self.assertRaises(UserError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v.id, {"instrument_ids": [i1.id]})
