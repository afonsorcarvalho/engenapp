# Modo Semana da Agenda no PWA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao Gestor, no celular, uma visão semanal da agenda com carga por técnico e por instrumento, e remanejar visitas por toque.

**Architecture:** O backend quase não muda — três acréscimos em `models/os_visita.py` (ids de instrumento no payload, uma lista de opções, um campo a mais na whitelist) e **nenhum método de mutação novo**: dia, técnico e instrumento vão todos pelo `pwa_visita_update` que já existe e já é guardado por Gestor. O front ganha um modo dentro da rota `/agenda` que já existe, com três faixas empilhadas (dias, painel de recursos, visitas do dia) e uma máquina de seleção onde o painel vira alvo do gesto. Carga e ocupação são funções puras calculadas no cliente a partir das visitas que a busca já devolve.

**Tech Stack:** Odoo 16.0 (Python, `TransactionCase`), Next.js 14 App Router, React 18, TypeScript, `@tanstack/react-query` v5, zustand, Tailwind, vitest + @testing-library/react.

**Spec:** `addons/afr_qualificacao_agendamento/docs/superpowers/specs/2026-09-17-agenda-modo-semana-design.md`

## Global Constraints

- **Repo:** monorepo `odoo_engenapp`, branch `main-monorepo`. `afr_qualificacao_agendamento` **não** é submodule — commite de `/home/afonso/docker/odoo_engenapp`. `afr_qualificacao` **é** submodule — commite de dentro de `addons/afr_qualificacao/`.
- **Commits sempre via agente `git-commit-push` (haiku)**, nunca `git commit` direto. **Sem `push`** até o user autorizar.
- **Container Odoo:** `odoo_engenapp-web-qualificacao-1`, banco `qualificacao-dev`, binário `/opt/odoo/venv/bin/odoo`, db host interno `db-qualificacao`. As flags `--db_host/--db_user/--db_password` são obrigatórias. Ruído `OSError: Address already in use` do httpd é ambiental.
- **Baseline no início deste plano:** backend `afr_qualificacao_agendamento` **99 testes, 0 failed**; front **269 testes, 0 failed**; `npx tsc --noEmit` limpo; `npx next build` limpo.
- **O front nunca chama `Date.now()`/`new Date()` para decidir "hoje".** A janela vem de `server_today` no payload. Há teste-âncora que estoura se `Date.now` for tocado.
- **Alvo de toque ≥44px** — o técnico usa luva.
- **Só Gestor age.** O modo é visível a todos; `Ajustar` e os alvos do painel só existem com `can_manage`.
- **Nenhuma trava de agendamento existente é relaxada.**
- **`_PWA_WRITABLE_FIELDS` é a única porta de escrita**, e recusa qualquer chave fora dela.
- Código, identificadores e mensagens de commit em inglês; strings de UI e docstrings em pt-BR. Nomes de método de teste seguem o padrão pt-BR já estabelecido em `tests/test_pwa_agenda.py`.
- Tokens de tema do projeto apenas — `temaTokens.test.ts` reprova classe de cor crua.

## File Structure

**Backend (`addons/afr_qualificacao_agendamento/`)**

| Arquivo | Responsabilidade |
|---|---|
| `models/os_visita.py` (modificar) | `instrument_ids` no serializer; `pwa_instrumento_options`; `instrument_ids` na whitelist com normalização de ids. |
| `tests/test_pwa_agenda.py` (modificar) | Classe nova `TestPwaAgendaInstrumento`. |
| `__manifest__.py` (modificar) | Bump `16.0.1.1.0` → `16.0.1.2.0`. |

**Front (`addons/afr_qualificacao/pwa/`)**

| Arquivo | Responsabilidade |
|---|---|
| `lib/odoo/agenda.ts` (modificar) | `instrument_ids` no tipo; `VisitaVals.instrument_ids`; `listInstrumentoOptions()`. |
| `lib/hooks/useAgenda.ts` (modificar) | `useInstrumentoOptions(enabled)`. |
| `lib/store/tecnicoSettings.ts` (modificar) | Preferência de modo (`lista` \| `semana`). |
| `app/tecnico/qualificacao/agenda/carga.ts` (criar) | Funções puras: carga por dia, carga por técnico, ocupação por instrumento, calibração vencida. Nenhum React. |
| `app/tecnico/qualificacao/agenda/_FaixaDias.tsx` (criar) | Faixa dos 7 dias com total de horas e marca de conflito. |
| `app/tecnico/qualificacao/agenda/_PainelRecursos.tsx` (criar) | Painel Técnico ⇄ Instrumento, e os alvos do gesto. |
| `app/tecnico/qualificacao/agenda/page.tsx` (modificar) | Botão de modo, montagem das três faixas, máquina de seleção, tarja de erro. |
| `app/tecnico/qualificacao/_components/VisitaCard.tsx` (modificar) | Botão `Ajustar` e estado de selecionado. |
| `app/tecnico/qualificacao/__tests__/*` | Testes das funções puras, dos dois componentes novos e da máquina de seleção. |

---

### Task 1: `instrument_ids` no payload

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py` (dentro de `_pwa_serialize`)
- Modify: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py`

**Interfaces:**
- Consumes: `_pwa_serialize(self, is_manager, my_employee_id)`, `PwaAgendaCommon` (base de teste com `user_tec`/`user_usr`/`user_gestor`, `emp_tec`/`emp_outro`, `hoje`/`d1`/`d2`/`d_fora`, `_make_os(state="scheduled")`, `_make_visita(os, day, employee, **extra)`).
- Produces: a chave `"instrument_ids": list[int]` em toda linha de visita devolvida por `pwa_agenda_fetch`, `pwa_visita_update` e `pwa_visita_create`. As Tasks 3 e 5 dependem dela.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao fim de `tests/test_pwa_agenda.py`:

```python
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
        self._make_visita(os1, self.d1, self.emp_tec)
        data = self.Visita.with_user(self.user_gestor).pwa_agenda_fetch(
            only_mine=False)
        self.assertEqual(data["visitas"][0]["instrument_ids"], [])
```

Registrar nada no `tests/__init__.py` — o arquivo já é importado.

> O modelo do certificado pode exigir campos além dos dois usados. Se o
> `create` falhar, descubra os obrigatórios com `fields_get()` ou copie o idioma
> de `tests/test_resource_conflict.py`, que já monta instrumentos com
> certificado, e ajuste **só o create** — nunca a asserção.

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento:TestPwaAgendaInstrumento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.stats|tests.result'
```

Esperado: FAIL em `test_serializer_devolve_ids_de_instrumento` e
`test_visita_sem_instrumento_devolve_lista_vazia` com `KeyError: 'instrument_ids'`.

- [ ] **Step 3: Implementar**

Em `_pwa_serialize`, na linha imediatamente ANTES de `"instrument_list"`:

```python
            # Os nomes servem ao card; os ids servem à folha (marcar o que já
            # está escolhido) e ao painel de recursos (saber qual visita ocupa
            # qual instrumento). Um não substitui o outro.
            "instrument_ids": self.instrument_ids.ids,
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 2 testes, 0 failed, 0 error.

- [ ] **Step 5: Rodar a suíte inteira do módulo**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags afr_qualificacao_agendamento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.result'
```

Esperado: `0 failed, 0 error(s) of 101 tests` (99 do baseline + 2).

- [ ] **Step 6: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`, sem push, staging só de `models/os_visita.py` e `tests/test_pwa_agenda.py` do módulo agendamento.

```
feat(agendamento): serialize instrument ids alongside their names

The card needs names, but the sheet needs ids to know what is already
selected, and the week panel needs them to know which visit holds which
instrument. Neither replaces the other.
```

---

### Task 2: `pwa_instrumento_options`

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py` (após `pwa_tecnico_options`)
- Modify: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py` (classe `TestPwaAgendaInstrumento`)

**Interfaces:**
- Consumes: `PwaAgendaCommon`, o helper `_instrumento(nome, validade=None)` da Task 1.
- Produces: `pwa_instrumento_options(self) -> list[dict]`, cada item `{"id": int, "name": str, "validade": str | False}`. A Task 5 consome pelo front.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar à classe `TestPwaAgendaInstrumento`:

```python
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
        self._instrumento("INS-CHAVES")
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        self.assertTrue(opts)
        for k in ("id", "name", "validade"):
            self.assertIn(k, opts[0])

    def test_options_sem_permissao_hr_nao_estoura(self):
        """Espelha `test_tecnico_options_sem_permissao_hr_nao_estoura`. Aqui
        não deve haver `sudo` — `engc.calibration.instruments` é legível por
        `base.group_user` —, mas o teste ancora que a chamada funciona para
        quem não tem HR, que é o caso do Gestor recém-criado."""
        self._instrumento("INS-HR")
        self.assertFalse(self.user_gestor.has_group("hr.group_hr_user"))
        opts = self.Visita.with_user(self.user_gestor).pwa_instrumento_options()
        self.assertTrue(opts)

    def test_options_visivel_ao_tecnico(self):
        """Leitura é global na agenda; o método não tem guard de Gestor."""
        self._instrumento("INS-TEC")
        opts = self.Visita.with_user(self.user_tec).pwa_instrumento_options()
        self.assertTrue(opts)
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento:TestPwaAgendaInstrumento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.result'
```

Esperado: `AttributeError` em `pwa_instrumento_options` nos 5 testes novos.

- [ ] **Step 3: Implementar**

Logo após `pwa_tecnico_options` em `models/os_visita.py`:

```python
    @api.model
    def pwa_instrumento_options(self):
        """Instrumentos para o painel de recursos e para o seletor da folha.

        Sem `sudo`, ao contrário de `pwa_tecnico_options`:
        `engc.calibration.instruments` tem leitura para `base.group_user`
        (`engenapp/engc_os/security/ir.model.access.csv`), então não há a
        armadilha de delegação que o `hr.employee` tem.

        `validade` é a MAIOR `validate_calibration` entre os certificados —
        um campo só, comparado no cliente com o dia escolhido. Devolver uma
        matriz instrumento × dia seria carregar o servidor à toa: se a maior
        validade não alcança o dia, nenhum certificado alcança.
        """
        out = []
        for inst in self.env["engc.calibration.instruments"].search([]):
            datas = [
                c.validate_calibration
                for c in inst.certificate_ids
                if c.validate_calibration
            ]
            out.append({
                "id": inst.id,
                "name": inst.tag or inst.id_number or inst.name,
                "validade": fields.Date.to_string(max(datas)) if datas else False,
            })
        return out
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 7 testes na classe (2 da Task 1 + 5), 0 failed.

- [ ] **Step 5: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`, sem push.

```
feat(agendamento): add pwa_instrumento_options with a single validity date

No sudo here, unlike the technician list: engc.calibration.instruments is
readable by base.group_user, so the hr.employee delegation trap does not
apply. The payload carries the latest validate_calibration rather than a
per-day matrix — if the latest one does not reach the day, none does.
```

---

### Task 3: `instrument_ids` gravável pela agenda

**Files:**
- Modify: `addons/afr_qualificacao_agendamento/models/os_visita.py` (`_PWA_WRITABLE_FIELDS` e `pwa_visita_update`)
- Modify: `addons/afr_qualificacao_agendamento/tests/test_pwa_agenda.py`
- Modify: `addons/afr_qualificacao_agendamento/__manifest__.py` (bump de versão)

**Interfaces:**
- Consumes: `_PWA_WRITABLE_FIELDS` (hoje `{date, time_start, time_stop, tecnico_id, note}`); `pwa_visita_update(visita_id, vals)`; o helper `_instrumento` da Task 1.
- Produces: `pwa_visita_update` aceitando `{"instrument_ids": [1, 2]}` — lista simples de ids. A Task 6 chama assim pelo front. Fecha o backend.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar à classe `TestPwaAgendaInstrumento`:

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags /afr_qualificacao_agendamento:TestPwaAgendaInstrumento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.result'
```

Esperado: `test_gestor_grava_instrumentos` e `test_lista_vazia_desliga_todos` falham
com `UserError: Campo(s) não editável(is) pela agenda: instrument_ids.`
`test_recusa_tupla_de_comando`, `test_recusa_valor_nao_lista`, `test_tecnico_barrado`
e `test_os_em_execucao_recusa` **já passam** — pelo motivo errado (a whitelist
recusa tudo). É esperado; eles viram rede de segurança depois do Step 3.

- [ ] **Step 3: Implementar**

(a) A whitelist passa a ser:

```python
    # Campos que a agenda do PWA pode gravar. `planned_hours` fica de fora de
    # propósito: é derivado do par início/fim, não digitado.
    _PWA_WRITABLE_FIELDS = frozenset({
        "date", "time_start", "time_stop", "tecnico_id", "note",
        "instrument_ids",
    })
```

(b) Em `pwa_visita_update`, logo APÓS a linha `vals = dict(vals)` e ANTES do
bloco que calcula `start`/`stop`:

```python
        if "instrument_ids" in vals:
            ids = vals["instrument_ids"]
            # Lista simples de ids, nunca tupla de comando do Odoo: um
            # `(0, 0, {...})` vindo do cliente criaria registro de instrumento
            # novo pela porta da agenda.
            if not isinstance(ids, (list, tuple)) or not all(
                isinstance(i, int) and not isinstance(i, bool) for i in ids
            ):
                raise UserError(_(
                    "Instrumentos precisam vir como lista de ids."
                ))
            vals["instrument_ids"] = [(6, 0, list(ids))]
```

(c) Bump em `__manifest__.py`:

```python
    "version": "16.0.1.2.0",
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 13 testes na classe, 0 failed, 0 error.

- [ ] **Step 5: Rodar a suíte inteira do módulo**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /opt/odoo/venv/bin/odoo \
  -d qualificacao-dev -u afr_qualificacao_agendamento \
  --test-enable --test-tags afr_qualificacao_agendamento \
  --stop-after-init --no-http --workers=0 --max-cron-threads=0 \
  --db_host=db-qualificacao --db_user=odoo --db_password=odoo 2>&1 \
  | grep -iE 'FAIL:|ERROR:|tests.result'
```

Esperado: `0 failed, 0 error(s) of 112 tests` (99 + 13).

- [ ] **Step 6: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp`, sem push.

```
feat(agendamento): let the agenda write instrument_ids, bump to 16.0.1.2.0

The endpoint takes a plain list of ids and builds the (6, 0, ids) command
server-side. A raw Odoo command tuple from the client is refused: a
(0, 0, {...}) would create an instrument record through the agenda door.
The OS-state lock needs no new code — instrument_ids is already in
_SCHEDULE_FIELDS.
```

---

### Task 4: Dados de instrumento no front

**Files:**
- Modify: `addons/afr_qualificacao/pwa/lib/odoo/agenda.ts`
- Modify: `addons/afr_qualificacao/pwa/lib/hooks/useAgenda.ts`
- Modify: `addons/afr_qualificacao/pwa/lib/odoo/__tests__/agenda.test.ts`

**Interfaces:**
- Consumes: `odooClient.callKw(model, method, args, kwargs)`; `pwa_instrumento_options` (Task 2); `instrument_ids` no payload (Task 1); `instrument_ids` gravável (Task 3).
- Produces:
  - `VisitaAgenda.instrument_ids: number[]`
  - `VisitaVals.instrument_ids?: number[]`
  - `listInstrumentoOptions(): Promise<InstrumentoOpcao[]>`
  - `useInstrumentoOptions(enabled: boolean)`
  A Task 6 consome os dois últimos.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar ao `describe('agenda RPC')` em `lib/odoo/__tests__/agenda.test.ts`:

```ts
  it('listInstrumentoOptions chama o método com sudo do backend', async () => {
    callKw.mockResolvedValue([])
    await listInstrumentoOptions()
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_instrumento_options', [])
  })

  it('updateVisita aceita instrument_ids como lista de ids', async () => {
    callKw.mockResolvedValue({ id: 7 })
    await updateVisita(7, { instrument_ids: [1, 2] })
    expect(callKw).toHaveBeenCalledWith(MODEL, 'pwa_visita_update', [
      7, { instrument_ids: [1, 2] },
    ])
  })
```

e acrescentar `listInstrumentoOptions` à linha de `import` desse arquivo.

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa
npx vitest run lib/odoo/__tests__/agenda.test.ts
```

Esperado: FAIL — `listInstrumentoOptions is not a function` / erro de import.

- [ ] **Step 3: Implementar em `lib/odoo/agenda.ts`**

(a) Na interface `VisitaAgenda`, imediatamente após `instrument_list`:

```ts
  /** Ids dos instrumentos — a folha marca por eles, o painel casa por eles. */
  instrument_ids: number[]
```

(b) Na interface `VisitaVals`, ao fim:

```ts
  /** Lista simples de ids; o servidor monta o `(6, 0, ids)`. */
  instrument_ids?: number[]
```

(c) Tipo e função novos, ao fim do arquivo:

```ts
export interface InstrumentoOpcao {
  id: number
  name: string
  /** Maior `validate_calibration` dos certificados; `false` se não há nenhum. */
  validade: string | false
}

export async function listInstrumentoOptions(): Promise<InstrumentoOpcao[]> {
  return odooClient.callKw<InstrumentoOpcao[]>(
    VISITA_MODEL, 'pwa_instrumento_options', [],
  )
}
```

- [ ] **Step 4: Implementar o hook**

Em `lib/hooks/useAgenda.ts`, acrescentar `listInstrumentoOptions` ao import de
`@/lib/odoo/agenda` e, ao fim do arquivo:

```ts
export function useInstrumentoOptions(enabled: boolean) {
  return useQuery({
    queryKey: ['agenda-instrumentos'],
    queryFn: listInstrumentoOptions,
    staleTime: 5 * 60_000,
    enabled,
  })
}
```

- [ ] **Step 5: Rodar e confirmar que passa**

```bash
npx vitest run
npx tsc --noEmit
```

Esperado: suíte inteira verde (269 do baseline + 2 desta = 271); `tsc` limpo.

> `tsc` vai acusar todo lugar que constrói um `VisitaAgenda` literal sem
> `instrument_ids` — são os helpers `visita()` dos arquivos de teste. Acrescente
> `instrument_ids: []` a cada um. É ajuste de fixture, não de asserção.

- [ ] **Step 6: Commit**

Agente `git-commit-push`, `cwd=.../addons/afr_qualificacao` (submodule), sem push.

```
feat(pwa): carry instrument ids and options through the data layer

Transport only. Instruments go up as a plain list of ids; the server builds
the Odoo command, so the client cannot smuggle a create through it.
```

---

### Task 5: Funções puras de carga e ocupação

**Files:**
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/carga.ts`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/carga.test.ts`

**Interfaces:**
- Consumes: `VisitaAgenda`, `Opcao` e `InstrumentoOpcao` de `@/lib/odoo/agenda` (a Task 4 já criou `InstrumentoOpcao` e o campo `instrument_ids`). Campos de visita usados: `id`, `date`, `time_start`, `time_stop`, `planned_hours`, `os_name`, `tecnico_id`, `tecnico_name`, `instrument_ids`, `conflict`.
- Produces:
  - `Opcao` e `InstrumentoOpcao` reexportados de `@/lib/odoo/agenda`
  - `interface CargaDia { date: string; horas: number; conflito: boolean }`
  - `interface CargaTecnico { id: number; name: string; horas: number }`
  - `interface UsoInstrumento { id: number; name: string; vencido: boolean; usos: { visitaId: number; osName: string; tecnicoName: string; faixa: string }[] }`
  - `cargaPorDia(visitas, dias): CargaDia[]`
  - `cargaPorTecnico(visitas, dia, tecnicos): CargaTecnico[]`
  - `usoPorInstrumento(visitas, dia, instrumentos): UsoInstrumento[]`
  - `diasDaSemana(inicio): string[]`
  - `horaOdoo` é reusada de `../_components/VisitaCard` (já exportada), **não** reimplementada.
  As Tasks 5 e 6 consomem tudo isto.

- [ ] **Step 1: Escrever o teste que falha**

Criar `app/tecnico/qualificacao/__tests__/carga.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import {
  cargaPorDia, cargaPorTecnico, usoPorInstrumento, diasDaSemana,
} from '../agenda/carga'
import type { VisitaAgenda } from '@/lib/odoo/agenda'

function v(over: Partial<VisitaAgenda> = {}): VisitaAgenda {
  return {
    id: 1, date: '2026-09-17', time_start: 8, time_stop: 12, planned_hours: 4,
    os_id: 4, os_name: 'OS26-02', os_state: 'scheduled',
    partner_name: 'Hospital', city: 'São Luís',
    equipment_list: [], instrument_list: [], instrument_ids: [],
    tecnico_id: 441, tecnico_name: 'Afonso', is_mine: true,
    state: 'planned', overflow: false, editable: true, lock_reason: false,
    conflict: false, conflict_msg: '', note: '',
    ...over,
  }
}

describe('diasDaSemana', () => {
  it('devolve 7 dias ISO a partir do início, sem ler o relógio do aparelho', () => {
    const agora = Date.now
    Date.now = () => { throw new Error('relógio do aparelho usado') }
    try {
      expect(diasDaSemana('2026-09-14')).toEqual([
        '2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17',
        '2026-09-18', '2026-09-19', '2026-09-20',
      ])
    } finally {
      Date.now = agora
    }
  })
})

describe('cargaPorDia', () => {
  const dias = ['2026-09-17', '2026-09-18', '2026-09-19']

  it('soma as horas previstas de cada dia', () => {
    const r = cargaPorDia(
      [v({ id: 1, date: '2026-09-17', planned_hours: 4 }),
       v({ id: 2, date: '2026-09-17', planned_hours: 2.5 }),
       v({ id: 3, date: '2026-09-19', planned_hours: 8 })],
      dias,
    )
    expect(r.map((d) => d.horas)).toEqual([6.5, 0, 8])
  })

  it('devolve todos os dias da janela, inclusive os vazios', () => {
    expect(cargaPorDia([], dias).map((d) => d.date)).toEqual(dias)
  })

  it('marca o dia que tem alguma visita em conflito', () => {
    const r = cargaPorDia(
      [v({ id: 1, date: '2026-09-18', conflict: true })], dias,
    )
    expect(r.map((d) => d.conflito)).toEqual([false, true, false])
  })
})

describe('cargaPorTecnico', () => {
  const tecnicos = [
    { id: 441, name: 'Afonso' },
    { id: 9, name: 'Bruno' },
  ]

  it('inclui técnico do roster sem visita nenhuma, com zero hora', () => {
    const r = cargaPorTecnico(
      [v({ tecnico_id: 441, date: '2026-09-17', planned_hours: 4 })],
      '2026-09-17', tecnicos,
    )
    expect(r).toEqual([
      { id: 441, name: 'Afonso', horas: 4 },
      { id: 9, name: 'Bruno', horas: 0 },
    ])
  })

  it('ignora visita de outro dia', () => {
    const r = cargaPorTecnico(
      [v({ tecnico_id: 441, date: '2026-09-18', planned_hours: 4 })],
      '2026-09-17', tecnicos,
    )
    expect(r[0].horas).toBe(0)
  })
})

describe('usoPorInstrumento', () => {
  const instrumentos = [
    { id: 1, name: 'Q001', validade: '2027-01-01' as string | false },
    { id: 2, name: 'Q002', validade: '2026-01-01' as string | false },
    { id: 3, name: 'Q003', validade: false as string | false },
  ]

  it('lista onde cada instrumento está, com a faixa de horário', () => {
    const r = usoPorInstrumento(
      [v({ id: 7, date: '2026-09-17', instrument_ids: [1],
           time_start: 8, time_stop: 12, os_name: 'OS26-02',
           tecnico_name: 'Afonso' })],
      '2026-09-17', instrumentos,
    )
    expect(r[0].usos).toEqual([
      { visitaId: 7, osName: 'OS26-02', tecnicoName: 'Afonso', faixa: '08:00–12:00' },
    ])
    expect(r[1].usos).toEqual([])
  })

  it('um instrumento em duas visitas no mesmo dia aparece com os dois usos', () => {
    const r = usoPorInstrumento(
      [v({ id: 7, date: '2026-09-17', instrument_ids: [1], time_start: 8, time_stop: 12 }),
       v({ id: 8, date: '2026-09-17', instrument_ids: [1], time_start: 13, time_stop: 17 })],
      '2026-09-17', instrumentos,
    )
    expect(r[0].usos.map((u) => u.visitaId)).toEqual([7, 8])
  })

  it('marca vencido quando a validade não alcança o dia, e não marca quando alcança', () => {
    const r = usoPorInstrumento([], '2026-09-17', instrumentos)
    expect(r.map((i) => i.vencido)).toEqual([false, true, true])
  })

  it('validade exatamente igual ao dia ainda vale', () => {
    const r = usoPorInstrumento(
      [], '2026-09-17', [{ id: 1, name: 'Q001', validade: '2026-09-17' }],
    )
    expect(r[0].vencido).toBe(false)
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa
npx vitest run app/tecnico/qualificacao/__tests__/carga.test.ts
```

Esperado: FAIL — `Failed to resolve import "../agenda/carga"`.

- [ ] **Step 3: Implementar**

Criar `app/tecnico/qualificacao/agenda/carga.ts`:

```ts
/**
 * Carga e ocupação da semana — funções puras, sem React e sem relógio local.
 *
 * O servidor decide a janela (`server_today` no payload) e devolve as visitas;
 * tudo aqui é agregação do que já veio. Nenhuma chamada de rede, para que o
 * painel possa ser testado sem montar componente.
 */
import { horaOdoo } from '../_components/VisitaCard'
import type { VisitaAgenda, Opcao, InstrumentoOpcao } from '@/lib/odoo/agenda'

// `InstrumentoOpcao` vem da camada de dados (Task 4), não é redefinido aqui:
// duas interfaces com o mesmo nome divergem na primeira mudança.
export type { Opcao, InstrumentoOpcao }

export interface CargaDia {
  date: string
  horas: number
  conflito: boolean
}

export interface CargaTecnico {
  id: number
  name: string
  horas: number
}

export interface UsoInstrumento {
  id: number
  name: string
  vencido: boolean
  usos: {
    visitaId: number
    osName: string
    tecnicoName: string
    faixa: string
  }[]
}

/** Sete dias ISO a partir de `inicio`, em UTC — nunca lê o relógio do aparelho. */
export function diasDaSemana(inicio: string): string[] {
  const [a, m, d] = inicio.split('-').map(Number)
  const base = Date.UTC(a, m - 1, d)
  return Array.from({ length: 7 }, (_, i) => {
    const dt = new Date(base)
    dt.setUTCDate(dt.getUTCDate() + i)
    return dt.toISOString().slice(0, 10)
  })
}

export function cargaPorDia(
  visitas: VisitaAgenda[],
  dias: string[],
): CargaDia[] {
  return dias.map((date) => {
    const doDia = visitas.filter((v) => v.date === date)
    return {
      date,
      horas: doDia.reduce((s, v) => s + (v.planned_hours || 0), 0),
      conflito: doDia.some((v) => v.conflict),
    }
  })
}

/**
 * Inclui TODO técnico do roster, mesmo sem visita — é justamente para quem
 * está livre que se quer mover.
 */
export function cargaPorTecnico(
  visitas: VisitaAgenda[],
  dia: string,
  tecnicos: Opcao[],
): CargaTecnico[] {
  return tecnicos.map((t) => ({
    id: t.id,
    name: t.name,
    horas: visitas
      .filter((v) => v.date === dia && v.tecnico_id === t.id)
      .reduce((s, v) => s + (v.planned_hours || 0), 0),
  }))
}

export function usoPorInstrumento(
  visitas: VisitaAgenda[],
  dia: string,
  instrumentos: InstrumentoOpcao[],
): UsoInstrumento[] {
  const doDia = visitas.filter((v) => v.date === dia)
  return instrumentos.map((i) => ({
    id: i.id,
    name: i.name,
    // Sem certificado conta como vencido: não há data que alcance o dia.
    // Validade igual ao dia ainda vale — é o mesmo `>=` do
    // `_instrument_valid_on` no servidor.
    vencido: !i.validade || i.validade < dia,
    usos: doDia
      .filter((v) => v.instrument_ids.includes(i.id))
      .map((v) => ({
        visitaId: v.id,
        osName: v.os_name,
        tecnicoName: v.tecnico_name,
        faixa: `${horaOdoo(v.time_start)}–${horaOdoo(v.time_stop)}`,
      })),
  }))
}
```

- [ ] **Step 4: Rodar e confirmar que passa**

```bash
npx vitest run app/tecnico/qualificacao/__tests__/carga.test.ts
npx tsc --noEmit
```

Esperado: 10 testes passando; suíte inteira em 281; `tsc` limpo.

> Se o `tsc` reclamar que `Opcao` não é exportado de `@/lib/odoo/agenda`,
> confira o arquivo: ele já declara `export interface Opcao { id, name }`.

- [ ] **Step 5: Commit**

Agente `git-commit-push`, `cwd=/home/afonso/docker/odoo_engenapp/addons/afr_qualificacao` (submodule), branch `main`, sem push.

```
feat(pwa): add pure load and occupancy helpers for the week view

Aggregation only, over the visits the fetch already returns — no network
and no local clock, so the panel can be tested without mounting anything.
The technician roll-up keeps technicians with no visits at all: an idle
technician is exactly who you want to move work to.
```

---

### Task 6: Faixa de dias e painel de recursos

**Files:**
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/_FaixaDias.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/_PainelRecursos.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/PainelSemana.test.tsx`

**Interfaces:**
- Consumes: `CargaDia`, `CargaTecnico`, `UsoInstrumento`, `InstrumentoOpcao`, `Opcao` (Task 4).
- Produces:
  - `FaixaDias({ dias, selecionado, onSelecionar })` — `dias: CargaDia[]`
  - `PainelRecursos({ dimensao, onTrocarDimensao, tecnicos, instrumentos, instrumentoIdsDaVisita, alvoAtivo, onTocarTecnico, onTocarInstrumento })`
    - `dimensao: 'tecnico' | 'instrumento'`
    - `alvoAtivo: boolean` — quando falso, as linhas são texto, não botão
    - `instrumentoIdsDaVisita: number[]` — marca o que a visita selecionada já usa
  A Task 7 monta os dois.

- [ ] **Step 1: Escrever o teste que falha**

Criar `app/tecnico/qualificacao/__tests__/PainelSemana.test.tsx`:

```tsx
// @vitest-environment happy-dom
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FaixaDias } from '../agenda/_FaixaDias'
import { PainelRecursos } from '../agenda/_PainelRecursos'

const dias = [
  { date: '2026-09-14', horas: 4, conflito: false },
  { date: '2026-09-15', horas: 0, conflito: false },
  { date: '2026-09-16', horas: 12, conflito: true },
]

describe('FaixaDias', () => {
  it('mostra um alvo por dia, com as horas, e marca o selecionado', () => {
    render(<FaixaDias dias={dias} selecionado="2026-09-15" onSelecionar={vi.fn()} />)
    const alvos = screen.getAllByRole('button')
    expect(alvos).toHaveLength(3)
    expect(alvos[1]).toHaveAttribute('aria-pressed', 'true')
    expect(alvos[0]).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('4h')).toBeInTheDocument()
    expect(screen.getByText('12h')).toBeInTheDocument()
  })

  it('dia vazio não mostra "0h"', () => {
    render(<FaixaDias dias={dias} selecionado="2026-09-14" onSelecionar={vi.fn()} />)
    expect(screen.queryByText('0h')).toBeNull()
  })

  it('dia com conflito recebe rótulo acessível', () => {
    render(<FaixaDias dias={dias} selecionado="2026-09-14" onSelecionar={vi.fn()} />)
    expect(screen.getAllByRole('button')[2].getAttribute('aria-label')).toMatch(/conflito/i)
  })

  it('tocar num dia avisa qual', () => {
    const onSelecionar = vi.fn()
    render(<FaixaDias dias={dias} selecionado="2026-09-14" onSelecionar={onSelecionar} />)
    fireEvent.click(screen.getAllByRole('button')[2])
    expect(onSelecionar).toHaveBeenCalledWith('2026-09-16')
  })

  it('todo alvo tem 44px', () => {
    render(<FaixaDias dias={dias} selecionado="2026-09-14" onSelecionar={vi.fn()} />)
    for (const b of screen.getAllByRole('button')) {
      expect(b.className).toContain('min-h-[44px]')
    }
  })
})

const tecnicos = [
  { id: 441, name: 'Afonso', horas: 8 },
  { id: 9, name: 'Bruno', horas: 0 },
]
const instrumentos = [
  { id: 1, name: 'Q001', vencido: false,
    usos: [{ visitaId: 7, osName: 'OS26-02', tecnicoName: 'Afonso', faixa: '08:00–12:00' }] },
  { id: 2, name: 'Q002', vencido: false, usos: [] },
  { id: 3, name: 'Q003', vencido: true, usos: [] },
]

function painel(over = {}) {
  return (
    <PainelRecursos
      dimensao="tecnico"
      onTrocarDimensao={vi.fn()}
      tecnicos={tecnicos}
      instrumentos={instrumentos}
      instrumentoIdsDaVisita={[]}
      alvoAtivo={false}
      onTocarTecnico={vi.fn()}
      onTocarInstrumento={vi.fn()}
      {...over}
    />
  )
}

describe('PainelRecursos — técnico', () => {
  it('técnico sem hora aparece como livre, não como "0h"', () => {
    render(painel())
    expect(screen.getByText(/livre/i)).toBeInTheDocument()
    expect(screen.queryByText('0h')).toBeNull()
  })

  it('sem alvo ativo, as linhas não são botão', () => {
    render(painel())
    expect(screen.queryByRole('button', { name: /Afonso/ })).toBeNull()
  })

  it('com alvo ativo, tocar num técnico avisa qual', () => {
    const onTocarTecnico = vi.fn()
    render(painel({ alvoAtivo: true, onTocarTecnico }))
    fireEvent.click(screen.getByRole('button', { name: /Bruno/ }))
    expect(onTocarTecnico).toHaveBeenCalledWith(9)
  })
})

describe('PainelRecursos — instrumento', () => {
  it('mostra onde o instrumento está, com a faixa de horário', () => {
    render(painel({ dimensao: 'instrumento' }))
    expect(screen.getByText(/08:00–12:00/)).toBeInTheDocument()
    expect(screen.getByText(/OS26-02/)).toBeInTheDocument()
  })

  it('instrumento sem uso aparece como livre', () => {
    render(painel({ dimensao: 'instrumento' }))
    expect(screen.getAllByText(/livre/i).length).toBeGreaterThan(0)
  })

  it('calibração vencida é dita em texto, não só em cor', () => {
    render(painel({ dimensao: 'instrumento' }))
    expect(screen.getByText(/calibra[çc][ãa]o vencida/i)).toBeInTheDocument()
  })

  it('marca o que a visita selecionada já usa', () => {
    render(painel({ dimensao: 'instrumento', alvoAtivo: true, instrumentoIdsDaVisita: [1] }))
    expect(screen.getByRole('button', { name: /Q001/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Q002/ })).toHaveAttribute('aria-pressed', 'false')
  })

  it('com alvo ativo, tocar num instrumento avisa qual', () => {
    const onTocarInstrumento = vi.fn()
    render(painel({ dimensao: 'instrumento', alvoAtivo: true, onTocarInstrumento }))
    fireEvent.click(screen.getByRole('button', { name: /Q002/ }))
    expect(onTocarInstrumento).toHaveBeenCalledWith(2)
  })

  it('o botão de dimensão troca', () => {
    const onTrocarDimensao = vi.fn()
    render(painel({ onTrocarDimensao }))
    fireEvent.click(screen.getByRole('button', { name: /Instrumento/ }))
    expect(onTrocarDimensao).toHaveBeenCalledWith('instrumento')
  })
})
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa
npx vitest run app/tecnico/qualificacao/__tests__/PainelSemana.test.tsx
```

Esperado: FAIL — `../agenda/_FaixaDias` e `../agenda/_PainelRecursos` não resolvem.

- [ ] **Step 3: Implementar `_FaixaDias.tsx`**

```tsx
'use client'
import { clsx } from 'clsx'
import type { CargaDia } from './carga'

/** "2026-09-17" → { sigla: "qua", num: "17" }, em UTC. */
function rotulo(iso: string) {
  const [a, m, d] = iso.split('-').map(Number)
  const dt = new Date(Date.UTC(a, m - 1, d))
  return {
    sigla: new Intl.DateTimeFormat('pt-BR', { weekday: 'short', timeZone: 'UTC' })
      .format(dt).replace('.', ''),
    num: String(d).padStart(2, '0'),
  }
}

/** Horas com no máximo uma casa, sem ".0" pendurado. */
function horasCurtas(h: number): string {
  return `${Number(h.toFixed(1))}h`
}

export function FaixaDias({
  dias,
  selecionado,
  onSelecionar,
}: {
  dias: CargaDia[]
  selecionado: string
  onSelecionar: (date: string) => void
}) {
  return (
    <div className="flex gap-1 rounded-lg border border-border bg-card p-1">
      {dias.map((d) => {
        const { sigla, num } = rotulo(d.date)
        const ativo = d.date === selecionado
        return (
          <button
            key={d.date}
            type="button"
            aria-pressed={ativo}
            aria-label={`${sigla} ${num}, ${horasCurtas(d.horas)}${d.conflito ? ', com conflito' : ''}`}
            onClick={() => onSelecionar(d.date)}
            className={clsx(
              'flex min-h-[44px] flex-1 flex-col items-center justify-center rounded-md px-0.5 py-1',
              ativo ? 'bg-accent font-semibold text-foreground' : 'text-muted-foreground',
            )}
          >
            <span className="text-[10px] uppercase leading-none">{sigla}</span>
            <span className="text-sm leading-tight">{num}</span>
            {/* Dia vazio não escreve "0h": ruído que compete com o que tem carga. */}
            <span className={clsx('text-[10px] leading-none', d.conflito && 'text-danger')}>
              {d.horas > 0 ? horasCurtas(d.horas) : '—'}
            </span>
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Implementar `_PainelRecursos.tsx`**

```tsx
'use client'
import { clsx } from 'clsx'
import { AlertTriangle } from 'lucide-react'
import type { CargaTecnico, UsoInstrumento } from './carga'

export type Dimensao = 'tecnico' | 'instrumento'

const LINHA = 'flex min-h-[44px] w-full items-center gap-3 rounded-md px-3 py-1.5 text-left text-sm'

/**
 * Envolve cada linha. Sem alvo ativo (nenhuma visita em ajuste, ou usuário sem
 * `can_manage`) a linha é texto: oferecer toque que não faz nada é pior que não
 * oferecer.
 */
function Linha({
  ativo, pressionado, aoTocar, children, className,
}: {
  ativo: boolean
  pressionado?: boolean
  aoTocar: () => void
  children: React.ReactNode
  className?: string
}) {
  if (!ativo) return <div className={clsx(LINHA, className)}>{children}</div>
  return (
    <button
      type="button"
      aria-pressed={pressionado ?? false}
      onClick={aoTocar}
      className={clsx(LINHA, 'hover:bg-accent', pressionado && 'bg-accent', className)}
    >
      {children}
    </button>
  )
}

export function PainelRecursos({
  dimensao,
  onTrocarDimensao,
  tecnicos,
  instrumentos,
  instrumentoIdsDaVisita,
  alvoAtivo,
  onTocarTecnico,
  onTocarInstrumento,
}: {
  dimensao: Dimensao
  onTrocarDimensao: (d: Dimensao) => void
  tecnicos: CargaTecnico[]
  instrumentos: UsoInstrumento[]
  instrumentoIdsDaVisita: number[]
  alvoAtivo: boolean
  onTocarTecnico: (id: number) => void
  onTocarInstrumento: (id: number) => void
}) {
  // Escala relativa ao mais cheio da vista: o modelo não define jornada padrão,
  // e fixar 8h aqui seria número fingido.
  const pico = Math.max(1, ...tecnicos.map((t) => t.horas))
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex gap-1 border-b border-border p-1">
        {(['tecnico', 'instrumento'] as const).map((d) => (
          <button
            key={d}
            type="button"
            aria-pressed={dimensao === d}
            onClick={() => onTrocarDimensao(d)}
            className={clsx(
              'min-h-[44px] flex-1 rounded-md text-sm',
              dimensao === d ? 'bg-accent font-semibold' : 'text-muted-foreground',
            )}
          >
            {d === 'tecnico' ? 'Técnico' : 'Instrumento'}
          </button>
        ))}
      </div>

      <div className="p-1">
        {dimensao === 'tecnico' && tecnicos.map((t) => (
          <Linha key={t.id} ativo={alvoAtivo} aoTocar={() => onTocarTecnico(t.id)}>
            <span className="w-28 shrink-0 truncate">{t.name}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-muted" aria-hidden>
              <span
                className="block h-full rounded-full bg-primary"
                style={{ width: `${(t.horas / pico) * 100}%` }}
              />
            </span>
            <span className="w-16 shrink-0 text-right text-xs text-muted-foreground">
              {t.horas > 0 ? `${Number(t.horas.toFixed(1))}h` : 'livre'}
            </span>
          </Linha>
        ))}

        {dimensao === 'instrumento' && instrumentos.map((i) => (
          <Linha
            key={i.id}
            ativo={alvoAtivo}
            pressionado={instrumentoIdsDaVisita.includes(i.id)}
            aoTocar={() => onTocarInstrumento(i.id)}
          >
            <span className="w-20 shrink-0 truncate">{i.name}</span>
            <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
              {i.usos.length === 0
                ? 'livre'
                : i.usos.map((u) => `${u.faixa} · ${u.osName}/${u.tecnicoName}`).join(' | ')}
            </span>
            {/* O aviso é dito em texto, não só em cor: cor sozinha não chega a
                quem não a distingue, e o card fica em tela pequena ao sol. */}
            {i.vencido && (
              <span className="flex shrink-0 items-center gap-1 text-xs text-danger">
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                calibração vencida
              </span>
            )}
          </Linha>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Rodar e confirmar que passa**

```bash
npx vitest run app/tecnico/qualificacao/__tests__/PainelSemana.test.tsx
npx tsc --noEmit
```

Esperado: 12 testes passando; `tsc` limpo.

> Se `bg-muted` não existir no `tailwind.config.ts`, use o token de fundo neutro
> que o projeto já tem (`temaTokens.test.ts` lista os válidos). Não invente cor
> crua.

- [ ] **Step 6: Commit**

Agente `git-commit-push`, `cwd=.../addons/afr_qualificacao` (submodule), sem push.

```
feat(pwa): add the week day strip and the resource panel

Rows are plain text until a visit is being adjusted: offering a tap that
does nothing is worse than offering none. Lapsed calibration is stated in
words, not only in colour. The load bar scales to the busiest technician-day
in view, because the model defines no standard working day and eight hours
would be an invented number.
```

---

### Task 7: Modo Semana e a máquina de seleção

**Files:**
- Modify: `addons/afr_qualificacao/pwa/lib/store/tecnicoSettings.ts`
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/_components/VisitaCard.tsx`
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/agenda/page.tsx`
- Create: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/ModoSemana.test.tsx`
- Modify: `addons/afr_qualificacao/pwa/app/tecnico/qualificacao/__tests__/AgendaLista.test.tsx`
- Modify: `addons/afr_qualificacao/pwa/docs/BASELINE.md`

**Interfaces:**
- Consumes: `FaixaDias`, `PainelRecursos`, `Dimensao` (Task 6); `cargaPorDia`, `cargaPorTecnico`, `usoPorInstrumento`, `diasDaSemana` (Task 4); `useInstrumentoOptions` (Task 5); `useTecnicoOptions`, `useUpdateVisita`, `useAgenda` (já existem); `VisitaCard` (já existe).
- Produces: nada — é a última task.

- [ ] **Step 1: Escrever o teste que falha**

Criar `app/tecnico/qualificacao/__tests__/ModoSemana.test.tsx`:

```tsx
// @vitest-environment happy-dom
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgendaPage from '../agenda/page'
import type { AgendaPayload, VisitaAgenda } from '@/lib/odoo/agenda'

const mutateUpdate = vi.fn()

function visita(over: Partial<VisitaAgenda> = {}): VisitaAgenda {
  return {
    id: 7, date: '2026-09-18', time_start: 8, time_stop: 12, planned_hours: 4,
    os_id: 4, os_name: 'OS26-02', os_state: 'scheduled',
    partner_name: 'Hospital', city: 'São Luís',
    equipment_list: [], instrument_list: [], instrument_ids: [],
    tecnico_id: 441, tecnico_name: 'Afonso', is_mine: true,
    state: 'planned', overflow: false, editable: true, lock_reason: false,
    conflict: false, conflict_msg: '', note: '',
    ...over,
  }
}

const payload: AgendaPayload = {
  server_today: '2026-09-17',
  date_from: '2026-09-17',
  date_to: '2026-09-23',
  my_employee_id: 441,
  can_manage: true,
  visitas: [visita()],
}

let payloadAtual: AgendaPayload = payload

vi.mock('@/lib/hooks/useAgenda', () => ({
  useAgendaDisponivel: () => ({ data: true }),
  useAgenda: () => ({ data: payloadAtual, isLoading: false, error: null }),
  useUpdateVisita: () => ({ mutateAsync: mutateUpdate, isPending: false }),
  useCreateVisita: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteVisita: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useTecnicoOptions: () => ({ data: [{ id: 441, name: 'Afonso' }, { id: 9, name: 'Bruno' }] }),
  useOsOptions: () => ({ data: [] }),
  useInstrumentoOptions: () => ({
    data: [{ id: 1, name: 'Q001', validade: '2027-01-01' }],
  }),
}))

function montar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}><AgendaPage /></QueryClientProvider>,
  )
}

function irParaSemana() {
  fireEvent.click(screen.getByRole('button', { name: /Semana/ }))
}

describe('Modo Semana', () => {
  beforeEach(() => {
    payloadAtual = payload
    mutateUpdate.mockReset().mockResolvedValue(visita())
  })

  it('o botão de modo alterna Lista e Semana', () => {
    montar()
    expect(screen.queryByRole('button', { name: /^Técnico$/ })).toBeNull()
    irParaSemana()
    expect(screen.getByRole('button', { name: /^Técnico$/ })).toBeInTheDocument()
  })

  it('"Só minhas" chega desabilitado no modo Semana', () => {
    montar()
    const filtro = screen.getByRole('checkbox') as HTMLInputElement
    expect(filtro.disabled).toBe(false)
    irParaSemana()
    expect((screen.getByRole('checkbox') as HTMLInputElement).disabled).toBe(true)
  })

  it('tocar num técnico com a visita em ajuste passa a visita para ele', async () => {
    montar()
    irParaSemana()
    fireEvent.click(screen.getByRole('button', { name: /Ajustar/ }))
    fireEvent.click(screen.getByRole('button', { name: /Bruno/ }))
    await waitFor(() =>
      expect(mutateUpdate).toHaveBeenCalledWith({ id: 7, vals: { tecnico_id: 9 } }),
    )
  })

  it('tocar num dia com a visita em ajuste move para aquele dia', async () => {
    montar()
    irParaSemana()
    fireEvent.click(screen.getByRole('button', { name: /Ajustar/ }))
    fireEvent.click(screen.getByRole('button', { name: /^sáb 19/i }))
    await waitFor(() =>
      expect(mutateUpdate).toHaveBeenCalledWith({ id: 7, vals: { date: '2026-09-19' } }),
    )
  })

  it('tocar num instrumento liga, e tocar de novo desliga', async () => {
    montar()
    irParaSemana()
    fireEvent.click(screen.getByRole('button', { name: /Ajustar/ }))
    fireEvent.click(screen.getByRole('button', { name: /^Instrumento$/ }))
    fireEvent.click(screen.getByRole('button', { name: /Q001/ }))
    await waitFor(() =>
      expect(mutateUpdate).toHaveBeenCalledWith({ id: 7, vals: { instrument_ids: [1] } }),
    )
    payloadAtual = { ...payload, visitas: [visita({ instrument_ids: [1] })] }
    mutateUpdate.mockClear()
    fireEvent.click(screen.getByRole('button', { name: /Q001/ }))
    await waitFor(() =>
      expect(mutateUpdate).toHaveBeenCalledWith({ id: 7, vals: { instrument_ids: [] } }),
    )
  })

  it('erro do servidor aparece em tarja e a seleção não se perde', async () => {
    mutateUpdate.mockRejectedValue(
      new Error('Não é possível programar uma visita para uma data passada'),
    )
    montar()
    irParaSemana()
    fireEvent.click(screen.getByRole('button', { name: /Ajustar/ }))
    fireEvent.click(screen.getByRole('button', { name: /Bruno/ }))
    await waitFor(() =>
      expect(screen.getByText(/data passada/)).toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: /Concluir/ })).toBeInTheDocument()
  })

  it('sem can_manage não há "Ajustar" e o painel não vira alvo', () => {
    payloadAtual = {
      ...payload, can_manage: false,
      visitas: [visita({ editable: false, lock_reason: 'Somente o Gestor edita a agenda.' })],
    }
    montar()
    irParaSemana()
    expect(screen.queryByRole('button', { name: /Ajustar/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Bruno/ })).toBeNull()
  })
})
```

Acrescentar `instrument_ids: []` ao helper `visita()` de
`__tests__/AgendaLista.test.tsx` se a Task 5 ainda não tiver feito.

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
cd /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa
npx vitest run app/tecnico/qualificacao/__tests__/ModoSemana.test.tsx
```

Esperado: FAIL — não há botão `Semana`.

- [ ] **Step 3: Preferência de modo no store**

Em `lib/store/tecnicoSettings.ts`:

```ts
export type ModoAgenda = 'lista' | 'semana'

interface TecnicoSettings {
  filterMine: boolean
  lastUserId: number | null
  modoAgenda: ModoAgenda
  setFilterMine: (v: boolean) => void
  setLastUserId: (id: number | null) => void
  setModoAgenda: (m: ModoAgenda) => void
}
```

e, dentro do `persist`:

```ts
      modoAgenda: 'lista',
      setModoAgenda: (modoAgenda) => set({ modoAgenda }),
```

- [ ] **Step 4: Botão "Ajustar" no card**

Em `_components/VisitaCard.tsx`, a assinatura passa a aceitar duas props
opcionais, para a Lista continuar funcionando sem mudança:

```tsx
export function VisitaCard({
  visita,
  onSelect,
  onAjustar,
  emAjuste = false,
}: {
  visita: VisitaAgenda
  onSelect: (visita: VisitaAgenda) => void
  /** Só o modo Semana passa isto; sem ele, não há botão. */
  onAjustar?: (visita: VisitaAgenda) => void
  emAjuste?: boolean
}) {
```

No ramo editável, o `<button>` do card passa a ser embrulhado:

```tsx
  return (
    <div className={clsx('flex flex-col gap-1', emAjuste && 'rounded-lg ring-2 ring-primary')}>
      <button type="button" onClick={() => onSelect(visita)} className={clsx(base, 'hover:bg-accent')}>
        <Corpo visita={visita} />
      </button>
      {onAjustar && (
        <button
          type="button"
          onClick={() => onAjustar(visita)}
          className="min-h-[44px] rounded-md border border-border px-3 text-sm font-medium"
        >
          {emAjuste ? 'Concluir' : 'Ajustar'}
        </button>
      )}
    </div>
  )
```

O ramo travado (`!visita.editable`) fica **igual** — não ganha `Ajustar`.

- [ ] **Step 5: Montar o modo na página**

Em `agenda/page.tsx`:

(a) Imports novos:

```tsx
import { FaixaDias } from './_FaixaDias'
import { PainelRecursos, type Dimensao } from './_PainelRecursos'
import { cargaPorDia, cargaPorTecnico, usoPorInstrumento, diasDaSemana } from './carga'
import { useTecnicoOptions, useInstrumentoOptions, useUpdateVisita } from '@/lib/hooks/useAgenda'
import { mensagemDeFalha } from '@/lib/odoo/client'
import { clsx } from 'clsx'
import type { VisitaVals } from '@/lib/odoo/agenda'
```

`clsx`, `mensagemDeFalha` e `VisitaVals` ainda NÃO são importados neste arquivo
hoje — confira a lista de imports antes de assumir que estão lá.

(b) Estado novo, junto dos que já existem:

```tsx
  const { modoAgenda, setModoAgenda } = useTecnicoSettings()
  const semana = modoAgenda === 'semana'
  const [diaSel, setDiaSel] = useState<string | null>(null)
  const [dimensao, setDimensao] = useState<Dimensao>('tecnico')
  const [emAjuste, setEmAjuste] = useState<VisitaAgenda | null>(null)
  const [erroAjuste, setErroAjuste] = useState('')
  const update = useUpdateVisita()
```

(c) A janela encurta no modo Semana — trocar o `JANELA_DIAS` fixo por:

```tsx
  const janelaDias = semana ? 7 : 14
  const fim = inicio ? deslocarJanela(inicio, janelaDias - 1) : null
```

e as duas setas de navegação passam a usar `janelaDias` no lugar de `JANELA_DIAS`.

(d) O filtro fica desabilitado no modo Semana — no `<input id="agenda-filter-mine">`:

```tsx
          disabled={semana || semEmpregado}
```

e o texto de apoio ganha o ramo:

```tsx
            {semana
              ? 'Desligado na semana: a carga é da equipe'
              : semEmpregado
                ? 'Seu usuário não tem técnico vinculado'
                : filterMine
                  ? 'Visitas atribuídas a você'
                  : 'Visitas de toda a equipe'}
```

(e) Botão de modo, logo acima da navegação de janela:

```tsx
      <div className="flex gap-1 rounded-lg border border-border bg-card p-1">
        {(['lista', 'semana'] as const).map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={modoAgenda === m}
            onClick={() => setModoAgenda(m)}
            className={clsx(
              'min-h-[44px] flex-1 rounded-md text-sm',
              modoAgenda === m ? 'bg-accent font-semibold' : 'text-muted-foreground',
            )}
          >
            {m === 'lista' ? 'Lista' : 'Semana'}
          </button>
        ))}
      </div>
```

(f) A máquina de seleção. Uma função só, para que os três alvos não divirjam:

```tsx
  /**
   * Cada toque no painel grava UM campo. A visita em ajuste continua
   * selecionada depois do erro: o Gestor precisa poder tentar outro alvo sem
   * recomeçar.
   */
  async function ajustar(vals: VisitaVals) {
    if (!emAjuste) return
    setErroAjuste('')
    try {
      await update.mutateAsync({ id: emAjuste.id, vals })
    } catch (e) {
      setErroAjuste(e instanceof Error && e.message ? e.message : mensagemDeFalha(e))
    }
  }
```

(g) O corpo do modo Semana, substituindo a lista agrupada quando `semana`:

```tsx
  const dias = ancora ? diasDaSemana(ancora) : []
  const diaAtual = diaSel && dias.includes(diaSel) ? diaSel : dias[0] ?? ''
  const visitas = data?.visitas ?? []
  const doDia = visitas.filter((v) => v.date === diaAtual)
```

e, no JSX:

```tsx
      {semana && (
        <>
          <FaixaDias
            dias={cargaPorDia(visitas, dias)}
            selecionado={diaAtual}
            onSelecionar={(d) => (emAjuste ? ajustar({ date: d }) : setDiaSel(d))}
          />
          {erroAjuste && <p className="text-sm text-danger">{erroAjuste}</p>}
          <PainelRecursos
            dimensao={dimensao}
            onTrocarDimensao={setDimensao}
            tecnicos={cargaPorTecnico(visitas, diaAtual, tecnicos.data ?? [])}
            instrumentos={usoPorInstrumento(visitas, diaAtual, instrumentos.data ?? [])}
            instrumentoIdsDaVisita={emAjuste?.instrument_ids ?? []}
            alvoAtivo={!!emAjuste}
            onTocarTecnico={(id) => ajustar({ tecnico_id: id })}
            onTocarInstrumento={(id) => {
              const atuais = emAjuste?.instrument_ids ?? []
              ajustar({
                instrument_ids: atuais.includes(id)
                  ? atuais.filter((x) => x !== id)
                  : [...atuais, id],
              })
            }}
          />
          {doDia.map((v) => (
            <VisitaCard
              key={v.id}
              visita={v}
              onSelect={setSelecionada}
              onAjustar={data?.can_manage ? (x) => setEmAjuste(emAjuste?.id === x.id ? null : x) : undefined}
              emAjuste={emAjuste?.id === v.id}
            />
          ))}
          {doDia.length === 0 && (
            <p className="py-6 text-center text-muted-foreground">Nenhuma visita neste dia.</p>
          )}
        </>
      )}
```

com `const tecnicos = useTecnicoOptions(semana)` e
`const instrumentos = useInstrumentoOptions(semana && dimensao === 'instrumento')`
junto dos outros hooks. A lista agrupada existente passa a ficar dentro de
`{!semana && (...)}`.

**Importante:** `emAjuste` guarda a visita como ela estava ao ser selecionada.
Depois de cada gravação bem-sucedida, o `onSuccess` do `useUpdateVisita`
invalida a busca e o payload volta atualizado — mas `emAjuste` continua com a
cópia velha. Resolver ressincronizando a partir do payload:

```tsx
  const emAjusteAtual = emAjuste
    ? visitas.find((v) => v.id === emAjuste.id) ?? emAjuste
    : null
```

e usar `emAjusteAtual` em `instrumentoIdsDaVisita` e no cálculo do toggle de
instrumento. Sem isso, ligar dois instrumentos em sequência desligaria o
primeiro.

- [ ] **Step 6: Rodar e confirmar que passa**

```bash
npx vitest run
npx tsc --noEmit
```

Esperado: suíte inteira verde (281 + 12 da Task 6 + 7 desta = 300); `tsc` limpo.

- [ ] **Step 7: Atualizar a baseline**

Em `pwa/docs/BASELINE.md`, acrescentar uma seção nova datada de 2026-09-17 com a
contagem final e os arquivos novos. Não reescrever as seções anteriores.

- [ ] **Step 8: Validar na UI, por `agent-browser`**

Regra do projeto: testar a interface eu mesmo, não delegar o clique ao user.

1. `~/.claude/bin/devserver list` antes de subir qualquer coisa.
2. Se não houver servidor do PWA de pé:
   `~/.claude/bin/devserver start --port 3012 --dir /home/afonso/docker/odoo_engenapp/addons/afr_qualificacao/pwa`
   (o script `dev` fixa `-p 3010`; o app escuta na 3010 mesmo assim).
3. Aquecer `/login` e `/tecnico/qualificacao/agenda` com `curl`.
4. Entrar como `gestor@teste.local` / `teste1234` no banco `qualificacao-dev`
   (servidor `http://localhost:8084`).
5. Conferir, com screenshot: o botão Semana aparece; a faixa mostra carga; o
   painel troca Técnico ⇄ Instrumento; "Ajustar" seleciona; tocar num técnico
   move; tocar num instrumento liga e desliga; um erro de servidor cai na tarja.

- [ ] **Step 9: Commit**

Agente `git-commit-push`, `cwd=.../addons/afr_qualificacao` (submodule), sem push.

```
feat(pwa): add the week mode with tap-to-adjust

The panel that shows who is free is also the target of the gesture, so no
separate move flow exists. Tapping a card still opens the sheet, as in the
list — adjusting starts from its own button, so one touch never means two
things. "Só minhas" is disabled here: load per day and per technician only
means something with the whole team in view.
```

---

## Notas de integração

- **Nenhum método de mutação novo.** Dia, técnico e instrumento vão todos por
  `pwa_visita_update`, que já é guardado por `_check_manager_only` e já carrega
  as quatro travas. O modo Semana não abre superfície nova de escrita.
- **Granularidade do "livre":** o painel diz livre por **dia**, mas o conflito
  do modelo é por **janela sobreposta**. Por isso cada linha ocupada mostra o
  horário. Está registrado na spec como decisão, não como descuido.
- **Avisos seguem não bloqueantes**, como no modelo e no board OWL: gravar é
  permitido, a tarja de conflito aparece no card depois.
- **Relógio do WSL pode estar adiantado**; `sudo hwclock -s` dentro do WSL antes
  de confiar em timestamp lido à mão. Não quebra os testes (as datas do backend
  são relativas a `context_today`, e o front usa `server_today`).
- **Débito prévio, inalterado:** os `board_*` seguem sem guard contra o grupo
  Usuário, e `_local_to_utc` usa `self.env.user.tz` — os dois já registrados
  como follow-up na spec anterior.
