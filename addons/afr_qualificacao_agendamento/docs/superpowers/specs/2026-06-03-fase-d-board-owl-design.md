# Fase D — Board OWL (Gantt técnico × dia) — Design

- **Módulo:** `afr_qualificacao_agendamento` (Odoo 16.0 Community, OWL 2)
- **Data:** 2026-06-03
- **Status:** Design aprovado (aguarda revisão do spec antes do plano)
- **Depende de:** Fases A/B/C (modelo visita + conflitos). Commits `fcc178e`, `11090b1` (+ Fase C uncommitted).
- **Design geral:** `afr_qualificacao/docs/superpowers/specs/2026-06-03-agendamento-visitas-qualificacao-design.md` (§7)

## 1. Problema e objetivo

A Fase A entregou o calendar nativo sobre visitas. A Fase D entrega o **board
de gestão**: uma grade Gantt **técnico (linhas) × dia (colunas)** que mostra a
ocupação de cada técnico, destaca conflitos e permite **reagendar arrastando**.
É a tela principal de planejamento de campo.

## 2. Decisões (brainstorm 2026-06-03)

| Tema | Decisão |
|---|---|
| Layout | Técnico (linhas) × Dia (colunas), Gantt de recurso |
| Linhas | Técnicos com ≥1 visita no intervalo |
| Horizonte | Intervalo **configurável** (date pickers; default semana atual) + ‹ › Hoje |
| Barra | Cor por OS; vermelho se qualquer conflito; tooltip OS/cliente/horas/conflito |
| Drag | Solta na célula → nova **data + técnico** → grava (`board_reschedule`) → refetch |
| Clique | Abre o **form da visita** (service `action`) |
| Arquitetura | `ir.actions.client` OWL (padrão CME totem) + 2 métodos Python testáveis |

## 3. Arquitetura

### Abordagem escolhida — client action OWL + métodos de dados no backend

`ir.actions.client` com `tag="afr_qualif_visita_board"`, componente OWL
registrado em `registry.category("actions")`. O componente lê/escreve via
`useService("orm").call(...)` de dois métodos Python em
`afr.qualificacao.os.visita` (testáveis com TDD). A lógica de dados fica no
Python; o OWL renderiza a grade e trata drag/clique. Segue o padrão do
`afr_cme_rastreabilidade/static/src/cme_totem/` (component + xml template + scss,
`registry.category("actions").add`).

### Abordagens rejeitadas
- **OCA `web_timeline`** — novo dependency, menos controle; o usuário escolheu
  OWL custom na Fase A.
- **Calendar nativo** — já entregue na Fase A; não dá a grade técnico×dia.

## 4. Backend — métodos em `afr.qualificacao.os.visita`

### `board_fetch(date_from, date_to)`  `@api.model`
Recebe duas datas (string ISO). Retorna dict serializável:
```python
{
  "technicians": [{"id": int, "name": str}, ...],   # técnicos com visita no range, ordenados por nome
  "visitas": [
    {
      "id": int,
      "tecnico_id": int,
      "date": "YYYY-MM-DD",
      "os_id": int,
      "os_name": str,
      "partner_name": str,
      "planned_hours": float,
      "state": str,                      # planned/done
      "equipment_names": str,            # join ", "
      "conflict": bool,                  # any(4 conflitos)
      "conflict_msg": str,               # join das msgs ativas
    }, ...
  ],
}
```
Domínio: `[("date", ">=", date_from), ("date", "<=", date_to)]`. `technicians`
derivado dos `tecnico_id` distintos das visitas do range. `conflict` =
`tecnico_conflict or travel_conflict or instrument_conflict or
calibration_conflict`; `conflict_msg` concatena as `*_msg` não-vazias.

### `board_reschedule(visita_id, new_date, new_tecnico_id)`  `@api.model`
`browse(visita_id).write({"date": new_date, "tecnico_id": new_tecnico_id})`.
Os conflitos recomputam no próximo read (não-stored). Retorna `True`.
Valida que a visita não está `done` (não reagenda realizada) → `UserError` se for.

## 5. Frontend — componente OWL `visita_board`

Arquivos em `static/src/board/`:
- `visita_board.js` — `class VisitaBoard extends Component`:
  - `useState({date_from, date_to, technicians:[], visitas:[]})`.
  - `onWillStart` → `_fetch()`. Default range = semana atual (segunda→domingo).
  - `_fetch()` → `orm.call("afr.qualificacao.os.visita","board_fetch",[from,to])`.
  - Navegação: `prevRange()`, `nextRange()`, `today()`, e inputs de data
    (`onChangeFrom/To`) que refazem `_fetch`.
  - Grade: dias = lista de datas entre from/to; para cada técnico×dia, filtra
    visitas. `cellVisitas(tecnicoId, day)`.
  - Cor por OS: `colorIndex(os_id)` = `os_id % N` → classe CSS de paleta.
  - Drag HTML5: `onDragStart(ev, visitaId)` seta dataTransfer; `onDrop(ev,
    tecnicoId, day)` → `orm.call(...,"board_reschedule",[id, day, tecnicoId])`
    → `_fetch()`. `onDragOver` previne default.
  - Clique: `openVisita(id)` → `action.doAction({type:"ir.actions.act_window",
    res_model:"afr.qualificacao.os.visita", res_id:id, views:[[false,"form"]],
    target:"new"})`.
  - `registry.category("actions").add("afr_qualif_visita_board", VisitaBoard)`.
- `visita_board.xml` — template QWeb-OWL: toolbar (date pickers + ‹ › Hoje),
  tabela grid (thead = dias, 1ª coluna = técnico, células com barras
  arrastáveis), estado vazio.
- `visita_board.scss` — grid, barras coloridas (paleta), `.conflict` vermelho,
  hover/drag styles.

### Ação + menu (`views/visita_board_action.xml`)
```xml
<record id="action_visita_board" model="ir.actions.client">
    <field name="name">Quadro de Agenda</field>
    <field name="tag">afr_qualif_visita_board</field>
</record>
<menuitem id="menu_visita_board" name="Quadro de Agenda"
          parent="afr_qualificacao.menu_afr_qualificacao_root"
          action="action_visita_board" sequence="8"/>
```

### Manifest
```python
"assets": {
    "web.assets_backend": [
        "afr_qualificacao_agendamento/static/src/board/visita_board.scss",
        "afr_qualificacao_agendamento/static/src/board/visita_board.xml",
        "afr_qualificacao_agendamento/static/src/board/visita_board.js",
    ],
},
```

## 6. Testes
- **Python (TDD, `tests/test_board.py`):**
  - `test_board_fetch_structure`: cria visitas em datas; `board_fetch` retorna
    `technicians` distintos + `visitas` com os campos esperados.
  - `test_board_fetch_range`: visita fora do intervalo não aparece.
  - `test_board_fetch_conflict_flag`: visita com conflito (ex: técnico duplo) →
    `conflict=True` e `conflict_msg` não-vazio.
  - `test_board_reschedule`: grava nova `date` + `tecnico_id`.
  - `test_board_reschedule_done_blocked`: visita `done` → `UserError`.
- **OWL/JS:** teste manual/visual no navegador (8083) — não há infra de teste JS
  neste stack (consistente com o CME totem, que também não tem testes JS).

## 7. Riscos e atenção
- **JS sem teste automatizado:** a lógica testável foi empurrada pro Python
  (`board_fetch`/`board_reschedule`); o OWL é fino e validado manualmente.
- **Drag-drop HTML5 manual** (sem lib): há precedente zero no repo; usar
  `draggable=true` + dataTransfer. Manter simples.
- **Performance:** intervalos muito largos trazem muitas visitas; `board_fetch`
  filtra por range. Sem paginação em v1 (volume de visitas é baixo).
- **Linhas só de técnicos com visita:** criar visita p/ técnico novo não é feito
  no board (precisa de OS) — usa motor/aba (Fases B/A). Documentado.
- **Reschedule de `done`** bloqueado p/ não alterar histórico.
