# afr_sgq — Split de Módulo (SGQ + Operação + Regulatório)

## Context

O módulo `afr_ecm` cresceu de um ECM corporativo genérico para incluir, nas fases F4.3.x, workflows verticais de qualidade/saúde: Não-Conformidade (NC), CAPA, Recall, NOTIVISA (tecnovigilância), renovação de licenças e sumário de ciclos de esterilização. Esses workflows são específicos do domínio CME/RDC 15/ISO 13485 e não pertencem a um ECM genérico.

**Objetivo:** extrair SGQ + Operação + Regulatório para um novo módulo `afr_sgq` instalável opcionalmente sobre `afr_ecm`. `afr_ecm` volta a ser ECM corporativo genérico; `afr_sgq` é a camada vertical de qualidade/saúde.

**Decisões do brainstorm (2026-05-14):**
- "Assistente" = ajuda no split (refactor de código), **sem wizard runtime**.
- `audit_scope` (auditoria externa) **fica em afr_ecm** — auditor audita qualquer área, conceito genérico. Não há integração SGQ-específica atual.
- afr_sgq = **puro código** (models/workflows/grupos/crons/regras). **Zero seed de taxonomia** — doc types e estrutura de pastas continuam dados runtime (criados via MCP/UI).
- DB de teste será **recriada fresca pós-split** — sem migration scripts.
- afr_sgq = **novo submódulo git** (mesma política do afr_ecm): repo `github.com/afonsorcarvalho/afr_sgq`, branch `main`, path `addons/afr_sgq`, commits de dentro do dir.

## Abordagem escolhida: A — Split limpo, afr_sgq puro código

Novo módulo `afr_sgq` com `depends=['afr_ecm']`. Move models/views/data/security/tests dos 3 domínios. afr_ecm remove tudo isso e faz bump de versão. xmlids atualizados nas referências cruzadas.

Rejeitadas: B (overlay por flag — não é split real, afr_ecm continua gordo); C (split + migration scripts — over-engineering dado DB fresca).

---

## Fronteira dos módulos

### Vai para `afr_sgq`

| Categoria | Arquivos |
|---|---|
| **Models (8)** | `nc.py`, `nc_sla_check.py`, `capa.py` (SGQ); `recall.py`, `dms_file_recall_trigger.py`, `dms_file_cycle_summary.py` (Operação); `notivisa.py`, `dms_file_license_renewal.py` (Regulatório) |
| **Views (7)** | `nc_views.xml`, `capa_views.xml`, `recall_views.xml`, `notivisa_views.xml`, `menus_nc_capa.xml`, `menus_recall.xml`, `menus_notivisa.xml` |
| **Data (9)** | `sequence_nc_capa.xml`, `sequence_notivisa.xml`, `sequence_recall.xml`, `cron_capa_verification.xml`, `cron_cycle_summary.xml`, `cron_license_renewal.xml`, `cron_nc_sla.xml`, `cron_notivisa_overdue.xml`, `cron_recall_overdue.xml` |
| **Security** | `record_rules_nc_capa.xml`, `record_rules_notivisa.xml`, `record_rules_recall.xml`; novo `security_sgq_groups.xml` com 3 res.groups (`group_ecm_area_sgq`, `_operacao`, `_regulatorio`); novo `ir.model.access.csv` com rows de `afr.ecm.nc`/`afr.ecm.capa`/`afr.ecm.recall`/`afr.ecm.notivisa` |
| **Tests (6)** | `test_nc_capa.py`, `test_nc_sla.py`, `test_recall.py`, `test_notivisa.py`, `test_cycle_summary.py`, `test_license_renewal.py` |

### Fica em `afr_ecm` (base ECM genérico)

- Models: `approval_action`, `approval_level`, `audit_log`, `audit_mixin`, `audit_scope`, `dms_directory`, `dms_file`, `document_type`, `hr_employee_revocation`, `dms_file_revocation_cron`, `metadata_field`, `metadata_value`, `physical_location`
- Views: `audit_log_views`, `audit_scope_views`, `dms_directory_views`, `dms_file_views`, `document_type_views`, `menus`, `physical_location_views`
- Data: `cron_audit_scope_expire`, `cron_data`, `cron_ti_revocation`, `dms_access_group_data`, `dms_access_group_links` (versão 9-grupos), `document_type_data`, `mail_activity_data`
- Security: `ir.model.access.csv` (sem rows SGQ), `record_rules.xml`, `record_rules_ecm_areas.xml` (RH_funcionario + auditor — nenhuma é SGQ), `security.xml`, `security_ecm_areas.xml` (9 grupos + categoria)
- Tests: `test_approval`, `test_audit_log`, `test_audit_scope_tree_rule`, `test_document_type`, `test_expiration`, `test_ocr`, `test_physical_location`, `test_record_rules_refinement`, `test_ti_revocation`

**Racional de casos de fronteira:**
- `audit_scope` + grupo `group_ecm_area_auditor` + rules de auditor → afr_ecm (genérico, sem dependência de NC/CAPA).
- `hr_employee_revocation` + `dms_file_revocation_cron` + `cron_ti_revocation` → afr_ecm (área TI, não SGQ/Op/Reg).
- `dms_file_*` que vão pro afr_sgq usam `_inherit = 'dms.file'` — o model base permanece em afr_ecm; afr_sgq estende via dependency.
- `_name` dos models (`afr.ecm.nc` etc.) **não é renomeado** — evita quebrar tabelas/dados. O prefixo `afr.ecm.*` permanece mesmo no afr_sgq (é só naming, não acoplamento).

---

## Cross-references e xmlid migration

| Item | Antes | Depois |
|---|---|---|
| 3 res.groups de área | `afr_ecm.group_ecm_area_sgq/operacao/regulatorio` | `afr_sgq.group_ecm_area_sgq/operacao/regulatorio` |
| Categoria de grupos | `afr_ecm.module_category_ecm_areas` | **inalterada** — afr_sgq referencia `afr_ecm.module_category_ecm_areas` |
| Grupos base | `afr_ecm.group_ecm_user/manager/admin` | **inalterados** — afr_sgq referencia via dependency |
| Record rules SGQ | refs internas a `group_ecm_area_*` | atualizadas para `afr_sgq.group_ecm_area_*` |
| ACLs | rows em `afr_ecm/security/ir.model.access.csv` | movidas para `afr_sgq/security/ir.model.access.csv` |
| Menus parent | `parent="afr_ecm.menu_ecm_root"` | **mantido** — afr_sgq referencia via dependency |
| `menu_ecm_operacao_root` | criado em `menus_recall.xml` (afr_ecm) | criado em `menus_recall.xml` (afr_sgq) |

**`security_ecm_areas.xml` split:**
- afr_ecm mantém: `module_category_ecm_areas` + 9 grupos (`comercial`, `rh`, `rh_funcionario`, `financeiro`, `ti`, `eng`, `sst`, `diretoria`, `auditor`).
- afr_sgq novo `security_sgq_groups.xml`: 3 grupos (`sgq`, `operacao`, `regulatorio`), referenciando `<field name="category_id" ref="afr_ecm.module_category_ecm_areas"/>`.

**`dms_access_group_links.xml`:** o `<function model="dms.access.group" name="write">` busca grupos `dms.access.group` por nome (search-by-name) e os vincula aos res.groups. Os `dms.access.group` (ECM_SGQ/Operacao/Regulatorio etc.) são **dados runtime** (criados via MCP/UI, não pertencem a módulo). O arquivo **fica inteiro em afr_ecm** cobrindo os 9 grupos de área restantes. afr_sgq **não traz** esse arquivo — o vínculo dms.access.group↔res.groups para SGQ/Operação/Regulatório é setup runtime (via UI ou MCP, igual à criação dos próprios `dms.access.group`). Best-effort/no-op se o grupo não existe.

---

## Estrutura `afr_sgq`

```
addons/afr_sgq/
├── __init__.py                       from . import models
├── __manifest__.py                   depends=['afr_ecm'], version 16.0.1.0.0
├── CLAUDE.md                         regras de submódulo (espelho do afr_ecm/CLAUDE.md)
├── README.md
├── models/
│   ├── __init__.py                   8 imports
│   ├── nc.py
│   ├── nc_sla_check.py
│   ├── capa.py
│   ├── recall.py
│   ├── dms_file_recall_trigger.py
│   ├── dms_file_cycle_summary.py
│   ├── notivisa.py
│   └── dms_file_license_renewal.py
├── views/
│   ├── nc_views.xml
│   ├── capa_views.xml
│   ├── recall_views.xml
│   ├── notivisa_views.xml
│   ├── menus_nc_capa.xml
│   ├── menus_recall.xml
│   └── menus_notivisa.xml
├── data/
│   ├── sequence_nc_capa.xml
│   ├── sequence_notivisa.xml
│   ├── sequence_recall.xml
│   ├── cron_capa_verification.xml
│   ├── cron_cycle_summary.xml
│   ├── cron_license_renewal.xml
│   ├── cron_nc_sla.xml
│   ├── cron_notivisa_overdue.xml
│   └── cron_recall_overdue.xml
├── security/
│   ├── ir.model.access.csv           rows nc/capa/recall/notivisa
│   ├── security_sgq_groups.xml       3 res.groups
│   ├── record_rules_nc_capa.xml
│   ├── record_rules_recall.xml
│   └── record_rules_notivisa.xml
└── tests/
    ├── __init__.py                   6 imports
    ├── test_nc_capa.py
    ├── test_nc_sla.py
    ├── test_recall.py
    ├── test_notivisa.py
    ├── test_cycle_summary.py
    └── test_license_renewal.py
```

### `__manifest__.py` afr_sgq

```python
{
    'name': 'AFR SGQ — Sistema de Gestão da Qualidade (CME)',
    'version': '16.0.1.0.0',
    'category': 'Document Management/Quality',
    'summary': 'Workflows de qualidade/saúde sobre afr_ecm: NC, CAPA, Recall, '
               'NOTIVISA, renovação de licenças, sumário de ciclos. '
               'Domínio CME / RDC 15 / ISO 13485.',
    'author': 'Engenapp',
    'license': 'LGPL-3',
    'depends': ['afr_ecm'],
    'data': [
        'security/security_sgq_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules_nc_capa.xml',
        'security/record_rules_recall.xml',
        'security/record_rules_notivisa.xml',
        'data/sequence_nc_capa.xml',
        'data/sequence_recall.xml',
        'data/sequence_notivisa.xml',
        'data/cron_capa_verification.xml',
        'data/cron_cycle_summary.xml',
        'data/cron_license_renewal.xml',
        'data/cron_nc_sla.xml',
        'data/cron_notivisa_overdue.xml',
        'data/cron_recall_overdue.xml',
        'views/nc_views.xml',
        'views/capa_views.xml',
        'views/recall_views.xml',
        'views/notivisa_views.xml',
        'views/menus_nc_capa.xml',
        'views/menus_recall.xml',
        'views/menus_notivisa.xml',
    ],
    'installable': True,
    'application': False,
}
```

### afr_ecm pós-split

- `__manifest__.py`: versão `16.0.1.7.0` → **`16.0.2.0.0`** (breaking — features removidas); remove **12 entradas** de `data` (3 record_rules + 3 sequences + 6 crons) + **7 entradas de views** (nc/capa/recall/notivisa + 3 menus_*); remove 3 res.groups de `security_ecm_areas.xml`.
- `models/__init__.py`: remove 8 imports.
- `tests/__init__.py`: remove 6 imports.
- `security/ir.model.access.csv`: remove rows de nc/capa/recall/notivisa.
- `git rm` dos 8 models + 7 views + 9 data + 3 record_rules + 6 tests.

---

## Submódulo git

afr_sgq segue a mesma política do afr_ecm (ver `addons/afr_ecm/CLAUDE.md`):

1. Criar repo `github.com/afonsorcarvalho/afr_sgq` (branch `main`).
2. `addons/afr_sgq/` registrado em `.gitmodules` do monorepo.
3. Commits/pushes **de dentro de `addons/afr_sgq/`**, nunca via path do monorepo.
4. Após push do submódulo, bump do pointer no monorepo.
5. `CLAUDE.md` próprio espelhando as regras.

Ordem de operações git:
1. Criar repo remoto vazio `afr_sgq`.
2. `git init` em `addons/afr_sgq/`, primeiro commit, push para `origin/main`.
3. Adicionar como submódulo no monorepo (`.gitmodules`).
4. Commit no afr_ecm (remoção dos arquivos) → push afr_ecm `origin/main`.
5. Bump pointers afr_ecm + afr_sgq no monorepo → push monorepo.

---

## Verificação

1. **Compile/lint:** `python -m py_compile` em todos os `.py` movidos; `xmllint --noout` em todos os XML.
2. **afr_ecm standalone:** instala numa DB fresca sem `afr_sgq` — sem erro, menus SGQ/Op/Reg ausentes, base ECM (dms, document_type, audit, physical_location, OCR, expiration, audit_scope) funcional.
3. **afr_sgq sobre afr_ecm:** instala `afr_sgq` numa DB que tem `afr_ecm` — sem erro de xmlid não-resolvido.
4. **Smoke test funcional:** na DB fresca com ambos instalados — criar NC → escalar para CAPA → percorrer verificação 30/60/90d; criar Recall; criar NOTIVISA; confirmar 6 crons SGQ ativos + 3 res.groups na categoria "AFR ECM — Áreas".
5. **Regressão afr_ecm:** crons de afr_ecm (audit_scope_expire, ti_revocation, expiration) intactos; grupos de área restantes (9) intactos; record rules de auditor/RH intactas.
6. **Recriar DB teste:** `odoo_ecm_test` recriada fresca, instala `afr_ecm` + `afr_sgq`, re-roda os testes UI das fases F4.3.x.

---

## Fora de escopo (follow-ups)

- Migration scripts para DBs de produção existentes com dados afr_ecm misturados (decisão: DB teste é fresca; produção tratará quando houver).
- Seed XML de taxonomia (doc types SGQ/OP/REG + estrutura de pastas) — continuam dados runtime.
- `afr_ecm_account` (bridge accounting) — não afetado pelo split.
