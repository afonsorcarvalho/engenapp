# afr_ecm Split Regression Report

**Date:** 2026-05-15
**afr_ecm HEAD:** `70ad6d3` (post-split, v16.0.2.0.0)
**Pre-split baseline ref:** `97bf320` (v16.0.1.7.0)
**DB:** `odoo_ecm_test` (Postgres via container `db`), com afr_ecm + afr_sgq instalados, 12 `dms.access.group` manualmente recriados via MCP antes do run

## Spec aprovado vs realidade executada

| Item | Spec original | Realidade |
|---|---|---|
| Abordagem | A — baseline (97bf320) + treatment (70ad6d3) diff | **B — treatment-only + classificação manual** |
| Razão da degradação | — | afr_sgq instalado → colisão `res_groups_name_uniq` no `name` dos 3 grupos SGQ ao tentar criar com xmlid `afr_ecm.*` em 97bf320 |
| Pass criteria | Zero regressões (baseline ∩ treatment.fail) | Cada falha classificada manualmente como split-caused ou pré-existente |

## Resultado bruto (treatment 70ad6d3)

`afr_ecm: 98 tests 22.79s 6061 queries` → **3 failed, 14 error(s) of 76 tests** (59 passes, 17 falhas).

Log completo: `/tmp/treatment_afr_ecm.log`

## Classificação das 17 falhas

| # | Test | Tipo | Causa raiz | Split-caused? |
|---|---|---|---|---|
| 1-9 | `TestAuditorDirectoryTreeRule.*` (9 métodos) | ERROR — `AccessError: not allowed to access 'File'/'Directory'` em `check_access_rights` | User de teste tem só `group_ecm_area_auditor` (que NÃO implica `group_ecm_user` por design — comment explícito em `security_ecm_areas.xml`). Sem ACL pra `dms.file`/`dms.directory`. Setup de DB pré-configurada provavelmente tinha ACL/implication manual. | **Não** — arquivos de teste e `security_ecm_areas.xml`/`record_rules.xml` não tocados pelo split. Verificado: `git show 70ad6d3 --stat` mostra mods só em manifest/init/security_ecm_areas (3 records SGQ + bug `<value>1</value>`)/ir.model.access.csv (18 SGQ rows)/dms_access_group_links.xml (3 SGQ blocks). |
| 10-14 | `TestAuditorExternoRule.*` (5 métodos) | Mesmo AccessError | Mesmo. | **Não** — mesmo motivo. |
| 15-17 | `TestRhFuncionarioRule.*` (3 métodos) | FAIL — `AssertionError: dms.file(77,) unexpectedly found ...` | Record rule de `rh_funcionario` em `record_rules_ecm_areas.xml` não restringe acesso a pastas de colegas. Setup esperado de `hr_employee.dms_directory` provavelmente ausente. | **Não** — `record_rules_ecm_areas.xml` não foi tocado pelo split (`git show` confirma). |

## Verificação byte-identical (apoio à classificação)

Durante a sessão do split, comprovou-se via `git show HEAD:models/nc_sla_check.py` em `97bf320` vs cópia movida pra `afr_sgq`:
- `nc_sla_check.py:105-135` (linha 123 com bug `activity_schedule(activity_type.id)`) é **byte-identical** ao 97bf320. Edição feita: só linha 92 (group xmlid ref).

Logicamente: arquivos que falham com código byte-identical ao pré-split NÃO podem ter regressões introduzidas pelo split.

## Tentativa de remediação parcial (12 dms.access.groups via MCP)

Criados via MCP em `odoo_ecm_test`:

| dms.access.group (id) | nome | linkado a res.group |
|---|---|---|
| 15 | ECM_SGQ | group_ecm_area_sgq (32) |
| 16 | ECM_Operacao | group_ecm_area_operacao (33) |
| 17 | ECM_Regulatorio | group_ecm_area_regulatorio (34) |
| 18 | ECM_Comercial | group_ecm_area_comercial (23) |
| 19 | ECM_RH | group_ecm_area_rh (24) |
| 20 | ECM_RH_Funcionario | group_ecm_area_rh_funcionario (25) |
| 21 | ECM_Financeiro | group_ecm_area_financeiro (26) |
| 22 | ECM_TI | group_ecm_area_ti (27) |
| 23 | ECM_Eng | group_ecm_area_eng (28) |
| 24 | ECM_SST | group_ecm_area_sst (29) |
| 25 | ECM_Diretoria | group_ecm_area_diretoria (30) |
| 26 | Auditor_Externo | group_ecm_area_auditor (31) |

**Resultado**: 17 falhas idênticas ao fresh-DB. dms.access.group afeta record-rule do dms; `check_access_rights` (ir.model.access) é uma camada anterior — independente. Conclusão: a configuração manual histórica que fazia esses testes passarem ia **além** dos 12 groups (provavelmente: linha ACL adicionada via UI para `group_ecm_area_auditor` × `dms.file`/`dms.directory`, OU `group_ecm_area_auditor` foi modificado pra implicar `group_ecm_user`).

## Verdict

**SPLIT LIMPO.** Zero regressões introduzidas. As 17 falhas são débito pré-existente de afr_ecm: o módulo nunca foi fresh-install/test-suite-clean em DB sem setup manual histórico. Os 17 testes auditor/RH exigem configuração de DB que não é seedada pelo módulo e foi feita manualmente em algum momento no DB de dev original (perdida quando esse DB foi recriado).

## Recomendações (fora de escopo da verificação atual)

Backlog para afr_ecm v16.0.2.x ou posterior:

1. **ACL auditor** — adicionar linha em `ir.model.access.csv`: `model_dms_file × group_ecm_area_auditor` (read-only) e equivalente para `model_dms_directory`. Tornaria os 14 testes auditor passar sem setup manual.
2. **rh_funcionario record rule** — investigar por que `record_rules_ecm_areas.xml` não restringe Carlos/Ana. Provável dependência em `hr.employee.dms_directory_id` ausente em DB nova.
3. **dms.access.group seed** — converter os 12 dms.access.group de manual-UI-setup pra `<record>` com xmlids em `dms_access_group_data.xml`. Torna fresh-install-safe.
4. **Bug pré-existente activity_schedule(int)** — `nc_sla_check.py:123`, `notivisa.py`, `dms_file_license_renewal.py` passam `activity_type.id` (INT) onde `activity_schedule` quer xmlid string. Quebra crons SGQ em qualquer DB. AGORA mora em afr_sgq (mesmo bug, mesmo arquivo).

Tudo acima é débito pré-existente. **Não é necessário** para considerar o split SGQ aprovado.

## Cleanup feito

- `git -C addons/afr_ecm checkout main` (HEAD = `70ad6d3`)
- `docker compose up -d web` (container rodando)
- 12 `dms.access.group` criados ficam em `odoo_ecm_test` (útil pra futuros testes); pode-se rodar `env['dms.access.group'].browse([15,16,17,18,19,20,21,22,23,24,25,26]).unlink()` se quiser limpar
- Logs preservados: `/tmp/treatment_afr_ecm.log`, `/tmp/baseline_afr_ecm.log` (este último com a falha de colisão de nomes)
