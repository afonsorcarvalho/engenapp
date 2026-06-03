# Fase B — Motor de Sugestão de Visitas — Design

- **Módulo:** `afr_qualificacao_agendamento` (Odoo 16.0 Community)
- **Data:** 2026-06-03
- **Status:** Design aprovado (aguarda revisão do spec antes do plano)
- **Depende de:** Fase A (modelo `afr.qualificacao.os.visita`, commit `fcc178e`)
- **Design geral:** `afr_qualificacao/docs/superpowers/specs/2026-06-03-agendamento-visitas-qualificacao-design.md` (§5)
- **Plano Fase A:** `afr_qualificacao_agendamento/docs/superpowers/plans/2026-06-03-agendamento-visitas-fase-a.md`

## 1. Problema e objetivo

A Fase A entregou o modelo de visitas e o agendamento manual. A Fase B adiciona
o **motor assistivo**: a partir do técnico e da data de início escolhidos pelo
humano, gerar automaticamente as visitas diárias de uma OS, distribuindo as
horas estimadas (técnico-dias F5.8.0) pelos dias. O humano confirma e ajusta.

## 2. Decisões (brainstorm 2026-06-03)

| Tema | Decisão |
|---|---|
| Autonomia | Assistivo: humano escolhe técnico + data início; motor gera; humano ajusta |
| Empacotamento | Por equipamento, sequencial; equipamentos do mesmo `parallel_group` compartilham os mesmos dias (paralelo); solo em sequência. 1 equipamento/grupo por bloco |
| Dias | **Corridos** (inclui fim de semana); sem feriados |
| Re-execução | Substitui visitas `state='planned'`; **preserva** `state='done'` |
| Fonte das horas | `sale.order._qualif_schedule_rows()` (técnico-dias F5.8.0); **não** F10 |
| Modelo | Reusa `afr.qualificacao.os.visita` da Fase A — **nenhum campo novo** |
| Invocação | Wizard transient (botão "Sugerir visitas" na OS) |

## 3. Arquitetura

### Abordagem escolhida — wizard + método de serviço

Botão "Sugerir visitas" na OS abre um wizard transient
(`afr.qualificacao.os.suggest.wizard`) com `tecnico_id` (default
`tecnico_default_id`) e `date_start` (default hoje). O botão do wizard chama
`os._suggest_visitas(tecnico, date_start)` — método de serviço isolado e
testável no modelo OS (herança do satélite). A lógica não vive no wizard.

### Abordagens rejeitadas
- **Botão direto sem wizard** (usa `tecnico_default_id` + hoje): fere o modelo
  assistivo (humano deve escolher).
- **Auto-gerar no confirm da SO**: automático demais; contradiz "humano ajusta".

## 4. Algoritmo `_suggest_visitas(tecnico, date_start)`

Método em `afr.qualificacao.os` (via `_inherit` no satélite). Passos:

1. **Limpa** as visitas `state='planned'` da OS (`visita_ids.filtered(planned).unlink()`);
   **preserva** `state='done'`.
2. **Fonte de dados:** `rows = self.sale_order_id._qualif_schedule_rows()` →
   lista de dicts `{equipment, hours, work_hours_per_day, days}` na ordem de
   aparição. Se `not self.sale_order_id`: `raise UserError` ("OS sem pedido de
   venda; não há horas estimadas para sugerir visitas.").
3. **Agrupa por `parallel_group`:** para cada equipment, lê o `parallel_group`
   da qualificação correspondente (`self.qualificacao_ids` filtradas por
   `equipment_id`). Rótulo não-vazio → membros do mesmo bloco (paralelo);
   vazio → bloco solo (1 equipment). Preserva a ordem de primeira aparição dos
   blocos.
4. **Por bloco**, sequencialmente:
   - **Bloco solo** (equip com `H` horas, jornada `J`):
     `n = ceil(H / J)` visitas em dias corridos. Dias cheios recebem
     `planned_hours = J`; o último recebe o resto `H - (n-1)*J` (se `H` não é
     múltiplo de `J`). `equipment_ids = [equip]`.
   - **Bloco paralelo** (N equips, cada um `Hₘ`/`Jₘ`):
     `block_days = max(ceil(Hₘ / Jₘ))` dias corridos. Cada visita:
     `equipment_ids` = todos os membros; `planned_hours` = jornada representativa
     do bloco `Jb = max(Jₘ)` em **todos** os dias do bloco (aproximação v1; o
     humano ajusta). *(Paralelo é aproximação — não modela resto/proporção por
     dia; sugestão para o humano refinar.)*
5. **Datas:** aloca dias consecutivos (corridos) a partir de `date_start`,
   bloco após bloco (a próxima visita continua do dia seguinte ao último dia do
   bloco anterior). `sequence` incrementa 10, 20, 30… `tecnico_id` = o escolhido.
   Modo dia (sem `time_start`/`time_stop`). `travel_buffer_hours = 0`
   (mesmo cliente dentro da OS).
6. **Conflitos:** os campos computados da Fase A (`tecnico_conflict`,
   `travel_conflict`) recalculam sozinhos ao ler — sinalizam se o técnico já
   tem visitas em outra OS no período.

**Exemplos:**
- Autoclave 20h @ 8h/dia → 3 visitas: 8h, 8h, 4h (dias `date_start`, +1, +2).
- Grupo "A" {Estufa 16h, Incubadora 8h} @ 8h/dia → bloco de 2 dias; cada uma das
  2 visitas tem `equipment_ids = [Estufa, Incubadora]`.

## 5. Componentes e arquivos (no `afr_qualificacao_agendamento`)

```
afr_qualificacao_agendamento/
├── __manifest__.py                         # + wizards/views no data
├── wizards/
│   ├── __init__.py                         # from . import suggest_visitas_wizard
│   └── suggest_visitas_wizard.py           # afr.qualificacao.os.suggest.wizard (transient)
├── models/qualificacao_os.py               # + _suggest_visitas() + action_open_suggest_wizard()
├── views/
│   ├── suggest_visitas_wizard_views.xml     # form do wizard
│   └── qualificacao_os_views.xml           # + botão "Sugerir visitas" no form da OS
└── tests/test_suggest.py                   # TDD
```

- `__init__.py` (raiz) passa a importar `wizards` além de `models`.
- Wizard: campos `os_id` (M2o, required), `tecnico_id` (M2o hr.employee,
  required, default do `os_id.tecnico_default_id`), `date_start` (Date, required,
  default hoje). Botão `action_generate` → chama `os._suggest_visitas(...)` e
  retorna ação que reabre a OS (ou a agenda da OS).
- Botão na OS: `action_open_suggest_wizard` abre o wizard com
  `default_os_id`, `default_tecnico_id`, `default_date_start`.

## 6. Testes (TDD)

- `test_solo_equipment_day_split`: 1 equip 20h @ 8h → 3 visitas com
  `planned_hours` [8, 8, 4] em datas corridas.
- `test_exact_multiple`: 16h @ 8h → 2 visitas [8, 8].
- `test_parallel_group_shares_days`: 2 equips mesmo `parallel_group`,
  16h e 8h @ 8h → 2 visitas, cada uma com os 2 equipamentos.
- `test_sequential_blocks_dates`: 2 equips solo → blocos consecutivos, datas
  não se sobrepõem e seguem a ordem.
- `test_rerun_replaces_planned_preserves_done`: rodar 2× só recria planejadas;
  visita marcada `done` sobrevive.
- `test_no_sale_order_raises`: OS sem `sale_order_id` → `UserError`.

## 7. Riscos e atenção

- **Bloco paralelo é aproximação:** `planned_hours` por dia num grupo paralelo
  não modela exatamente o esforço simultâneo; é sugestão para o humano ajustar.
- **`_qualif_schedule_rows` depende de dados de cotação corretos** (jornada e
  horas nas section lines). OS sem esses dados → blocos com 0 dias (ignorados).
- **Dias corridos** podem cair em fim de semana — decisão consciente (v1).
- **Conflito entre OSes:** o motor não resolve automaticamente; apenas as visitas
  geradas herdam a detecção de conflito da Fase A (aviso não-bloqueante).
