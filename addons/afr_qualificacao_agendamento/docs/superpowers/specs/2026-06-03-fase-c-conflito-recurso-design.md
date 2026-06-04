# Fase C — Conflito de Recurso e Calibração — Design

- **Módulo:** `afr_qualificacao_agendamento` (Odoo 16.0 Community)
- **Data:** 2026-06-03
- **Status:** Design aprovado (aguarda revisão do spec antes do plano)
- **Depende de:** Fase A (modelo visita) + Fase B (motor). Commits `fcc178e`, `11090b1`.
- **Design geral:** `afr_qualificacao/docs/superpowers/specs/2026-06-03-agendamento-visitas-qualificacao-design.md` (§6)

## 1. Problema e objetivo

As Fases A/B detectam conflito de técnico e deslocamento. A Fase C fecha a
detecção de conflito adicionando os recursos metrológicos: avisar quando um
**instrumento** (validador/padrão) está prometido em duas OS no mesmo período,
e quando a **calibração** de um instrumento está vencida na data da visita.
Ambos são avisos **não-bloqueantes** (alerta + decoração), coerentes com as
Fases A/B.

## 2. Decisões (brainstorm 2026-06-03)

| Tema | Decisão |
|---|---|
| Fonte dos instrumentos | **Atribuição manual** por visita (M2m `instrument_ids`, stored, editável) |
| Conveniência | Botão **"Puxar do plano F10"** pré-preenche `instrument_ids` a partir das linhas do plano de recursos cujos equipamentos batem com os da visita |
| Conflito de recurso | Mesmo instrumento em **OS diferente** com janela de data sobreposta |
| Conflito de calibração | Instrumento sem certificado válido na **data da visita** (`validate_calibration >= visita.date`) |
| Severidade | Não-bloqueante (alerta no form + decoração na tree) |
| Escopo | Tudo no satélite `afr_qualificacao_agendamento` — **zero mudança no submodule pai** |

## 3. Modelo de dados (`afr.qualificacao.os.visita`)

Campos novos (no satélite, `os_visita.py`):

| Campo | Tipo | Notas |
|---|---|---|
| `instrument_ids` | Many2many → `engc.calibration.instruments` | "Instrumentos (validador/padrão)"; stored, editável; relation própria |
| `instrument_conflict` | Boolean (computed, non-stored) | Instrumento duplo-alocado |
| `instrument_conflict_msg` | Char (computed) | Descrição |
| `calibration_conflict` | Boolean (computed, non-stored) | Calibração vencida na data |
| `calibration_conflict_msg` | Char (computed) | Lista instrumentos vencidos |

`instrument_ids` é **stored** → pesquisável no domínio da busca de conflito.
Os 4 campos de conflito seguem o padrão não-stored das Fases A/B.

## 4. Lógica — `_compute_resource_conflicts` (método novo)

`@api.depends("instrument_ids", "date", "date_start", "date_stop")`. Para cada
visita `r`:

- **Conflito de recurso (instrumento duplo):**
  Se `r.instrument_ids`, busca outra visita com:
  `os_id != r.os_id` (mesma OS usando o instrumento em vários dias **não** é
  conflito), `instrument_ids in r.instrument_ids.ids`, e janela sobreposta
  (`date_start < r.date_stop AND date_stop > r.date_start`), excluindo
  `r._origin.id`. Se achar → `instrument_conflict=True`, msg com o instrumento e
  a OS conflitante.
- **Conflito de calibração (vencida):**
  Para cada `inst` em `r.instrument_ids`, válido na data se
  `any(c.validate_calibration and c.validate_calibration >= r.date
  for c in inst.certificate_ids)`. Instrumentos sem certificado válido →
  `calibration_conflict=True`, msg listando os vencidos. (`r.date` é a Date da
  visita; suficiente para granularidade-dia.)

Helper privado no satélite (sem tocar o pai):
```python
def _instrument_valid_on(self, instrument, day):
    return any(
        c.validate_calibration and c.validate_calibration >= day
        for c in instrument.certificate_ids
    )
```

## 5. Botão "Puxar do plano F10" — `action_pull_instruments_from_plan`

Método na visita: preenche `instrument_ids` a partir do plano de recursos da OS,
filtrando pelas linhas cujos equipamentos intersectam os da visita:
```python
def action_pull_instruments_from_plan(self):
    self.ensure_one()
    lines = self.os_id.resource_plan_line_ids.filtered(
        lambda l: l.instrument_id and (l.equipment_ids & self.equipment_ids)
    )
    self.instrument_ids = [(6, 0, lines.mapped("instrument_id").ids)]
    return True
```
Se a OS não tem plano F10 calculado, não faz nada (lista vazia). O humano edita
livremente depois.

## 6. Views (`os_visita_views.xml` + `qualificacao_os_views.xml`)

- **Form da visita:** campo `instrument_ids` (widget `many2many_tags`) na seção
  de equipamentos; botão "Puxar do plano F10" (`action_pull_instruments_from_plan`)
  ao lado; 2 blocos de alerta novos (`instrument_conflict_msg`,
  `calibration_conflict_msg`) com `attrs` invisible.
- **Tree da visita** (standalone e embed na OS): coluna `instrument_ids`
  (many2many_tags) opcional; `decoration-danger` passa a incluir
  `instrument_conflict or calibration_conflict` (além de técnico/deslocamento).
- Campos de conflito novos como `invisible="1"` na tree (para a decoração).

## 7. Segurança
Nenhum modelo novo. `instrument_ids` referencia `engc.calibration.instruments`
(usuários já têm leitura via stack engc). Sem nova linha em `ir.model.access.csv`.

## 8. Testes (TDD)
- `test_instrument_conflict_overlap`: 2 OS, mesmo instrumento, datas sobrepostas
  → ambas `instrument_conflict=True`.
- `test_no_instrument_conflict_diff_dates`: mesmo instrumento, datas distintas
  → sem conflito.
- `test_no_instrument_conflict_same_os`: 2 visitas da **mesma** OS com o mesmo
  instrumento → sem conflito.
- `test_calibration_expired`: instrumento com certificado `validate_calibration`
  < data da visita → `calibration_conflict=True`.
- `test_calibration_valid`: certificado `validate_calibration` >= data → sem
  conflito.
- `test_calibration_no_certificate`: instrumento sem certificado → conflito.
- `test_pull_instruments_from_plan`: cria resource_plan_line com instrument_id +
  equipment_ids; botão preenche `instrument_ids` da visita pelos equipamentos.

## 9. Riscos e atenção
- **Conflito de recurso não filtra estado da OS** (igual Fases A/B): visitas de
  OS em rascunho também contam. Refinamento futuro: limitar a OS comprometidas.
- **Calibração:** instrumento sem `certificate_ids` é tratado como vencido
  (conflito) — conservador e correto para liberar serviço.
- **Fixtures de teste** precisam de `engc.calibration.instruments` +
  `...certificates` (com `validate_calibration`) e `resource.plan.line`; montar
  no `setUp`.
- **Campos non-stored de conflito** não entram em filtro de busca (como nas
  Fases A/B) — só decoração/alerta.
