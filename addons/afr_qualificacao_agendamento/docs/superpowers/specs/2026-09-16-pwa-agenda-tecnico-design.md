# Agenda de Visitas no PWA Técnico — design

**Data:** 2026-09-16
**Módulos:** `afr_qualificacao_agendamento` (backend), `afr_qualificacao/pwa` (front)
**Versão alvo do módulo:** `16.0.1.1.0` (feat)

## Problema

O técnico em campo não tem como ver a própria agenda de visitas. O modelo
`afr.qualificacao.os.visita` existe e é planejado no Quadro de Agenda (board
OWL) do backend, mas o backend do Odoo não é usável no celular — o PWA é o
único cliente que o técnico abre em campo.

Junto disso, quem coordena a equipe precisa reagendar de dentro de campo, sem
voltar ao desktop.

## Decisões de produto

1. **Técnico comum: leitura.** Vê a agenda inteira da equipe, não edita nada.
2. **Gestor (`group_afr_qualificacao_manager`): CRUD completo** nas portas
   `pwa_*` da agenda — cria, edita e apaga visita. A frase vale para essas
   portas, não para o modelo: o ACL de `afr.qualificacao.os.visita` mantém
   `write`/`create` para o grupo Usuário (`1,1,1,0`, inalterado por decisão
   explícita desta spec — ver seção Segurança), e quem tem esse grupo alcança
   o modelo direto por `call_kw`, sem passar pelo guard de Gestor.
3. **As travas de agendamento existentes continuam valendo, inclusive para o
   Gestor.** Nenhuma regra de negócio é relaxada por causa desta feature.
4. **Aba nova "Agenda"**, lista agrupada por dia, janela de 14 dias.

## Segurança

### ACL (`security/ir.model.access.csv`)

| Grupo | Antes | Depois | Motivo |
|---|---|---|---|
| technician | `1,1,0,0` | **`1,0,0,0`** | Técnico é leitor. O write existia sem nenhuma `ir.rule` por trás, então hoje qualquer técnico reescreve visita de qualquer colega via `call_kw` direto. |
| user | `1,1,1,0` | `1,1,1,0` | Inalterado — o board OWL do backend depende disso. |
| manager | `1,1,1,1` | `1,1,1,1` | Inalterado. Já tem unlink; nada a conceder. |

**Risco a validar:** tirar write do técnico é aperto numa ACL existente. A
verificação é a suíte backend inteira (`afr_qualificacao` +
`afr_qualificacao_agendamento`), não só os testes novos. Auditoria feita
durante o design não achou nenhum fluxo que escreva visita como técnico — o
rollup `date_planned_start` em `afr.qualificacao.os` apenas lê
`visita_ids.date_start/date_stop`.

### Sem `ir.rule`

Nenhuma regra de registro é criada. Leitura é global por desenho (decisão 1) e
escrita é decidida pela ACL + guard de Gestor. Uma versão anterior deste design
previa `ir.rule` restritiva mais um campo `tecnico_user_id` armazenado, para
escopar o write do técnico à própria visita; com o técnico virando leitor, os
dois perderam função e foram removidos do escopo.

### Guard de servidor

`afr.qualificacao.os.visita` passa a herdar
`afr.qualificacao.manager.guard.mixin` e todos os métodos `pwa_*` de escrita
chamam `_check_manager_only(...)` antes de qualquer coisa.

O guard é obrigatório no servidor, não basta esconder o botão: o proxy
`/api/odoo` do PWA repassa `call_kw` sem allowlist de modelo/método, então
qualquer sessão autenticada alcança qualquer método público.

A hierarquia é `manager ⊃ user ⊃ technician` (`implied_ids` em
`qualificacao_groups.xml:26-37`). Como a implicação desce, um Usuário comum
**não** está no grupo Gestor e o guard o barra — ao contrário do que acontece
com regras de registro, onde a implicação faz o Gestor cair na regra
restritiva do Técnico e exige o par OR'ed.

**Guard é parcial, não completo.** Ele protege os métodos `pwa_*` — a
superfície nova desta feature. Ele NÃO protege os métodos `board_*`
pré-existentes do mesmo modelo (`board_split_overflow`, `board_delete_visita`,
`board_set_hours`, `board_reschedule`, `board_create_visita`), que não têm
nenhum guard e continuam alcançáveis por `call_kw` sem allowlist — o mesmo
proxy `/api/odoo` que motiva o guard nos `pwa_*` vale igual para eles.

Contra o Técnico isso não importa: o ACL já barra `write`/`create` do grupo
technician (`1,0,0,0`, decisão desta spec), então `call_kw` num `board_*`
falha na ACL antes de chegar ao método. Mas contra o Usuário o guard dos
`pwa_*` é **cosmético**: o grupo Usuário mantém ACL de escrita completa
(`1,1,1,0`) e os `board_*` não perguntam por Gestor, então um Usuário comum
alcança o mesmo efeito de `board_create_visita`/`board_delete_visita`/etc.
que um Gestor teria pelos `pwa_*` — só que sem passar pelo guard. O guard só
é *load-bearing* contra o Técnico, que a ACL já bloqueia de qualquer jeito.

Follow-up nomeado, fora do escopo desta feature: ou (a) adicionar guard de
Gestor aos `board_*`, ou (b) tirar o write do grupo Usuário do ACL e dar ao
board OWL do backend um caminho de Gestor. Nenhuma das duas foi feita aqui.

### Divulgação aceita

`pwa_agenda_fetch` não tem guard e devolve a agenda da equipe inteira, com
`partner_name`, `city` e `conflict_msg` de todos. `conflict_msg` é montado por
`_compute_conflicts`, que interpola o **nome da OS conflitante** — ou seja, um
técnico enxerga nomes de OS e clientes de colegas. É consequência direta da
decisão 1 (leitura global) e está aceita, não é descuido. Restringir isso
depois significa escopar a leitura, não remendar a mensagem.

### Travas preservadas

- `write()` recusa `date`/`time_start`/`time_stop`/`planned_hours`/`tecnico_id`/
  `os_id`/`equipment_ids`/`instrument_ids` quando `os_id.state` não está em
  `("draft", "scheduled")`.
- `_board_check_not_done()` — visita `state == "done"` é registro de fato,
  imutável e não apagável.
- `_check_date_not_past` — visita não-`done` não vai para data passada.
- `_check_equipment_overlap` — o mesmo equipamento não fica em duas visitas
  sobrepostas.

## Backend — métodos novos

Todos em `models/os_visita.py`, prefixo `pwa_` para não se confundir com os
`board_*` (que servem o board OWL e têm outro contrato).

### `pwa_agenda_fetch(date_from=None, date_to=None, only_mine=True)`

`@api.model`. Sem guard — leitura é liberada a todos os grupos.

**Datas vazias: o servidor define a janela** —
`fields.Date.context_today(self)` até `+13` dias. O payload devolve
`server_today` e a janela usada, e o front navega sempre a partir desses
valores. O front nunca chama `Date.now()` para decidir "hoje": o relógio do
aparelho é fonte conhecida de defeito neste app (ver `todayRangeOdoo` no
`pwa/TODO.md`) e o servidor já é a fonte de tempo do relatório diário.

`only_mine` filtra por `tecnico_id == env.user.employee_id`, resolvido com
`sudo()` — o técnico não lê `hr.employee`.

**Usuário sem empregado vinculado** (caso comum do Gestor administrativo):
`my_employee_id` volta `False`, `only_mine` é ignorado e a agenda inteira é
devolvida. Sem isso, a tela abriria vazia e sem explicação. O front desabilita
o toggle "Só minhas" quando `my_employee_id` é falso.

**Retorno:**

```python
{
  "server_today": "2026-09-16",
  "date_from": "2026-09-16",
  "date_to": "2026-09-29",
  "my_employee_id": 441,
  "can_manage": False,          # has_group(manager)
  "visitas": [
    {
      "id": 12, "date": "2026-09-17",
      "time_start": 8.0, "time_stop": 12.0, "planned_hours": 4.0,
      "os_id": 4, "os_name": "OS26-06-0002", "os_state": "scheduled",
      "partner_name": "Hospital São Lucas", "city": "São Luís",
      "equipment_list": ["Autoclave 01", "Autoclave 02"],
      "instrument_list": ["TAG-114"],
      "tecnico_id": 441, "tecnico_name": "Afonso",
      "is_mine": True, "state": "planned", "overflow": False,
      "editable": False, "lock_reason": "Somente o Gestor edita a agenda.",
      "conflict": True, "conflict_msg": "Deslocamento ...",
      "note": ""
    }
  ]
}
```

`editable` e `lock_reason` são decididos **no servidor**:

| Condição (na ordem) | `editable` | `lock_reason` |
|---|---|---|
| não é Gestor | `False` | `"Somente o Gestor edita a agenda."` |
| `state == "done"` | `False` | `"Visita já realizada."` |
| `os_state` fora de draft/scheduled | `False` | `"OS em execução (<rótulo>)."` |
| resto | `True` | `False` |

O front pinta o cadeado e o texto; não reimplementa a regra.

`board_fetch` não é reusado: devolve a agenda da equipe inteira sem janela
escopada, sem noção de quem pode editar e sem `server_today`.

### `pwa_visita_update(visita_id, vals)`

`@api.model`. `_check_manager_only("editar a agenda de visitas")`.

Whitelist rígida de chaves: `date`, `time_start`, `time_stop`, `tecnico_id`,
`note`. Qualquer outra chave levanta `UserError` — fecha `os_id`, `state`,
`equipment_ids`, `instrument_ids`.

Ordem: guard → `_board_check_not_done()` → `planned_hours = time_stop -
time_start` quando os dois vierem e `stop > start` → `write()` normal (sem
`sudo`: o Gestor tem write de verdade, e o `write()` do modelo é justamente
onde mora a trava de estado da OS que queremos honrar).

Devolve a linha atualizada, no mesmo serializer do `pwa_agenda_fetch`, para o
front atualizar o cache sem refetch.

`ValidationError` das constraints (equipamento sobreposto, data passada) sobe
sem tratamento — a mensagem do modelo é a mensagem que o usuário precisa ler.

### `pwa_visita_create(os_id, tecnico_id, date)`

`@api.model`. Guard de Gestor. Cria a visita mínima — mesmo conjunto de campos
do `board_create_visita`. Devolve a linha serializada.

### `pwa_visita_delete(visita_id)`

`@api.model`. Guard de Gestor → `_board_check_not_done()` → `unlink()`. O
`unlink()` do modelo já recusa OS fora de draft/scheduled.

### Reuso

`board_technician_options()` e `board_os_options()` servem os seletores da tela
de criação sem alteração. Não duplicar.

## Front — PWA

### Rota e navegação

`app/tecnico/qualificacao/agenda/page.tsx`. `NAV_ITEMS` em `TecnicoNav.tsx`
ganha a entrada `{ href: '<root>/agenda', label: 'Agenda', Icon: CalendarDays }`
entre OSs e Histórico, e `useActiveHref()` ganha o ramo correspondente. A
entrada única serve as duas variantes (`bottom` e `side`).

### Detecção do módulo

O PWA é publicado dentro de `afr_qualificacao`; o modelo vive em
`afr_qualificacao_agendamento`, que **depende** de `afr_qualificacao`. A
dependência aponta ao contrário do que o uso sugere, então o PWA não pode
assumir que o modelo existe.

`useAgendaDisponivel()`: um `search_count` em `ir.model` por
`afr.qualificacao.os.visita`, `staleTime: Infinity`, uma vez por sessão. Falso →
o item da nav não é renderizado e a rota, se alcançada por URL, mostra um
estado vazio explicativo em vez de erro de RPC.

### Lista

- Agrupada por data, cabeçalho de dia grudento.
- `[◀] 16–22 set [▶]` movendo a janela de 14 em 14 dias a partir de
  `server_today`.
- Toggle "Só minhas" persistido em `tecnicoSettings` (zustand), como o da home.
- Card: OS, cliente, faixa de horário, equipamentos, badge de conflito quando
  `conflict`. Alvo de toque ≥44px (o técnico usa luva).
- Card não editável: cadeado e `lock_reason` em texto, sem afordância de toque.

### Edição (só Gestor)

Não existe Modal genérico no projeto — só `PdfViewerModal`. Entra um
`BottomSheet` em `components/ui/`: folha vinda de baixo com data, hora início,
hora fim, técnico (`board_technician_options`), observações, salvar e apagar.

- Apagar pede confirmação e usa o token `--destructive` (DESIGN.md: `danger` é
  estado, `destructive` é o botão que apaga).
- Erro de constraint aparece dentro da folha, sem fechá-la.
- FAB "+ Nova visita" só para Gestor, abre a mesma folha em modo criação com os
  seletores de OS e técnico.

### Cache

Sucesso de qualquer mutação invalida `['agenda', ...]` **e** `['tecnico-os',
...]`: `date_planned_start`/`date_planned_end` da OS são rollup computado das
visitas, e a home do PWA mostra esse campo no card da OS.

Escrita é online-only, como o resto deste PWA (não há outbox; o data layer é
react-query com persistência de cache).

## Fora de escopo

- Arrastar-e-soltar para reagendar (o board OWL do backend faz isso).
- Botão de split de overflow (`board_split_overflow`).
- Marcar visita como realizada (`state = done`).
- Relaxar qualquer trava de agendamento existente.
- Regra de registro multi-empresa no modelo de visita (não existe hoje;
  introduzi-la é decisão à parte).

## Testes

### Backend — `tests/test_pwa_agenda.py` (novo)

Matriz de papel:

| Ator | `pwa_agenda_fetch` | `update` / `create` / `delete` |
|---|---|---|
| técnico | passa | `UserError` do guard |
| usuário | passa | `UserError` do guard |
| gestor | passa | passa |

Mais:

- `editable`/`lock_reason` corretos por estado: OS `scheduled` → editável;
  OS `in_progress` → travada com o rótulo do estado; visita `done` → travada.
- Whitelist: `{"os_id": X}` e `{"state": "done"}` levantam `UserError`.
- Janela: sem datas, devolve `server_today` e 14 dias; com datas, respeita.
- `only_mine` filtra por empregado do usuário.
- **Constraint dispara por hora, não só por data:** `_check_equipment_overlap`
  observa `date_start`/`date_stop`, que são *computed stored* derivados de
  `date`/`time_start`/`time_stop`. Um `pwa_visita_update` que mexe só em
  `time_start`/`time_stop` para dentro de uma sobreposição precisa levantar
  `ValidationError`. Se não levantar, a promessa de "travas preservadas" é
  falsa e o conserto entra no plano — não se descobre isso no Bloco H.
- **Regressão de delegação:** `pwa_agenda_fetch` chamado por usuário sem
  permissão em HR. É a armadilha `hr.employee` / `hr.employee.public` que já
  mordeu este módulo (`is_tecnico`) e o `engc_os`.
- Suíte completa dos dois módulos, para provar que tirar write do técnico não
  regrediu nenhum fluxo.

### Front — vitest

Baseline em `pwa/docs/BASELINE.md` está limpo: qualquer falha é regressão.

- Card bloqueado renderiza o motivo e não oferece toque.
- Agrupamento por dia e navegação de janela não chamam `Date.now()`.
- Mutação invalida as duas query keys.
- Item da nav some quando `useAgendaDisponivel()` é falso.
- Folha de edição só aparece com `can_manage`.

## Débito conhecido que esta feature empilha

O Bloco H (H1–H12) de `pwa/app/tecnico/qualificacao/F7_0_TEST_CHECKLIST.md` é o
portão de aceitação do PWA Técnico e nunca foi executado, com um bloqueio
conhecido: item `kind='outro'` sem anexo levanta `ValidationError`
(`models/qualificacao_collect_item.py:269-276` exige `file` para qualquer
`state='collected'`, enquanto o front trata o anexo como opcional).
