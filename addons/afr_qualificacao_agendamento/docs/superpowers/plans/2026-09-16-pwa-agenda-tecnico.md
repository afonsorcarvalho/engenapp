# Agenda de Visitas no PWA Técnico — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao técnico em campo uma aba "Agenda" no PWA que mostra as visitas de `afr.qualificacao.os.visita`, com criação/edição/exclusão liberadas apenas para o Gestor.

**Architecture:** Backend novo mora em `afr_qualificacao_agendamento/models/os_visita.py`, num bloco de métodos `@api.model` prefixados `pwa_` (os `board_*` existentes servem o board OWL e ficam intocados). Toda decisão de permissão e de tempo é do servidor: o guard é `_check_manager_only` do mixin de `afr_qualificacao`, e a janela de datas nasce de `fields.Date.context_today`. O front é uma rota nova em `afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/`, que consome um único payload já decidido e só pinta o resultado.

**Tech Stack:** Odoo 16.0 (Python, `TransactionCase`), Next.js 14 App Router, React 18, TypeScript, `@tanstack/react-query` v5, zustand, Tailwind, vitest + @testing-library/react.

**Spec:** `addons/afr_qualificacao_agendamento/docs/superpowers/specs/2026-09-16-pwa-agenda-tecnico-design.md`

## Global Constraints

- **Repo:** monorepo `odoo_engenapp`, branch `main-monorepo`. `afr_qualificacao_agendamento` **não** é submodule (confira `.gitmodules`); commite a partir de `/home/afonso/docker/odoo_engenapp`. `afr_qualificacao` **é** submodule — commite de dentro de `addons/afr_qualificacao/` e `git push origin main` ANTES de qualquer bump de pointer.
- **Commits sempre via agente `git-commit-push` (haiku)**, nunca `git commit` direto.
- **Container Odoo:** `odoo_engenapp-web-qualificacao-1`, banco `qualificacao-dev`, binário `/opt/odoo/venv/bin/odoo`, db host interno `db-qualificacao`. Não usar `odoo-bin`. O comando completo, já verificado, está em cada task — as flags `--db_host/--db_user/--db_password` são obrigatórias.
- **Baseline levantado em 2026-09-16, antes desta feature.** `afr_qualificacao_agendamento`: **0 failed / 0 error** (56 testes). `afr_qualificacao`: **1 failed** — `TestResourcePlan.test_fleet_single_logger_two_temp_standards`, falha pré-existente por poluição de dados no banco de dev (pega o validador real "Qualificador 0001" em vez do transitório do teste). Qualquer falha além dessa é regressão desta feature.
- **Técnico não lê `hr.employee`** no Odoo 16. Qualquer leitura de `tecnico_id.name` tem que passar por `sudo()`, ou a delegação para `hr.employee.public` estoura. Esta armadilha já mordeu este módulo (`is_tecnico`) e o `engc_os`.
- **O front nunca chama `Date.now()`/`new Date()` para decidir "hoje".** A janela vem de `server_today` no payload.
- **Bump de versão:** `afr_qualificacao_agendamento/__manifest__.py` vai de `16.0.1.0.1` para `16.0.1.1.0` (feat), uma vez só, na Task 4. Mudança só de front **não** bumpa manifest.
- **Nenhuma trava de agendamento existente é relaxada** — nem para o Gestor.
- Código, identificadores e mensagens de commit em inglês; strings de UI e docstrings em pt-BR, como o resto dos dois módulos.

## File Structure

**Backend (`addons/afr_qualificacao_agendamento/`)**

| Arquivo | Responsabilidade |
|---|---|
| `security/ir.model.access.csv` (modificar) | Técnico vira leitor: `1,1,0,0` → `1,0,0,0`. |
| `models/os_visita.py` (modificar) | Herdar o mixin de guard; bloco novo `# ───────── PWA Técnico ─────────` no fim da classe, com `_pwa_lock_reason`, `_pwa_serialize`, `pwa_agenda_fetch`, `pwa_visita_update`, `pwa_visita_create`, `pwa_visita_delete`. |
| `tests/test_pwa_agenda.py` (criar) | Matriz de papel, serializer, janela, travas. |
| `tests/__init__.py` (modificar) | Importar o módulo de teste novo. |
| `__manifest__.py` (modificar) | Bump de versão. |

**Front (`addons/afr_qualificacao/pwa/`)**

| Arquivo | Responsabilidade |
|---|---|
| `lib/odoo/agenda.ts` (criar) | Tipos do payload e wrappers RPC. Só transporte, zero regra. |
| `lib/hooks/useAgenda.ts` (criar) | Queries e mutações react-query, incluindo invalidação cruzada. |
| `app/tecnico/qualificacao/agenda/page.tsx` (criar) | Tela: janela, toggle, agrupamento por dia. |
| `app/tecnico/qualificacao/_components/VisitaCard.tsx` (criar) | Card de uma visita, inclusive o estado travado. |
| `app/tecnico/qualificacao/_components/VisitaSheet.tsx` (criar) | Folha de edição/criação/exclusão (só Gestor). |
| `components/ui/BottomSheet.tsx` (criar) | Folha genérica vinda de baixo. Não existe Modal genérico no projeto. |
| `app/tecnico/qualificacao/_components/TecnicoNav.tsx` (modificar) | 4º destino, escondível por prop. Continua componente puro — a consulta fica no layout. |
| `app/tecnico/qualificacao/layout.tsx` (modificar) | Resolve `useAgendaDisponivel()` uma vez e passa às duas variantes da nav. |
| `app/tecnico/qualificacao/__tests__/TecnicoNav.test.tsx` (modificar) | O teste atual afirma "os três destinos" — quebra de propósito. |

---

### Task 1: Técnico vira leitor + guard de Gestor no modelo

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/security/ir.model.access.csv:2`
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py:17-19`
- Create: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py`
- Modify: `addons/afr_qualificacao_agendamento/tests/__init__.py`

**Interfaces:**
- Consumes: `afr.qualificacao.manager.guard.mixin` de `afr_qualificacao` (método `_check_manager_only(acao)`, levanta `UserError` para quem não é Gestor, retorna cedo em `self.env.su`).
- Produces: a classe base de teste `PwaAgendaCommon` (usada pelas Tasks 2–4) e o fato de que `afr.qualificacao.os.visita` responde a `_check_manager_only`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py`:

```python
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
```

Registrar em `addons/afr_qualificacao_agendamento/tests/__init__.py`, na última linha:

```python
from . import test_pwa_agenda
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento:TestPwaAgendaAcl \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'
```

Esperado: FAIL em `test_tecnico_nao_escreve_visita` e `test_tecnico_nao_apaga_visita` (a ACL ainda dá write ao técnico), e ERROR nos três `test_guard_*` com `AttributeError: '_check_manager_only'`.

> Comando verificado em 2026-09-16 na forma de módulo inteiro (`--test-tags afr_qualificacao_agendamento`). O seletor de classe (`/módulo:Classe`) é do Odoo 16 e deve funcionar; se não filtrar, rode o módulo inteiro e leia as linhas `FAIL:`/`ERROR:` da classe em questão.

- [ ] **Step 3: Apertar a ACL**

Em `addons/afr_qualificacao_agendamento/security/ir.model.access.csv`, trocar a linha do técnico (a 2ª, logo após o cabeçalho) por:

```csv
access_afr_qualificacao_os_visita_technician,afr.qualificacao.os.visita.technician,model_afr_qualificacao_os_visita,afr_qualificacao.group_afr_qualificacao_technician,1,0,0,0
```

As linhas de `user` (`1,1,1,0`) e `manager` (`1,1,1,1`) **não mudam** — o board OWL do backend depende delas.

- [ ] **Step 4: Herdar o mixin de guard**

Em `addons/afr_qualificacao_agendamento/models/os_visita.py`, na declaração da classe:

```python
class AfrQualificacaoOsVisita(models.Model):
    _name = "afr.qualificacao.os.visita"
    _inherit = "afr.qualificacao.manager.guard.mixin"
    _description = "Visita de OS de Qualificação"
    _order = "date, time_start, id"
```

- [ ] **Step 5: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 7 testes, 0 failed, 0 error.

- [ ] **Step 6: Rodar a suíte INTEIRA dos dois módulos**

Apertar uma ACL viva é o risco desta task. O teste novo não prova nada sozinho.

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'

docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao \
  --test-enable --test-tags /afr_qualificacao \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'
```

Esperado: nenhuma falha nova em relação ao baseline. **Se aparecer falha nova, pare e relate** — significa que existe um fluxo que escreve visita como técnico, e a decisão de produto precisa ser revista antes de seguir.

- [ ] **Step 7: Commit**

Delegar ao agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`, staging só destes paths:

```
addons/afr_qualificacao_agendamento/security/ir.model.access.csv
addons/afr_qualificacao_agendamento/models/os_visita.py
addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py
addons/afr_qualificacao_agendamento/tests/__init__.py
```

```
feat(agendamento): make technician read-only on visits, add manager guard

The technician group had write on afr.qualificacao.os.visita with no
ir.rule behind it, so any technician could rewrite any colleague's visit
through a direct call_kw. Visits are now read-only for technicians; the
model inherits afr.qualificacao.manager.guard.mixin so the upcoming PWA
methods can gate writes on the manager group server-side.
```

---

### Task 2: `pwa_agenda_fetch` — leitura da agenda

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py` (bloco novo no fim da classe)
- Modify: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py` (classe nova)

**Interfaces:**
- Consumes: `PwaAgendaCommon` da Task 1; `_OS_UNLOCKED_STATES` (frozenset `("draft", "scheduled")`, já no modelo); `_compute_conflicts` / `_compute_resource_conflicts` (já no modelo).
- Produces:
  - `_pwa_lock_reason(self, is_manager) -> str | False`
  - `_pwa_serialize(self, is_manager, my_employee_id) -> dict`
  - `pwa_agenda_fetch(self, date_from=None, date_to=None, only_mine=True) -> dict`
  As Tasks 3 e 4 devolvem exatamente o dict de `_pwa_serialize`.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao fim de `tests/test_pwa_agenda.py`:

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento:TestPwaAgendaFetch \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'
```

Esperado: todos com `AttributeError: 'afr.qualificacao.os.visita' object has no attribute 'pwa_agenda_fetch'`.

- [ ] **Step 3: Implementar**

No fim da classe em `models/os_visita.py`, após `board_create_visita`:

```python
    # ───────── PWA Técnico ─────────
    # Os `board_*` acima servem o board OWL do backend e devolvem a agenda
    # inteira da equipe. Os `pwa_*` abaixo servem o app de campo: janela
    # escopada, decisão de permissão embutida e o servidor como dono do
    # relógio.
    _PWA_WINDOW_DAYS = 14

    def _pwa_lock_reason(self, is_manager):
        """Por que esta visita NÃO é editável no PWA — ou False se for.

        A ordem importa: quem não é Gestor recebe sempre a mesma frase, sem
        vazar em que estado a OS do colega está.
        """
        self.ensure_one()
        if not is_manager:
            return _("Somente o Gestor edita a agenda.")
        if self.state == "done":
            return _("Visita já realizada.")
        if self.os_id.state not in self._OS_UNLOCKED_STATES:
            label = dict(
                self.os_id._fields["state"].selection
            ).get(self.os_id.state, self.os_id.state)
            return _("OS em execução (%s).") % label
        return False

    def _pwa_serialize(self, is_manager, my_employee_id):
        """Uma visita como o PWA a consome. Chamar sobre recordset em sudo."""
        self.ensure_one()
        msgs = [m for m in (
            self.tecnico_conflict_msg, self.travel_conflict_msg,
            self.instrument_conflict_msg, self.calibration_conflict_msg,
        ) if m]
        lock = self._pwa_lock_reason(is_manager)
        return {
            "id": self.id,
            "date": fields.Date.to_string(self.date),
            "time_start": self.time_start,
            "time_stop": self.time_stop,
            "planned_hours": round(self.planned_hours, 2),
            "os_id": self.os_id.id or False,
            "os_name": self.os_id.name or "",
            "os_state": self.os_id.state or False,
            "partner_name": self.partner_id.name or "",
            "city": self.city or "",
            "equipment_list": list(filter(None, self.equipment_ids.mapped(
                lambda e: e.apelido or e.tag or e.name
            ))),
            "instrument_list": list(filter(None, self.instrument_ids.mapped(
                lambda i: i.tag or i.id_number or i.name
            ))),
            "tecnico_id": self.tecnico_id.id or False,
            "tecnico_name": self.tecnico_id.name or "",
            "is_mine": bool(
                my_employee_id and self.tecnico_id.id == my_employee_id
            ),
            "state": self.state,
            "overflow": self.overflow_next_day,
            "editable": not lock,
            "lock_reason": lock,
            "conflict": bool(
                self.tecnico_conflict or self.travel_conflict
                or self.instrument_conflict or self.calibration_conflict
            ),
            "conflict_msg": " | ".join(msgs),
            "note": self.note or "",
        }

    @api.model
    def pwa_agenda_fetch(self, date_from=None, date_to=None, only_mine=True):
        """Agenda do PWA. Leitura liberada aos três grupos (a ACL já barra
        quem não pertence a nenhum).

        Datas vazias: o SERVIDOR define a janela. O relógio do aparelho é
        fonte conhecida de defeito neste app — o payload devolve
        `server_today` e o front navega a partir dele.
        """
        today = fields.Date.context_today(self)
        d_from = fields.Date.to_date(date_from) if date_from else today
        d_to = (
            fields.Date.to_date(date_to) if date_to
            else d_from + timedelta(days=self._PWA_WINDOW_DAYS - 1)
        )
        is_manager = self.env.user.has_group(
            "afr_qualificacao.group_afr_qualificacao_manager"
        )
        # `employee_id` exige leitura de hr.employee, que o técnico não tem.
        my_employee_id = self.env.user.sudo().employee_id.id or False
        domain = [("date", ">=", d_from), ("date", "<=", d_to)]
        # Sem empregado vinculado (caso do Gestor administrativo), `only_mine`
        # não tem por onde filtrar: devolve tudo em vez de uma tela vazia.
        if only_mine and my_employee_id:
            domain.append(("tecnico_id", "=", my_employee_id))
        # Busca com os direitos do usuário (a ACL de leitura vale); serializa
        # em sudo por causa de `tecnico_id.name` — hr.employee delega para
        # hr.employee.public quando o usuário não tem permissão em HR, e a
        # leitura direta estoura.
        visitas = self.search(domain, order="date, time_start, id")
        return {
            "server_today": fields.Date.to_string(today),
            "date_from": fields.Date.to_string(d_from),
            "date_to": fields.Date.to_string(d_to),
            "my_employee_id": my_employee_id,
            "can_manage": is_manager,
            "visitas": [
                v._pwa_serialize(is_manager, my_employee_id)
                for v in visitas.sudo()
            ],
        }
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 12 testes, 0 failed, 0 error.

- [ ] **Step 5: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`, staging só de `models/os_visita.py` e `tests/test_pwa_agenda.py` do módulo agendamento.

```
feat(agendamento): add pwa_agenda_fetch for the technician app

Returns a scoped visit window plus the permission decision already made:
editable/lock_reason are computed server-side so the client never
reimplements the rule. The server owns the date window (server_today in
the payload) because the device clock has burned this app before.
Serialization runs sudo: reading tecnico_id.name as a technician trips
the hr.employee to hr.employee.public delegation.
```

---

### Task 3: `pwa_visita_update` — editar visita

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py`
- Modify: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py`

**Interfaces:**
- Consumes: `_pwa_serialize`, `_check_manager_only`, `_board_check_not_done` (já existe, levanta `UserError` em visita `done`).
- Produces: `pwa_visita_update(self, visita_id, vals) -> dict` (o mesmo dict de `_pwa_serialize`) e `_PWA_WRITABLE_FIELDS`.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao fim de `tests/test_pwa_agenda.py`:

```python
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
        equip = self.env["engc.equipment"].create({"name": "Autoclave PWA"})
        self._make_visita(os1, self.d1, self.emp_tec, time_start=8.0,
                          time_stop=12.0, equipment_ids=[(6, 0, [equip.id])])
        v2 = self._make_visita(os1, self.d1, self.emp_outro, time_start=14.0,
                               time_stop=16.0,
                               equipment_ids=[(6, 0, [equip.id])])
        with self.assertRaises(ValidationError):
            self.Visita.with_user(self.user_gestor).pwa_visita_update(
                v2.id, {"time_start": 10.0, "time_stop": 11.0})
```

Acrescentar `ValidationError` ao import de exceções no topo do arquivo:

```python
from odoo.exceptions import AccessError, UserError, ValidationError
```

> `engc.equipment` pode exigir campos além de `name` neste banco. Se o
> `create` falhar, descubra os obrigatórios com
> `self.env["engc.equipment"].fields_get()` (ou copie o idioma de
> `tests/test_resource_conflict.py`, que já monta equipamentos) e ajuste
> **só o create**, nunca a asserção.

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento:TestPwaAgendaUpdate \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'
```

Esperado: `AttributeError` em `pwa_visita_update` em todos.

- [ ] **Step 3: Implementar**

Após `pwa_agenda_fetch` em `models/os_visita.py`:

```python
    # Campos que a agenda do PWA pode gravar. `planned_hours` fica de fora de
    # propósito: é derivado do par início/fim, não digitado.
    _PWA_WRITABLE_FIELDS = frozenset({
        "date", "time_start", "time_stop", "tecnico_id", "note",
    })

    @api.model
    def pwa_visita_update(self, visita_id, vals):
        """Edita uma visita a partir da agenda do PWA. Só Gestor.

        Sem `sudo` no write: o Gestor tem write de verdade, e é justamente o
        `write()` do modelo que carrega a trava de estado da OS que queremos
        honrar. Um sudo aqui contornaria a própria regra que a spec preserva.
        """
        self._check_manager_only(_("editar a agenda de visitas"))
        extra = set(vals) - self._PWA_WRITABLE_FIELDS
        if extra:
            raise UserError(_(
                "Campo(s) não editável(is) pela agenda: %s."
            ) % ", ".join(sorted(extra)))
        visita = self.browse(visita_id)
        visita._board_check_not_done()
        vals = dict(vals)
        start = vals.get("time_start", visita.time_start)
        stop = vals.get("time_stop", visita.time_stop)
        if ("time_start" in vals or "time_stop" in vals) and stop > start:
            vals["planned_hours"] = stop - start
        visita.write(vals)
        my_employee_id = self.env.user.sudo().employee_id.id or False
        return visita.sudo()._pwa_serialize(True, my_employee_id)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 10 testes, 0 failed, 0 error.

Se `test_sobreposicao_de_equipamento_dispara_por_hora` falhar porque a constraint **não** dispara, **pare e relate**: o conserto (acrescentar `time_start`/`time_stop` ao `@api.constrains` de `_check_equipment_overlap`) é mudança de regra existente e precisa de aval antes.

- [ ] **Step 5: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`.

```
feat(agendamento): add pwa_visita_update, manager only

Hard whitelist of writable keys (date, time_start, time_stop, tecnico_id,
note) so the endpoint cannot reach os_id or state. planned_hours is
derived from the start/stop pair rather than accepted from the client.
The write is not sudo on purpose: the model's write() is where the
OS-state lock lives, and bypassing it would defeat the rule the spec
keeps.
```

---

### Task 4: `pwa_visita_create` / `pwa_visita_delete` + bump de versão

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py`
- Modify: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py`
- Modify: `addons/afr_qualificacao_agendamento/__manifest__.py:4`

**Interfaces:**
- Consumes: `_pwa_serialize`, `_check_manager_only`, `_board_check_not_done`.
- Produces: `pwa_visita_create(self, os_id, tecnico_id, date) -> dict`; `pwa_visita_delete(self, visita_id) -> True`. Fecha o contrato backend que a Task 5 consome.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao fim de `tests/test_pwa_agenda.py`:

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable \
  --test-tags /afr_qualificacao_agendamento:TestPwaAgendaCreateDelete \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'
```

Esperado: `AttributeError` em `pwa_visita_create` / `pwa_visita_delete`.

- [ ] **Step 3: Implementar**

Após `pwa_visita_update` em `models/os_visita.py`:

```python
    @api.model
    def pwa_visita_create(self, os_id, tecnico_id, date):
        """Cria visita mínima pela agenda do PWA. Só Gestor.

        Mesmo conjunto de campos do `board_create_visita`; os seletores da
        tela vêm de `board_os_options` e `board_technician_options`.
        """
        self._check_manager_only(_("criar visita pela agenda"))
        visita = self.create({
            "os_id": os_id, "tecnico_id": tecnico_id, "date": date,
        })
        my_employee_id = self.env.user.sudo().employee_id.id or False
        return visita.sudo()._pwa_serialize(True, my_employee_id)

    @api.model
    def pwa_visita_delete(self, visita_id):
        """Apaga visita pela agenda do PWA. Só Gestor. O `unlink()` do modelo
        ainda recusa OS fora de draft/scheduled."""
        self._check_manager_only(_("apagar visita pela agenda"))
        visita = self.browse(visita_id)
        visita._board_check_not_done()
        visita.unlink()
        return True
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 7 testes, 0 failed, 0 error.

- [ ] **Step 5: Bump de versão**

Em `addons/afr_qualificacao_agendamento/__manifest__.py`:

```python
    "version": "16.0.1.1.0",
```

- [ ] **Step 6: Rodar a suíte inteira do módulo**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats'
```

Esperado: nenhuma falha nova em relação ao baseline.

- [ ] **Step 7: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`.

```
feat(agendamento): add pwa_visita_create/delete and bump to 16.0.1.1.0

Both are manager-gated and reuse board_os_options/board_technician_options
for the pickers. Delete still honours the model's unlink lock, so a visit
belonging to an OS already in execution cannot be removed from the field.
```

---

### Task 5: Camada de dados do front

**Files:**
- Create: `addons/afr_qualificacao/pwa/lib/odoo/agenda.ts`
- Create: `addons/afr_qualificacao/pwa/lib/hooks/useAgenda.ts`
- Create: `addons/afr_qualificacao/pwa/lib/odoo/__tests__/agenda.test.ts`

**Interfaces:**
- Consumes: `odooClient` de `lib/odoo/client` — `callKw(model, method, args, kwargs)` e `searchCount(model, domain)`. O contrato do backend é o das Tasks 2–4.
- Produces:
  - `VisitaAgenda`, `AgendaPayload` (tipos)
  - `fetchAgenda(dateFrom, dateTo, onlyMine)`, `agendaDisponivel()`, `updateVisita(id, vals)`, `createVisita(osId, tecnicoId, date)`, `deleteVisita(id)`, `listTecnicoOptions()`, `listOsOptions()`
  - hooks `useAgenda(dateFrom, dateTo, onlyMine)`, `useAgendaDisponivel()`, `useUpdateVisita()`, `useCreateVisita()`, `useDeleteVisita()`

- [ ] **Step 1: Escrever o teste que falha**

Criar `lib/odoo/__tests__/agenda.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const callKw = vi.fn()
const searchCount = vi.fn()

vi.mock('../client', () => ({
  default: { callKw: (...a: unknown[]) => callKw(...a), searchCount: (...a: unknown[]) => searchCount(...a) },
}))

import { fetchAgenda, agendaDisponivel, updateVisita, createVisita, deleteVisita } from '../agenda'

const MODEL = 'afr.qualificacao.os.visita'

describe('agenda RPC', () => {
  beforeEach(() => {
    callKw.mockReset()
    searchCount.mockReset()
  })

  it('fetchAgenda passa as datas como kwargs nomeados', async () => {
    callKw.mockResolvedValue({ visitas: [] })
    await fetchAgenda('2026-09-16', '2026-09-29', true)
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_agenda_fetch', [], {
      date_from: '2026-09-16',
      date_to: '2026-09-29',
      only_mine: true,
    })
  })

  it('fetchAgenda sem datas deixa o servidor decidir a janela', async () => {
    callKw.mockResolvedValue({ visitas: [] })
    await fetchAgenda(null, null, false)
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_agenda_fetch', [], {
      date_from: null,
      date_to: null,
      only_mine: false,
    })
  })

  it('agendaDisponivel é falso quando o modelo não existe', async () => {
    searchCount.mockResolvedValue(0)
    expect(await agendaDisponivel()).toBe(false)
    expect(searchCount).toHaveBeenCalledWith('ir.model', [['model', '=', MODEL]])
  })

  it('agendaDisponivel é verdadeiro quando o modelo existe', async () => {
    searchCount.mockResolvedValue(1)
    expect(await agendaDisponivel()).toBe(true)
  })

  it('updateVisita manda id e vals posicionais', async () => {
    callKw.mockResolvedValue({ id: 7 })
    await updateVisita(7, { note: 'x' })
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_visita_update', [7, { note: 'x' }])
  })

  it('createVisita manda os/tecnico/data posicionais', async () => {
    callKw.mockResolvedValue({ id: 8 })
    await createVisita(3, 44, '2026-09-20')
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_visita_create', [3, 44, '2026-09-20'])
  })

  it('deleteVisita manda o id posicional', async () => {
    callKw.mockResolvedValue(true)
    await deleteVisita(9)
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_visita_delete', [9])
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa
npx vitest run lib/odoo/__tests__/agenda.test.ts
```

Esperado: FAIL — `Failed to resolve import "../agenda"`.

- [ ] **Step 3: Implementar `lib/odoo/agenda.ts`**

```ts
/**
 * Agenda de visitas — transporte RPC puro. Zero regra de negócio: quem
 * decide o que é editável, e qual é a janela de datas, é o servidor
 * (`pwa_agenda_fetch`).
 */
import odooClient from './client'

export const VISITA_MODEL = 'afr.qualificacao.os.visita'

export interface VisitaAgenda {
  id: number
  date: string
  time_start: number
  time_stop: number
  planned_hours: number
  os_id: number | false
  os_name: string
  os_state: string | false
  partner_name: string
  city: string
  equipment_list: string[]
  instrument_list: string[]
  tecnico_id: number | false
  tecnico_name: string
  is_mine: boolean
  state: 'planned' | 'done'
  overflow: boolean
  editable: boolean
  /** Frase pronta do servidor quando `editable` é falso. */
  lock_reason: string | false
  conflict: boolean
  conflict_msg: string
  note: string
}

export interface AgendaPayload {
  server_today: string
  date_from: string
  date_to: string
  my_employee_id: number | false
  can_manage: boolean
  visitas: VisitaAgenda[]
}

export interface VisitaVals {
  date?: string
  time_start?: number
  time_stop?: number
  tecnico_id?: number
  note?: string
}

export interface Opcao {
  id: number
  name: string
}

export async function fetchAgenda(
  dateFrom: string | null,
  dateTo: string | null,
  onlyMine: boolean,
): Promise<AgendaPayload> {
  return odooClient.callKw<AgendaPayload>(VISITA_MODEL, 'pwa_agenda_fetch', [], {
    date_from: dateFrom,
    date_to: dateTo,
    only_mine: onlyMine,
  })
}

/**
 * O PWA é publicado dentro de `afr_qualificacao`, mas o modelo de visita vive
 * em `afr_qualificacao_agendamento`, que DEPENDE de `afr_qualificacao`. A
 * dependência aponta ao contrário do uso, então a aba não pode ser assumida.
 */
export async function agendaDisponivel(): Promise<boolean> {
  const n = await odooClient.searchCount('ir.model', [['model', '=', VISITA_MODEL]])
  return n > 0
}

export async function updateVisita(id: number, vals: VisitaVals): Promise<VisitaAgenda> {
  return odooClient.callKw<VisitaAgenda>(VISITA_MODEL, 'pwa_visita_update', [id, vals])
}

export async function createVisita(
  osId: number,
  tecnicoId: number,
  date: string,
): Promise<VisitaAgenda> {
  return odooClient.callKw<VisitaAgenda>(VISITA_MODEL, 'pwa_visita_create', [osId, tecnicoId, date])
}

export async function deleteVisita(id: number): Promise<boolean> {
  return odooClient.callKw<boolean>(VISITA_MODEL, 'pwa_visita_delete', [id])
}

export async function listTecnicoOptions(): Promise<Opcao[]> {
  return odooClient.callKw<Opcao[]>(VISITA_MODEL, 'board_technician_options', [])
}

export async function listOsOptions(): Promise<Opcao[]> {
  return odooClient.callKw<Opcao[]>(VISITA_MODEL, 'board_os_options', [])
}
```

- [ ] **Step 4: Rodar e confirmar que passa**

```bash
npx vitest run lib/odoo/__tests__/agenda.test.ts
```

Esperado: 7 passed.

- [ ] **Step 5: Implementar os hooks**

Criar `lib/hooks/useAgenda.ts`:

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAgenda,
  agendaDisponivel,
  updateVisita,
  createVisita,
  deleteVisita,
  listTecnicoOptions,
  listOsOptions,
  type AgendaPayload,
  type VisitaVals,
} from '@/lib/odoo/agenda'

export function useAgendaDisponivel() {
  return useQuery({
    queryKey: ['agenda-disponivel'],
    queryFn: agendaDisponivel,
    staleTime: Infinity,
    retry: false,
  })
}

export function useAgenda(
  dateFrom: string | null,
  dateTo: string | null,
  onlyMine: boolean,
) {
  return useQuery<AgendaPayload>({
    queryKey: ['agenda', dateFrom, dateTo, onlyMine],
    queryFn: () => fetchAgenda(dateFrom, dateTo, onlyMine),
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  })
}

/**
 * Invalida a agenda E a lista de OSs: `date_planned_start`/`date_planned_end`
 * da OS são rollup computado das visitas, e a home mostra esse campo no card.
 */
function useInvalidarAgenda() {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: ['agenda'] })
    qc.invalidateQueries({ queryKey: ['tecnico-os'] })
  }
}

export function useUpdateVisita() {
  const invalidar = useInvalidarAgenda()
  return useMutation({
    mutationFn: ({ id, vals }: { id: number; vals: VisitaVals }) => updateVisita(id, vals),
    onSuccess: invalidar,
  })
}

export function useCreateVisita() {
  const invalidar = useInvalidarAgenda()
  return useMutation({
    mutationFn: ({ osId, tecnicoId, date }: { osId: number; tecnicoId: number; date: string }) =>
      createVisita(osId, tecnicoId, date),
    onSuccess: invalidar,
  })
}

export function useDeleteVisita() {
  const invalidar = useInvalidarAgenda()
  return useMutation({
    mutationFn: (id: number) => deleteVisita(id),
    onSuccess: invalidar,
  })
}

export function useTecnicoOptions(enabled: boolean) {
  return useQuery({
    queryKey: ['agenda-tecnicos'],
    queryFn: listTecnicoOptions,
    staleTime: 5 * 60_000,
    enabled,
  })
}

export function useOsOptions(enabled: boolean) {
  return useQuery({
    queryKey: ['agenda-os'],
    queryFn: listOsOptions,
    staleTime: 5 * 60_000,
    enabled,
  })
}
```

- [ ] **Step 6: Verificar tipos e suíte**

```bash
npx tsc --noEmit
npx vitest run
```

Esperado: `tsc` limpo; vitest sem falha nova em relação ao `pwa/docs/BASELINE.md`.

- [ ] **Step 7: Commit**

Agente `git-commit-push`, **`cwd=/home/afonso/docker/odoo_engenapp/addons/afr_qualificacao`** (submodule!), com `git push origin main`.

```
feat(pwa): add agenda RPC layer and react-query hooks

Transport only: the server decides the date window and what is editable,
so nothing here reimplements the rule. Mutations invalidate both the
agenda and the OS list, since the OS planned dates are a rollup of its
visits and the home screen shows them.
```

---

### Task 6: Aba, rota e lista

**Files:**
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/_components/TecnicoNav.tsx:11-15,18-24`
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/TecnicoNav.test.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/_components/VisitaCard.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/page.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/AgendaLista.test.tsx`

**Interfaces:**
- Consumes: `useAgenda`, `useAgendaDisponivel` (Task 5); `VisitaAgenda` (Task 5); `useTecnicoSettings` de `@/lib/store/tecnicoSettings`; `LoadingState` de `@/components/ui/LoadingState`.
- Produces: `VisitaCard({ visita, onSelect })`; `agruparPorDia(visitas)`; `deslocarJanela(dateFrom, dias)`. A Task 7 monta a folha por cima do `onSelect`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `app/tecnico/qualificacao/__tests__/AgendaLista.test.tsx`:

```tsx
// @vitest-environment happy-dom
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VisitaCard } from '../_components/VisitaCard'
import { agruparPorDia, deslocarJanela } from '../agenda/page'
import type { VisitaAgenda } from '@/lib/odoo/agenda'

function visita(over: Partial<VisitaAgenda> = {}): VisitaAgenda {
  return {
    id: 1, date: '2026-09-17', time_start: 8, time_stop: 12, planned_hours: 4,
    os_id: 4, os_name: 'OS26-06-0002', os_state: 'scheduled',
    partner_name: 'Hospital São Lucas', city: 'São Luís',
    equipment_list: ['Autoclave 01'], instrument_list: [],
    tecnico_id: 441, tecnico_name: 'Afonso', is_mine: true,
    state: 'planned', overflow: false,
    editable: true, lock_reason: false,
    conflict: false, conflict_msg: '', note: '',
    ...over,
  }
}

describe('VisitaCard', () => {
  it('editável é botão e chama onSelect', () => {
    const onSelect = vi.fn()
    render(<VisitaCard visita={visita()} onSelect={onSelect} />)
    const alvo = screen.getByRole('button', { name: /OS26-06-0002/ })
    alvo.click()
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(alvo.className).toContain('min-h-[44px]')
  })

  it('travado mostra o motivo do servidor e não é clicável', () => {
    const onSelect = vi.fn()
    render(
      <VisitaCard
        visita={visita({ editable: false, lock_reason: 'Somente o Gestor edita a agenda.' })}
        onSelect={onSelect}
      />,
    )
    expect(screen.getByText(/Somente o Gestor edita a agenda\./)).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('mostra a mensagem de conflito quando houver', () => {
    render(
      <VisitaCard
        visita={visita({ conflict: true, conflict_msg: 'Deslocamento São Luís → Imperatriz' })}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText(/Deslocamento São Luís/)).toBeInTheDocument()
  })
})

describe('agrupamento e janela', () => {
  it('agrupa por data preservando a ordem do servidor', () => {
    const grupos = agruparPorDia([
      visita({ id: 1, date: '2026-09-17' }),
      visita({ id: 2, date: '2026-09-17' }),
      visita({ id: 3, date: '2026-09-19' }),
    ])
    expect(grupos.map((g) => g.date)).toEqual(['2026-09-17', '2026-09-19'])
    expect(grupos[0].visitas.map((v) => v.id)).toEqual([1, 2])
  })

  it('desloca a janela sem consultar o relógio do aparelho', () => {
    const agora = Date.now
    // Qualquer leitura do relógio local aqui é defeito: a janela nasce do
    // `server_today` que veio no payload.
    Date.now = () => { throw new Error('relógio do aparelho usado') }
    try {
      expect(deslocarJanela('2026-09-16', 14)).toEqual('2026-09-30')
      expect(deslocarJanela('2026-09-16', -14)).toEqual('2026-09-02')
    } finally {
      Date.now = agora
    }
  })
})
```

Ajustar `app/tecnico/qualificacao/__tests__/TecnicoNav.test.tsx`: o teste `renderiza os três destinos com href correto` passa a ser **quatro** — renomear para `renderiza os quatro destinos com href correto` e acrescentar:

```tsx
    expect(screen.getByRole('link', { name: /Agenda/ })).toHaveAttribute(
      'href',
      '/tecnico/qualificacao/agenda',
    )
```

E acrescentar um caso ao mesmo `describe`:

```tsx
  it('esconde a Agenda quando o módulo de agendamento não existe', () => {
    render(<TecnicoNav variant="bottom" agendaDisponivel={false} />)
    expect(screen.queryByRole('link', { name: /Agenda/ })).toBeNull()
    expect(screen.getByRole('link', { name: /Histórico/ })).toBeInTheDocument()
  })
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa
npx vitest run app/tecnico/qualificacao/__tests__/AgendaLista.test.tsx \
  app/tecnico/qualificacao/__tests__/TecnicoNav.test.tsx
```

Esperado: FAIL — `VisitaCard` e `../agenda/page` não resolvem; o teste da nav não acha o link `Agenda`.

- [ ] **Step 3: Nav com o 4º destino**

Em `_components/TecnicoNav.tsx`, no import de ícones acrescentar `CalendarDays`, e em `NAV_ITEMS`:

```tsx
export const NAV_ITEMS = [
  { href: ROOT_PATH, label: 'OSs', Icon: ClipboardList },
  { href: `${ROOT_PATH}/agenda`, label: 'Agenda', Icon: CalendarDays },
  { href: `${ROOT_PATH}/historico`, label: 'Histórico', Icon: BarChart3 },
  { href: `${ROOT_PATH}/perfil`, label: 'Perfil', Icon: User },
] as const
```

E em `useActiveHref()`, antes do `return` final:

```tsx
  const isAgenda = pathname.startsWith(`${ROOT_PATH}/agenda`)
  if (isAgenda) return `${ROOT_PATH}/agenda`
```

A nav continua **componente puro**: quem decide se o módulo existe é o layout (Task 7), que passa a resposta por prop. Chamar `useAgendaDisponivel()` aqui dentro quebraria o teste — `useQuery` fora de um `QueryClientProvider` lança, e o teste da nav renderiza o componente sozinho.

Assinatura nova:

```tsx
export function TecnicoNav({
  variant,
  agendaDisponivel = true,
}: {
  variant: 'bottom' | 'side'
  /** Falso esconde a aba Agenda: o módulo de agendamento não está instalado. */
  agendaDisponivel?: boolean
}) {
  const activeHref = useActiveHref()
  const isSide = variant === 'side'
  const itens = NAV_ITEMS.filter(
    (i) => agendaDisponivel || !i.href.endsWith('/agenda'),
  )
```

e iterar `itens` em vez de `NAV_ITEMS` no `map`.

- [ ] **Step 4: `VisitaCard`**

Criar `_components/VisitaCard.tsx`:

```tsx
'use client'
import { Lock, AlertTriangle, Clock, MapPin } from 'lucide-react'
import { clsx } from 'clsx'
import type { VisitaAgenda } from '@/lib/odoo/agenda'

/** 8.5 → "08:30". Horas fracionárias do Odoo, sem tocar no fuso. */
export function horaOdoo(h: number): string {
  const hh = Math.floor(h)
  const mm = Math.round((h - hh) * 60)
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

function Corpo({ visita }: { visita: VisitaAgenda }) {
  return (
    <>
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Clock className="h-4 w-4 shrink-0" aria-hidden />
        {horaOdoo(visita.time_start)}–{horaOdoo(visita.time_stop)}
        <span className="truncate">{visita.os_name}</span>
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <MapPin className="h-4 w-4 shrink-0" aria-hidden />
        <span className="truncate">
          {visita.partner_name}
          {visita.city ? ` · ${visita.city}` : ''}
        </span>
      </div>
      {!visita.is_mine && (
        <p className="text-xs text-muted-foreground">Técnico: {visita.tecnico_name}</p>
      )}
      {visita.equipment_list.length > 0 && (
        <p className="truncate text-xs text-muted-foreground">
          {visita.equipment_list.join(', ')}
        </p>
      )}
      {visita.conflict && visita.conflict_msg && (
        <p className="flex items-start gap-1.5 text-xs text-danger">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          {visita.conflict_msg}
        </p>
      )}
    </>
  )
}

export function VisitaCard({
  visita,
  onSelect,
}: {
  visita: VisitaAgenda
  onSelect: (visita: VisitaAgenda) => void
}) {
  const base = 'flex w-full min-h-[44px] flex-col gap-1 rounded-lg border border-border bg-card p-3 text-left'
  // `lock_reason` é frase pronta do servidor. O front não decide nada aqui —
  // se decidisse, a regra viveria em dois lugares.
  if (!visita.editable) {
    return (
      <div className={clsx(base, 'opacity-70')}>
        <Corpo visita={visita} />
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Lock className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {visita.lock_reason}
        </p>
      </div>
    )
  }
  return (
    <button type="button" onClick={() => onSelect(visita)} className={clsx(base, 'hover:bg-accent')}>
      <Corpo visita={visita} />
    </button>
  )
}
```

- [ ] **Step 5: A página**

Criar `app/tecnico/qualificacao/agenda/page.tsx`:

```tsx
'use client'
import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { VisitaCard } from '../_components/VisitaCard'
import { LoadingState } from '@/components/ui/LoadingState'
import { useAgenda, useAgendaDisponivel } from '@/lib/hooks/useAgenda'
import { useTecnicoSettings } from '@/lib/store/tecnicoSettings'
import type { VisitaAgenda } from '@/lib/odoo/agenda'

const JANELA_DIAS = 14

export interface GrupoDia {
  date: string
  visitas: VisitaAgenda[]
}

/** Agrupa preservando a ordem em que o servidor mandou. */
export function agruparPorDia(visitas: VisitaAgenda[]): GrupoDia[] {
  const grupos: GrupoDia[] = []
  for (const v of visitas) {
    const ultimo = grupos[grupos.length - 1]
    if (ultimo && ultimo.date === v.date) ultimo.visitas.push(v)
    else grupos.push({ date: v.date, visitas: [v] })
  }
  return grupos
}

/**
 * Soma dias a uma data ISO sem tocar no relógio do aparelho. `Date.UTC` evita
 * que o fuso local mude o dia — o servidor é quem diz que dia é hoje.
 */
export function deslocarJanela(dateFrom: string, dias: number): string {
  const [a, m, d] = dateFrom.split('-').map(Number)
  const base = new Date(Date.UTC(a, m - 1, d))
  base.setUTCDate(base.getUTCDate() + dias)
  return base.toISOString().slice(0, 10)
}

function rotuloDia(iso: string): string {
  const [a, m, d] = iso.split('-').map(Number)
  return new Intl.DateTimeFormat('pt-BR', {
    weekday: 'short', day: '2-digit', month: 'short', timeZone: 'UTC',
  }).format(new Date(Date.UTC(a, m - 1, d)))
}

export default function AgendaPage() {
  const disponivel = useAgendaDisponivel()
  const { filterMine, setFilterMine } = useTecnicoSettings()
  // `null` na primeira carga: o servidor decide a janela e devolve
  // `date_from`, que passa a ancorar a navegação.
  const [inicio, setInicio] = useState<string | null>(null)
  const fim = inicio ? deslocarJanela(inicio, JANELA_DIAS - 1) : null
  const { data, isLoading, error } = useAgenda(inicio, fim, filterMine)

  if (disponivel.data === false) {
    return (
      <p className="mx-auto max-w-[880px] p-4 text-center text-muted-foreground">
        Agenda de visitas indisponível: o módulo de agendamento não está
        instalado neste servidor.
      </p>
    )
  }

  const ancora = inicio ?? data?.date_from ?? null
  const semEmpregado = data ? !data.my_employee_id : false
  const grupos = agruparPorDia(data?.visitas ?? [])

  return (
    <div className="mx-auto w-full max-w-[880px] space-y-4">
      <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-2 py-1">
        <button
          type="button"
          aria-label="Semanas anteriores"
          className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-accent"
          onClick={() => ancora && setInicio(deslocarJanela(ancora, -JANELA_DIAS))}
        >
          <ChevronLeft className="h-5 w-5" aria-hidden />
        </button>
        <span className="text-sm font-medium">
          {data ? `${rotuloDia(data.date_from)} – ${rotuloDia(data.date_to)}` : '—'}
        </span>
        <button
          type="button"
          aria-label="Próximas semanas"
          className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-accent"
          onClick={() => ancora && setInicio(deslocarJanela(ancora, JANELA_DIAS))}
        >
          <ChevronRight className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <label
        htmlFor="agenda-filter-mine"
        className="flex min-h-[44px] cursor-pointer items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2"
      >
        <span className="text-sm font-medium">
          Só minhas
          <span className="block text-xs font-normal text-muted-foreground">
            {semEmpregado
              ? 'Seu usuário não tem técnico vinculado'
              : filterMine
                ? 'Visitas atribuídas a você'
                : 'Visitas de toda a equipe'}
          </span>
        </span>
        <input
          id="agenda-filter-mine"
          type="checkbox"
          checked={filterMine && !semEmpregado}
          disabled={semEmpregado}
          onChange={(e) => setFilterMine(e.target.checked)}
          className="h-6 w-6 shrink-0 cursor-pointer accent-ok disabled:opacity-40"
        />
      </label>

      {isLoading && <LoadingState label="Carregando sua agenda..." />}
      {error && (
        <p className="text-center text-danger">
          Erro ao carregar a agenda. Verifique conexão.
        </p>
      )}
      {!isLoading && !error && grupos.length === 0 && (
        <p className="py-8 text-center text-muted-foreground">
          Nenhuma visita neste período.
        </p>
      )}

      {grupos.map((g) => (
        <section key={g.date} className="space-y-2">
          <h2 className="sticky top-0 z-10 bg-background py-1 text-sm font-semibold uppercase text-muted-foreground">
            {rotuloDia(g.date)}
          </h2>
          {g.visitas.map((v) => (
            <VisitaCard key={v.id} visita={v} onSelect={() => undefined} />
          ))}
        </section>
      ))}
    </div>
  )
}
```

> `onSelect` fica inerte nesta task de propósito: a folha de edição é a Task 7. Nada de Gestor ainda — o card travado já cobre o técnico, que é a maioria dos usuários.

- [ ] **Step 6: Rodar e confirmar que passa**

```bash
npx vitest run app/tecnico/qualificacao/__tests__/AgendaLista.test.tsx \
  app/tecnico/qualificacao/__tests__/TecnicoNav.test.tsx
npx tsc --noEmit
```

Esperado: todos passam; `tsc` limpo.

- [ ] **Step 7: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp/addons/afr_qualificacao` (submodule), `git push origin main`.

```
feat(pwa): add Agenda tab with per-day visit list

Cards render the server's editable/lock_reason verbatim rather than
re-deriving them. Window navigation walks ISO dates in UTC from the
payload's date_from, so the list never reads the device clock — a test
throws if Date.now is touched.
```

---

### Task 7: Folha de edição, criação e exclusão (Gestor)

**Files:**
- Create: `addons/afr_qualificacao/pwa/components/ui/BottomSheet.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/_components/VisitaSheet.tsx`
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/page.tsx`
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/layout.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/VisitaSheet.test.tsx`

**Interfaces:**
- Consumes: `BottomSheet({ open, title, onClose, children })`; `useUpdateVisita`, `useCreateVisita`, `useDeleteVisita`, `useTecnicoOptions`, `useOsOptions` (Task 5); `VisitaAgenda`, `VisitaVals` (Task 5); `mensagemDeFalha` de `@/lib/odoo/client`.
- Produces: `VisitaSheet({ visita, modo, open, onClose })` com `modo: 'editar' | 'criar'`. Última task — nada consome depois.

- [ ] **Step 1: Escrever o teste que falha**

Criar `app/tecnico/qualificacao/__tests__/VisitaSheet.test.tsx`:

```tsx
// @vitest-environment happy-dom
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { VisitaSheet } from '../_components/VisitaSheet'
import type { VisitaAgenda } from '@/lib/odoo/agenda'

const mutateUpdate = vi.fn()
const mutateCreate = vi.fn()
const mutateDelete = vi.fn()

vi.mock('@/lib/hooks/useAgenda', () => ({
  useUpdateVisita: () => ({ mutateAsync: mutateUpdate, isPending: false }),
  useCreateVisita: () => ({ mutateAsync: mutateCreate, isPending: false }),
  useDeleteVisita: () => ({ mutateAsync: mutateDelete, isPending: false }),
  useTecnicoOptions: () => ({ data: [{ id: 441, name: 'Afonso' }, { id: 9, name: 'Bruno' }] }),
  useOsOptions: () => ({ data: [{ id: 4, name: 'OS26-06-0002 - Hospital' }] }),
}))

const visita: VisitaAgenda = {
  id: 1, date: '2026-09-17', time_start: 8, time_stop: 12, planned_hours: 4,
  os_id: 4, os_name: 'OS26-06-0002', os_state: 'scheduled',
  partner_name: 'Hospital', city: 'São Luís',
  equipment_list: [], instrument_list: [],
  tecnico_id: 441, tecnico_name: 'Afonso', is_mine: true,
  state: 'planned', overflow: false, editable: true, lock_reason: false,
  conflict: false, conflict_msg: '', note: '',
}

describe('VisitaSheet', () => {
  beforeEach(() => {
    mutateUpdate.mockReset().mockResolvedValue(visita)
    mutateCreate.mockReset().mockResolvedValue(visita)
    mutateDelete.mockReset().mockResolvedValue(true)
  })

  it('salva só os campos da whitelist', async () => {
    render(<VisitaSheet open modo="editar" visita={visita} onClose={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Data'), { target: { value: '2026-09-18' } })
    fireEvent.click(screen.getByRole('button', { name: /Salvar/ }))
    await waitFor(() => expect(mutateUpdate).toHaveBeenCalled())
    const enviado = mutateUpdate.mock.calls[0][0]
    expect(enviado.id).toBe(1)
    expect(Object.keys(enviado.vals).sort()).toEqual(
      ['date', 'note', 'tecnico_id', 'time_start', 'time_stop'],
    )
    expect(enviado.vals.date).toBe('2026-09-18')
  })

  it('apagar exige confirmação', async () => {
    render(<VisitaSheet open modo="editar" visita={visita} onClose={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Apagar/ }))
    expect(mutateDelete).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Confirmar exclusão/ }))
    await waitFor(() => expect(mutateDelete).toHaveBeenCalledWith(1))
  })

  it('erro do servidor aparece na folha e não fecha', async () => {
    const onClose = vi.fn()
    mutateUpdate.mockRejectedValue(new Error('Não é possível programar uma visita para uma data passada'))
    render(<VisitaSheet open modo="editar" visita={visita} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /Salvar/ }))
    await waitFor(() =>
      expect(screen.getByText(/data passada/)).toBeInTheDocument(),
    )
    expect(onClose).not.toHaveBeenCalled()
  })

  it('modo criar pede OS, técnico e data', async () => {
    render(<VisitaSheet open modo="criar" visita={null} onClose={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('OS'), { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Técnico'), { target: { value: '441' } })
    fireEvent.change(screen.getByLabelText('Data'), { target: { value: '2026-09-20' } })
    fireEvent.click(screen.getByRole('button', { name: /Criar/ }))
    await waitFor(() =>
      expect(mutateCreate).toHaveBeenCalledWith({ osId: 4, tecnicoId: 441, date: '2026-09-20' }),
    )
  })

  it('modo criar não oferece apagar', () => {
    render(<VisitaSheet open modo="criar" visita={null} onClose={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /Apagar/ })).toBeNull()
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
npx vitest run app/tecnico/qualificacao/__tests__/VisitaSheet.test.tsx
```

Esperado: FAIL — `../_components/VisitaSheet` não resolve.

- [ ] **Step 3: `BottomSheet`**

Criar `components/ui/BottomSheet.tsx`:

```tsx
'use client'
import { useEffect } from 'react'
import { X } from 'lucide-react'

/**
 * Folha vinda de baixo. O projeto não tem Modal genérico (só o
 * `PdfViewerModal`, que é específico); esta é a primeira.
 */
export function BottomSheet({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: React.ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <div
        className="absolute inset-0 bg-black/60"
        aria-hidden
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-[560px] rounded-t-2xl border-t border-border bg-card p-4 shadow-[0_-8px_24px_rgba(0,0,0,0.45)]"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            type="button"
            aria-label="Fechar"
            onClick={onClose}
            className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-accent"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: `VisitaSheet`**

Criar `_components/VisitaSheet.tsx`:

```tsx
'use client'
import { useState } from 'react'
import { BottomSheet } from '@/components/ui/BottomSheet'
import { mensagemDeFalha } from '@/lib/odoo/client'
import {
  useUpdateVisita,
  useCreateVisita,
  useDeleteVisita,
  useTecnicoOptions,
  useOsOptions,
} from '@/lib/hooks/useAgenda'
import { horaOdoo } from './VisitaCard'
import type { VisitaAgenda } from '@/lib/odoo/agenda'

/** "08:30" → 8.5, o float de hora do Odoo. */
function paraFloat(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return (h || 0) + (m || 0) / 60
}

const campo = 'min-h-[44px] w-full rounded-md border border-border bg-background px-3'

export function VisitaSheet({
  open,
  modo,
  visita,
  onClose,
}: {
  open: boolean
  modo: 'editar' | 'criar'
  visita: VisitaAgenda | null
  onClose: () => void
}) {
  const update = useUpdateVisita()
  const criar = useCreateVisita()
  const apagar = useDeleteVisita()
  const tecnicos = useTecnicoOptions(open)
  const oss = useOsOptions(open && modo === 'criar')

  const [data, setData] = useState(visita?.date ?? '')
  const [inicio, setInicio] = useState(horaOdoo(visita?.time_start ?? 8))
  const [fim, setFim] = useState(horaOdoo(visita?.time_stop ?? 12))
  const [tecnicoId, setTecnicoId] = useState(String(visita?.tecnico_id ?? ''))
  const [osId, setOsId] = useState(String(visita?.os_id ?? ''))
  const [nota, setNota] = useState(visita?.note ?? '')
  const [erro, setErro] = useState('')
  const [confirmando, setConfirmando] = useState(false)

  const ocupado = update.isPending || criar.isPending || apagar.isPending

  async function salvar() {
    setErro('')
    try {
      if (modo === 'criar') {
        await criar.mutateAsync({
          osId: Number(osId), tecnicoId: Number(tecnicoId), date: data,
        })
      } else if (visita) {
        await update.mutateAsync({
          id: visita.id,
          vals: {
            date: data,
            time_start: paraFloat(inicio),
            time_stop: paraFloat(fim),
            tecnico_id: Number(tecnicoId),
            note: nota,
          },
        })
      }
      onClose()
    } catch (e) {
      // A mensagem do servidor é a que o usuário precisa ler (constraint de
      // equipamento sobreposto, data passada, OS travada). A folha fica
      // aberta com o que ele digitou.
      setErro(e instanceof Error && e.message ? e.message : mensagemDeFalha(e))
    }
  }

  async function confirmarExclusao() {
    if (!visita) return
    setErro('')
    try {
      await apagar.mutateAsync(visita.id)
      onClose()
    } catch (e) {
      setErro(e instanceof Error && e.message ? e.message : mensagemDeFalha(e))
    }
  }

  return (
    <BottomSheet
      open={open}
      title={modo === 'criar' ? 'Nova visita' : `Visita ${visita?.os_name ?? ''}`}
      onClose={onClose}
    >
      <div className="space-y-3">
        {modo === 'criar' && (
          <label className="block text-sm">
            OS
            <select aria-label="OS" className={campo} value={osId} onChange={(e) => setOsId(e.target.value)}>
              <option value="">—</option>
              {(oss.data ?? []).map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </label>
        )}

        <label className="block text-sm">
          Data
          <input aria-label="Data" type="date" className={campo} value={data} onChange={(e) => setData(e.target.value)} />
        </label>

        {modo === 'editar' && (
          <div className="flex gap-3">
            <label className="block flex-1 text-sm">
              Início
              <input aria-label="Início" type="time" className={campo} value={inicio} onChange={(e) => setInicio(e.target.value)} />
            </label>
            <label className="block flex-1 text-sm">
              Fim
              <input aria-label="Fim" type="time" className={campo} value={fim} onChange={(e) => setFim(e.target.value)} />
            </label>
          </div>
        )}

        <label className="block text-sm">
          Técnico
          <select aria-label="Técnico" className={campo} value={tecnicoId} onChange={(e) => setTecnicoId(e.target.value)}>
            <option value="">—</option>
            {(tecnicos.data ?? []).map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </label>

        {modo === 'editar' && (
          <label className="block text-sm">
            Observações
            <textarea aria-label="Observações" rows={3} className="w-full rounded-md border border-border bg-background p-3" value={nota} onChange={(e) => setNota(e.target.value)} />
          </label>
        )}

        {erro && <p className="text-sm text-danger">{erro}</p>}

        <div className="flex gap-2 pt-1">
          <button type="button" disabled={ocupado} onClick={salvar} className="min-h-[44px] flex-1 rounded-md bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-50">
            {modo === 'criar' ? 'Criar' : 'Salvar'}
          </button>
          {modo === 'editar' && !confirmando && (
            <button type="button" disabled={ocupado} onClick={() => setConfirmando(true)} className="min-h-[44px] rounded-md border border-destructive px-4 font-semibold text-destructive disabled:opacity-50">
              Apagar
            </button>
          )}
          {modo === 'editar' && confirmando && (
            <button type="button" disabled={ocupado} onClick={confirmarExclusao} className="min-h-[44px] rounded-md bg-destructive px-4 font-semibold text-destructive-foreground disabled:opacity-50">
              Confirmar exclusão
            </button>
          )}
        </div>
      </div>
    </BottomSheet>
  )
}
```

- [ ] **Step 5: Ligar a folha na página**

Em `app/tecnico/qualificacao/agenda/page.tsx`:

1. Importar `VisitaSheet` e o ícone `Plus`.
2. Estado novo, ao lado de `inicio`:

```tsx
  const [selecionada, setSelecionada] = useState<VisitaAgenda | null>(null)
  const [criando, setCriando] = useState(false)
```

3. Trocar `onSelect={() => undefined}` por `onSelect={setSelecionada}`.
4. Antes do `</div>` final:

```tsx
      {data?.can_manage && (
        <button
          type="button"
          onClick={() => setCriando(true)}
          className="fixed bottom-20 right-4 z-40 flex h-14 items-center gap-2 rounded-full bg-primary px-5 font-semibold text-primary-foreground shadow-[0_8px_24px_rgba(0,0,0,0.45)] lg:bottom-6"
        >
          <Plus className="h-5 w-5" aria-hidden />
          Nova visita
        </button>
      )}

      <VisitaSheet
        open={!!selecionada}
        modo="editar"
        visita={selecionada}
        onClose={() => setSelecionada(null)}
      />
      <VisitaSheet
        open={criando}
        modo="criar"
        visita={null}
        onClose={() => setCriando(false)}
      />
```

> `key` nas folhas não é necessário porque `open` desmonta o conteúdo do
> `BottomSheet` (`if (!open) return null`), mas os `useState` de `VisitaSheet`
> vivem no componente pai dela. Acrescente `key={selecionada?.id ?? 'nenhuma'}`
> na folha de edição para o formulário renascer a cada visita escolhida.

5. Esconder a aba quando o módulo não existe. A consulta fica no **layout**, que já é client component e renderiza as duas variantes da nav; a nav segue pura. Em `app/tecnico/qualificacao/layout.tsx`:

```tsx
import { useAgendaDisponivel } from '@/lib/hooks/useAgenda'
```

dentro de `TecnicoLayout`, junto dos outros hooks:

```tsx
  // `undefined` enquanto carrega: mostra a aba e evita o piscar de um item
  // que aparece depois. Só `false` (modelo ausente) esconde.
  const { data: temAgenda } = useAgendaDisponivel()
  const agendaDisponivel = temAgenda !== false
```

e nas duas chamadas:

```tsx
        <TecnicoNav variant="side" agendaDisponivel={agendaDisponivel} />
...
          <TecnicoNav variant="bottom" agendaDisponivel={agendaDisponivel} />
```

- [ ] **Step 6: Rodar tudo**

```bash
npx vitest run
npx tsc --noEmit
```

Esperado: suíte inteira passa (sem falha nova contra `pwa/docs/BASELINE.md`); `tsc` limpo.

- [ ] **Step 7: Validar na UI de verdade, por `agent-browser`**

Regra do projeto: testar a interface eu mesmo, não delegar o clique ao user.

1. `~/.claude/bin/devserver list` antes de subir qualquer coisa.
2. `~/.claude/bin/devserver start --port 3010 --dir /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa`
3. Aquecer as rotas com `curl` (a primeira visita compila e parece app travado).
4. `agent-browser open http://localhost:3010/login`, logar no `qualificacao-dev`, navegar até `/tecnico/qualificacao/agenda`.
5. Conferir, com screenshot: a aba aparece; a lista agrupa por dia; um card travado mostra o cadeado e o motivo; como Gestor, a folha abre, salva e o erro de constraint aparece dentro dela.

- [ ] **Step 8: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp/addons/afr_qualificacao` (submodule), `git push origin main`. Depois, bump do pointer no monorepo, em commit separado, a partir de `/home/afonso/docker/odoo_engenapp`:

```
feat(pwa): add visit sheet for managers, hide tab without the module

The sheet sends exactly the whitelisted keys the server accepts and keeps
server-side constraint messages in place instead of closing on error.
Delete is two-step. The Agenda tab disappears when ir.model has no
afr.qualificacao.os.visita, since the PWA ships in afr_qualificacao and
the scheduling module only depends on it, never the other way round.
```

```
chore: bump submodule afr_qualificacao (PWA visit agenda)
```

---

## Notas de integração

- **`_check_manager_only` é o guard, não a `ir.rule`.** `manager ⊃ user ⊃ technician`: a implicação desce, então o Usuário comum não está no grupo Gestor e o guard o barra. Para `ir.rule` seria o oposto — a implicação faria o Gestor cair na regra restritiva do Técnico e exigiria o par OR'ed, como em `afr.qualificacao.os`.
- **Divulgação aceita:** `pwa_agenda_fetch` não tem guard e devolve `partner_name`, `city` e `conflict_msg` de toda a equipe; `conflict_msg` interpola o nome da OS conflitante. É a decisão de leitura global, registrada na spec.
- **Relógio do WSL pode estar adiantado**; `sudo hwclock -s` dentro do WSL antes de confiar em qualquer timestamp. Não quebra os testes (todas as datas são relativas a `context_today`), mas confunde a leitura manual na UI.
- **Débito prévio:** o Bloco H (H1–H12) de `pwa/app/tecnico/qualificacao/F7_0_TEST_CHECKLIST.md` nunca rodou, e tem bloqueio conhecido em item `kind='outro'` sem anexo (`models/qualificacao_collect_item.py:269-276`). Esta feature empilha em cima disso.
