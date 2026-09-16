# -*- coding: utf-8 -*-
"""Agenda de visitas no PWA Técnico — papéis, serializer e mutações `pwa_*`.

Técnico é leitor; só o Gestor cria, edita e apaga. O guard vive no servidor
porque o proxy `/api/odoo` do PWA repassa `call_kw` sem allowlist de método:
esconder o botão não protege nada.
"""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
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
