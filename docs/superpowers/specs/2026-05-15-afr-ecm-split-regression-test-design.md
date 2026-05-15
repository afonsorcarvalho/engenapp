# afr_ecm Split Regression Test — Design

**Data:** 2026-05-15
**Contexto:** Após o split SGQ (commit afr_ecm `70ad6d3`, monorepo `da88805`), confirmar que nenhum teste do afr_ecm que passava antes do split passou a falhar. Verificação binária, sem alteração de código.

## Objetivo

Provar (ou refutar) numericamente que o split SGQ não introduziu regressões na suite de testes do afr_ecm. Saída esperada: lista de regressões — vazia = aprovado.

## Não-objetivos (YAGNI)

- Não corrige nenhum teste falho.
- Não roda smoke UI nem checks MCP.
- Não testa fresh-install (débito pré-existente, fora de escopo).
- Não testa afr_sgq (escopo é apenas afr_ecm).
- Não faz backup de DB (DB é descartável, só para teste).

## Setup

| Item | Valor |
|---|---|
| DB | `odoo-ecm-teste-local` (Postgres no container `db`, pré-configurada com os 12 `dms.access.group` manuais incluindo `Auditor_Externo` linkado) |
| Web container | parado durante cada run (evita locks) |
| Submodule afr_ecm | alterna entre `97bf320` (pré-split, baseline) e `main` = `70ad6d3` (pós-split, treatment) |
| Comando base | `docker compose run --rm --no-deps web -d odoo-ecm-teste-local -u afr_ecm --test-tags afr_ecm --stop-after-init --workers=0 --max-cron-threads=0` |
| Logs | `/tmp/baseline_afr_ecm.log`, `/tmp/treatment_afr_ecm.log` |

## Passos

1. **Snapshot do estado** — `git -C addons/afr_ecm rev-parse HEAD` deve ser `70ad6d3`. Verificar working tree limpo (`git -C addons/afr_ecm status --porcelain` vazio). Caso contrário, abortar.
2. **Baseline (97bf320)** — `docker compose stop web`; `git -C addons/afr_ecm checkout 97bf320`; rodar comando base; redirect → `/tmp/baseline_afr_ecm.log`.
3. **Treatment (70ad6d3)** — `git -C addons/afr_ecm checkout main`; rodar mesmo comando; redirect → `/tmp/treatment_afr_ecm.log`.
4. **Parser** — script Python ~30 linhas: para cada log, extrai pares `(class.method, status)` via regex nas linhas `Starting <class>.<method>` (registro de execução) + linhas `FAIL:` / `ERROR:` (status final). `pass = startedSet - failSet - errorSet`. Monta `baseline_pass`, `baseline_fail`, `treatment_pass`, `treatment_fail`.
5. **Diff** —
   - **Regressões** = `baseline_pass ∩ treatment_fail` (tests que passavam e agora falham)
   - **Pré-existentes** = `baseline_fail ∩ treatment_fail` (já falhavam, esperado)
   - **Ganho** = `baseline_fail ∩ treatment_pass` (improvável, info-only)
   - **Sumidos** = `baseline_pass - treatment_started` (testes que não existem mais no treatment, ex.: SGQ tests que foram pra afr_sgq) — info-only, não conta como regressão
6. **Restart web** — `docker compose up -d web`.
7. **Relatório** — markdown em `/tmp/afr_ecm_regression_report.md`: contagens, lista de regressões, lista de pré-existentes, lista de sumidos.

## Critério de aprovação

**Zero regressões** = split limpo. Qualquer item em `baseline_pass ∩ treatment_fail` requer investigação.

## Tratamento de erro

- Working tree afr_ecm sujo no início → STOP, reportar, sem mudanças feitas.
- `git checkout 97bf320` falha → STOP, reportar.
- Baseline ou treatment crash antes de rodar testes (install error) → log capturado, abortar comparação, reportar logs.
- Parser acha 0 testes em qualquer log → tag filter quebrado, STOP, reportar.

## Cleanup garantido

Independente de sucesso ou falha:
- `git -C addons/afr_ecm checkout main` (retorna ao estado publicado `70ad6d3`).
- `docker compose up -d web` (web volta no ar).

Logs em `/tmp/*.log` ficam para inspeção; podem ser removidos pelo user depois.

## Estimativa

~10 min de compute (dois runs da suite afr_ecm × ~3-4 min cada + parser + relatório).

## Saídas

- `/tmp/baseline_afr_ecm.log`
- `/tmp/treatment_afr_ecm.log`
- `/tmp/afr_ecm_regression_report.md` (markdown human-readable com diff)
- Mensagem final: contagem de regressões. Zero = aprovado.
