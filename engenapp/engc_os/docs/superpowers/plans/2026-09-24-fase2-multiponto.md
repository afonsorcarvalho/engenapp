# Fase 2 — Certificado de padrão multiponto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir cadastrar o certificado do padrão como tabela de pontos, e fazer cada linha de medição puxar a contribuição de incerteza do ponto correspondente ao valor calibrado.

**Architecture:** Um campo de valor nominal mais um booleano `is_generic` na linha de incerteza do certificado, com três constraints que impedem ambiguidade. Um seletor puro no modelo do certificado que interpola o erro e toma a incerteza do pior ponto do intervalo, e que **nunca levanta exceção** — devolve um `status`. As cinco contribuições do padrão descem de `engc.calibration.measurement` para `engc.calibration.measurement.lines` como computados `store=True`, e `_compute_statistics` passa a lê-las de lá sem que sua aritmética mude.

**Tech Stack:** Odoo 16.0, Python 3.9, PostgreSQL 12, QWeb. Testes via `odoo.tests.common.TransactionCase`, executados no container `odoo_engenapp-web-qualificacao-1` contra o banco `qualificacao-dev`.

**Spec:** [../specs/2026-09-24-fase2-multiponto-design.md](../specs/2026-09-24-fase2-multiponto-design.md)

## Global Constraints

- **Odoo 16.0, Python 3.9.** Nada de sintaxe 17+.
- **A aritmética de `_compute_statistics` NÃO muda.** Esta fase altera apenas de onde vêm os quatro insumos. Os testes de caracterização que fixam os números têm de continuar dando exatamente os mesmos valores. As correções de GUM são a Fase 3.
- **Nenhum compute `store=True` pode levantar exceção.** Um compute que estoura derruba todo `-u` do módulo, porque o upgrade recomputa os campos de todas as linhas existentes. Validação bloqueante mora em `action_done()` e num `onchange`, nunca no caminho do compute.
- **NÃO renomear `resolutino_instrument`.** O typo é deliberado: `addons/afr_qualificacao/views/qualificacao_subrecords_views.xml:130` referencia esse nome exato e renomear quebra a view do submodule com `ParseError`.
- **Comando de teste** (o entrypoint é obrigatório; `odoo -d` puro falha por falta de `db_host`):
  ```bash
  docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
    --no-http --test-enable -u engc_os --stop-after-init 2>&1 | tail -40
  ```
  Para uma classe só, acrescentar `--test-tags /engc_os:NomeDaClasse`. Shell interativo:
  ```bash
  docker exec -i odoo_engenapp-web-qualificacao-1 /entrypoint.sh odoo shell \
    -d qualificacao-dev --no-http --log-level=warn < script.py
  ```
- **Baseline:** 919 testes dos módulos dependentes (`afr_qualificacao` 757 + `afr_qualificacao_agendamento` 162) com **uma** falha pré-existente conhecida, `afr_qualificacao.tests.test_resource_plan.TestResourcePlan.test_fleet_single_logger_two_temp_standards`, mais os 40 testes do `engc_os`. Ruído conhecido a ignorar: `duplicate key ... afr_qualificacao_os_name_company_uniq`, docutils `ERROR/3 Unexpected indentation`, `Unit testing in workers mode could fail`, `QFont::setPixelSize`.
- **Branch:** `feat/calibracao-fase2-multiponto`, criada de `main-monorepo` em `c45c440`. **Sem worktree** — o container monta `/home/afonso/docker/odoo_engenapp/engenapp` em `/mnt/engenapp`; worktree em outro caminho não é vista pelo Odoo.
- **Git roda SEMPRE de `/home/afonso/docker/odoo_engenapp`.** O diretório `engenapp/` contém um `.git` órfão e obsoleto que **não** é submodule; rodar git de dentro dele responde pelo repo errado e o commit some.
- **Stage cirúrgico:** só caminhos sob `engenapp/engc_os/`. Nunca `git add -A` nem `git add engenapp/`. A árvore contém muito trabalho alheio não commitado, incluindo `engenapp/engc_os/models/hr_employee_public.py` e `engenapp/engc_os/models/__init__.py`.
- **Trailer obrigatório** em todo commit: `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- **Versão do `__manifest__.py`:** sai de `16.0.2.0.0` para `16.0.3.0.0` na Task 6 (a migração precisa disso para rodar).

## Review Focus

1. **Certificado com pontos cujo `coverage_factor` é zero.** O seletor divide por `k` para comparar `u = U/k` no pior caso. Um `k = 0` cadastrado por engano gera `ZeroDivisionError` dentro de um compute `store=True` — exatamente o que não pode acontecer. Coberto na Task 2, Step 1.
2. **Medição cuja unidade não consta de nenhuma linha do certificado.** Hoje isso levanta `ValidationError` via onchange; com o compute total, tem de virar `status='sem_unidade'` sem estourar. Coberto na Task 3, Step 1.
3. **Linha de medição criada por RPC, sem passar por onchange.** Era o defeito que motivou tornar os campos computados; o teste tem de criar via `create()` puro e afirmar que os valores do padrão chegaram. Coberto na Task 3, Step 1.
4. **Dois pontos com o mesmo `u = U/k`** (empate no pior caso). A regra precisa ser determinística, não depender da ordem de iteração do recordset. Coberto na Task 2, Step 1.
5. **`action_done()` numa calibração sem nenhuma linha de medição.** A nova validação percorre linhas; com zero linhas não pode nem estourar nem aprovar em falso. Coberto na Task 5, Step 1.

---

## Estrutura de arquivos

**Modificar:**
- `engenapp/engc_os/models/engc_calibration.py` — o grosso: campos novos, constraints, seletor, compute da linha, `_compute_statistics`, `action_done`
- `engenapp/engc_os/views/calibration_instruments_views.xml` — colunas novas na tabela de linhas do certificado
- `engenapp/engc_os/views/calibration_views.xml` — painel da medição vira identificação do certificado; colunas opcionais nas linhas
- `engenapp/engc_os/__manifest__.py` — versão `16.0.3.0.0`
- `engenapp/engc_os/tests/test_calibration_characterization.py` — uma asserção virada de propósito
- `engenapp/engc_os/tests/test_calibration_certificate.py` — duas asserções movidas para o nível da linha
- `engenapp/engc_os/tests/test_calibration_precision.py` — o guarda de `digits` perde 5 campos e ganha os novos

**Criar:**
- `engenapp/engc_os/tests/test_calibration_multipoint.py` — seleção, constraints, compute total, bloqueio, aceitação
- `engenapp/engc_os/migrations/16.0.3.0.0/post-migrate.py` — backfill defensivo e auditoria de `veff`

---

## Task 1: Campos e constraints na linha de incerteza

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — classe `CalibrationIntrumentUncertaintyLines`
- Modify: `engenapp/engc_os/views/calibration_instruments_views.xml` — tree de `uncertainty_lines`
- Create: `engenapp/engc_os/tests/test_calibration_multipoint.py`
- Modify: `engenapp/engc_os/tests/__init__.py`

**Interfaces:**
- Consumes: `CalibrationCase` de `tests/common.py` (fixture das fases anteriores).
- Produces: em `engc.calibration.instruments.uncertainty.lines` os campos `is_generic` (Boolean, default True), `nominal_value` (Float, digits `Calibration`), `veff_infinito` (Boolean, default True); e três `@api.constrains`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `engenapp/engc_os/tests/test_calibration_multipoint.py`:

```python
from odoo.exceptions import ValidationError

from .common import CalibrationCase


class TestUncertaintyLineConstraints(CalibrationCase):
    """A fixture já cria self.unc_line: uma linha em self.unit_tempo,
    com uncertainty=0.035, coverage_factor=2.0, erro_value=0.01,
    resolution=0.01, veff=2.0. Ela nasce genérica (is_generic=True)."""

    def _ponto(self, valor, **kw):
        vals = {
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False,
            'nominal_value': valor,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'erro_value': -0.002,
            'resolution': 0.01,
        }
        vals.update(kw)
        return self.env['engc.calibration.instruments.uncertainty.lines'].create(vals)

    def test_linha_nasce_generica(self):
        self.assertTrue(self.unc_line.is_generic)
        self.assertTrue(self.unc_line.veff_infinito)

    def test_ponto_em_zero_e_valido(self):
        """O certificado do cronômetro tem ponto em 0,000 s. Float no Odoo
        nunca grava NULL, então is_generic é o que desambigua."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        ponto = self._ponto(60.0)
        self.assertFalse(self.unc_line.is_generic)
        self.assertEqual(self.unc_line.nominal_value, 0.0)
        self.assertEqual(ponto.nominal_value, 60.0)

    def test_nao_mistura_generica_com_ponto(self):
        with self.assertRaises(ValidationError):
            self._ponto(60.0)

    def test_nao_repete_valor_nominal(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        with self.assertRaises(ValidationError):
            self._ponto(60.0)

    def test_nao_aceita_duas_genericas(self):
        with self.assertRaises(ValidationError):
            self._ponto(0.0, is_generic=True)

    def test_unidades_diferentes_nao_conflitam(self):
        outra = self.env['engc.calibration.measurement.unit'].create(
            {'name': 'Celsius', 'simbolo': 'C'})
        linha = self._ponto(0.0, is_generic=True, unit_of_measurement=outra.id)
        self.assertTrue(linha.is_generic)
        self.assertTrue(self.unc_line.is_generic)

    def test_seis_pontos_do_cronometro(self):
        """O caso que motivou a fase inteira: cadastrar a tabela do
        certificado sem que nada reclame."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        for valor in (60.0, 120.0, 480.0, 600.0, 1200.0):
            self._ponto(valor)
        linhas = self.certificate.uncertainty_lines
        self.assertEqual(len(linhas), 6)
        self.assertEqual(
            sorted(linhas.mapped('nominal_value')),
            [0.0, 60.0, 120.0, 480.0, 600.0, 1200.0])
```

Acrescentar em `engenapp/engc_os/tests/__init__.py`:
```python
from . import test_calibration_multipoint
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestUncertaintyLineConstraints 2>&1 | grep -E "Starting Test|FAIL|ERROR|tests.stats"
```
Esperado: falha em todos, porque `is_generic`, `nominal_value` e `veff_infinito` não existem.

- [ ] **Step 3: Acrescentar os campos**

Em `CalibrationIntrumentUncertaintyLines`, junto aos demais campos:

```python
    is_generic = fields.Boolean(
        string="Vale para toda a faixa",
        default=True,
        help="Marcado: a linha vale para qualquer valor medido — é o cadastro "
             "antigo, um conjunto de valores por unidade. Desmarcado: a linha "
             "vale para o ponto nominal indicado.",
    )
    nominal_value = fields.Float(
        string="Valor nominal",
        digits='Calibration',
        help="O ponto calibrado a que esta linha se refere. Só tem efeito "
             "com 'Vale para toda a faixa' desmarcado.",
    )
    veff_infinito = fields.Boolean(
        string="Veff infinito",
        default=True,
        help="Marcado: graus de liberdade efetivos infinitos, o caso usual "
             "em certificado de padrão. Desmarcado: usar o valor de Veff.",
    )
```

Remover o bloco `_sql_constraints` comentado que está no fim da classe — está morto e tem typo (`unit_of_measuremen`).

- [ ] **Step 4: Acrescentar as três constraints**

Ainda em `CalibrationIntrumentUncertaintyLines`. O import de `float_compare` vai no topo do arquivo, junto dos demais imports do Odoo: `from odoo.tools import float_compare`.

```python
    @api.constrains('is_generic', 'nominal_value', 'certificate',
                    'unit_of_measurement')
    def _check_pontos_coerentes(self):
        """Impede os três arranjos ambíguos dentro de um mesmo
        (certificado, unidade).

        A terceira checagem é a que fecha o bug que originou esta fase: sem
        ela, duas linhas na mesma unidade fazem _search_statistics devolver
        um recordset e qualquer leitura de campo levanta Expected singleton.
        """
        casas = self.env['decimal.precision'].precision_get('Calibration')
        for rec in self:
            irmas = rec.certificate.uncertainty_lines.filtered(
                lambda r: r.unit_of_measurement == rec.unit_of_measurement
                and r.id != rec.id
            )
            genericas = irmas.filtered('is_generic')
            if rec.is_generic:
                if genericas:
                    raise ValidationError(_(
                        "Já existe uma linha 'vale para toda a faixa' para a "
                        "unidade %s neste certificado."
                    ) % rec.unit_of_measurement.display_name)
                if irmas - genericas:
                    raise ValidationError(_(
                        "Não é possível misturar uma linha 'vale para toda a "
                        "faixa' com linhas de ponto na unidade %s. Ou a "
                        "unidade tem um conjunto único de valores, ou tem "
                        "pontos nominais."
                    ) % rec.unit_of_measurement.display_name)
            else:
                if genericas:
                    raise ValidationError(_(
                        "A unidade %s já tem uma linha 'vale para toda a "
                        "faixa' neste certificado. Desmarque-a antes de "
                        "cadastrar pontos."
                    ) % rec.unit_of_measurement.display_name)
                repetido = (irmas - genericas).filtered(
                    lambda r: float_compare(
                        r.nominal_value, rec.nominal_value,
                        precision_digits=casas) == 0
                )
                if repetido:
                    raise ValidationError(_(
                        "Já existe uma linha para o valor nominal %s na "
                        "unidade %s deste certificado."
                    ) % (rec.nominal_value,
                         rec.unit_of_measurement.display_name))
```

- [ ] **Step 5: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 7 testes PASS.

- [ ] **Step 6: Expor os campos na view do certificado**

Em `engenapp/engc_os/views/calibration_instruments_views.xml`, na `<tree>` de `uncertainty_lines`, acrescentar as colunas antes de `erro_value` e ajustar a ordenação:

```xml
                          <tree editable="bottom" multi_edit="1"
                                default_order="unit_of_measurement,nominal_value">
                            <field name="unit_of_measurement" width="3" />
                            <field name="is_generic" width="1"/>
                            <field name="nominal_value" width="1"
                                   attrs="{'readonly': [('is_generic','=',True)]}"/>
                            <field name="erro_value" width="1"/>
                            <field name="uncertainty" width="1"/>
                            <field name="coverage_factor" width="1"/>
                            <field name="veff_infinito" width="1"/>
                            <field name="veff" width="1"
                                   attrs="{'readonly': [('veff_infinito','=',True)]}"/>
                            <field name="resolution" width="1" />
                          </tree>
```

Fazer o mesmo no `<form>` logo abaixo (acrescentar `is_generic`, `nominal_value`, `veff_infinito` ao `<group>`).

- [ ] **Step 7: Rodar a suíte inteira**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "FAIL:|failures,|tests.stats"
```
Esperado: só a falha pré-existente do baseline. Os 40 testes anteriores continuam verdes.

- [ ] **Step 8: Verificar o backfill no banco**

A spec afirma que `_init_column` preenche coluna booleana nova quando o default é truthy. Confirmar no dado real:

```bash
docker exec odoo_engenapp-db-qualificacao-1 psql -U odoo -d qualificacao-dev -tAc \
 "SELECT is_generic, veff_infinito, count(*) FROM engc_calibration_instruments_uncertainty_lines GROUP BY 1,2;"
```
Esperado: todas as linhas com `t|t`. Se vier `NULL` ou `f`, **parar e reportar** — a Task 6 depende disso.

- [ ] **Step 9: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/views/calibration_instruments_views.xml engenapp/engc_os/tests/
mensagem: feat(engc_os): allow standard certificates to record calibrated points

Uncertainty lines gain a nominal value plus an is_generic flag. The flag
exists because a Float never stores NULL in Odoo, and the time standard's
certificate has a legitimate point at 0.000 s, so a zero nominal value
cannot mean "not filled in".

Three constraints forbid the ambiguous arrangements within one certificate
and unit: mixing a generic line with points, repeating a nominal value, and
holding two generic lines. The last one closes the defect this phase exists
for — two lines in one unit are what make the standard's values resolve to
a recordset and raise Expected singleton on any field read.

is_generic defaults to True, so the eight existing uncertainty lines keep
behaving exactly as before with no data migration.
```

---

## Task 2: O seletor de ponto

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — classe `CalibrationInstrumentCertificates`
- Modify: `engenapp/engc_os/tests/test_calibration_multipoint.py`

**Interfaces:**
- Consumes: `is_generic`, `nominal_value`, `veff_infinito` da Task 1.
- Produces, em `engc.calibration.instruments.certificates`:
  - `_select_uncertainty_at(unit, value)` → dict com as chaves `status`, `message`, `erro_value`, `uncertainty`, `coverage_factor`, `veff`, `veff_infinito`, `resolution`, `source_line_id`. **Nunca levanta.**
  - `_uncertainty_from_line(linha)` → o mesmo dict, a partir de uma linha
  - `_incerteza_padrao(linha)` → `float`, `u = U/k`, devolve `0.0` se `k` for zero
  - `_pior_ponto(a, b)` → a linha de maior `u`, empate pelo menor `id`
  - Valores possíveis de `status`: `'ok'`, `'sem_certificado'`, `'sem_unidade'`, `'fora_faixa'`

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `test_calibration_multipoint.py`:

```python
class TestSelectUncertaintyAt(CalibrationCase):

    def _ponto(self, valor, **kw):
        vals = {
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False,
            'nominal_value': valor,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'erro_value': -0.002,
            'resolution': 0.01,
        }
        vals.update(kw)
        return self.env['engc.calibration.instruments.uncertainty.lines'].create(vals)

    def _virar_multiponto(self):
        """Converte a linha genérica da fixture em 0 s e acrescenta 60 e 120."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        self.unc_line.erro_value = 0.000
        p60 = self._ponto(60.0, erro_value=-0.002, uncertainty=0.035)
        p120 = self._ponto(120.0, erro_value=-0.006, uncertainty=0.045)
        return p60, p120

    def test_linha_generica_serve_qualquer_valor(self):
        """100% do acervo atual cai aqui — não pode regredir."""
        for valor in (0.0, 60.0, 99999.0):
            r = self.certificate._select_uncertainty_at(self.unit_tempo, valor)
            self.assertEqual(r['status'], 'ok')
            self.assertAlmostEqual(r['uncertainty'], 0.035, places=6)
            self.assertEqual(r['source_line_id'], self.unc_line.id)

    def test_ponto_exato(self):
        p60, _ = self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 60.0)
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(r['source_line_id'], p60.id)
        self.assertAlmostEqual(r['erro_value'], -0.002, places=6)

    def test_entre_dois_pontos_interpola_erro(self):
        """90 s fica no meio de 60 e 120: erro = -0,002 + 0,5*(-0,006+0,002)"""
        self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertEqual(r['status'], 'ok')
        self.assertAlmostEqual(r['erro_value'], -0.004, places=6)

    def test_entre_dois_pontos_incerteza_pelo_pior(self):
        """U vem do ponto de maior u=U/k, não interpolada."""
        _, p120 = self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertAlmostEqual(r['uncertainty'], 0.045, places=6)
        self.assertEqual(r['source_line_id'], p120.id)

    def test_pior_ponto_usa_u_e_nao_U_nu(self):
        """U=0,050 com k=2,5 dá u=0,020, igual a U=0,040 com k=2,0.
        Escolher pelo U nu pegaria o errado."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.unc_line.uncertainty = 0.040
        self.unc_line.coverage_factor = 2.0
        self._ponto(120.0, uncertainty=0.050, coverage_factor=2.5)
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        # empate em u: resolve pelo menor id, que é a linha da fixture
        self.assertEqual(r['source_line_id'], self.unc_line.id)
        self.assertAlmostEqual(r['coverage_factor'], 2.0, places=6)

    def test_fora_da_faixa_devolve_status_sem_levantar(self):
        self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 2000.0)
        self.assertEqual(r['status'], 'fora_faixa')
        self.assertIn('2000', r['message'])
        self.assertEqual(r['uncertainty'], 0.0)

    def test_abaixo_da_faixa_tambem(self):
        self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, -5.0)
        self.assertEqual(r['status'], 'fora_faixa')

    def test_unidade_ausente_devolve_status_sem_levantar(self):
        outra = self.env['engc.calibration.measurement.unit'].create(
            {'name': 'Bar', 'simbolo': 'bar'})
        r = self.certificate._select_uncertainty_at(outra, 1.0)
        self.assertEqual(r['status'], 'sem_unidade')

    def test_k_zero_nao_estoura(self):
        """Review Focus 1: k=0 cadastrado por engano dividiria por zero
        dentro de um compute store=True."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self._ponto(120.0, coverage_factor=0.0)
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertEqual(r['status'], 'ok')
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestSelectUncertaintyAt 2>&1 | grep -E "Starting Test|FAIL|ERROR|tests.stats"
```
Esperado: `AttributeError` — `_select_uncertainty_at` não existe.

- [ ] **Step 3: Implementar os auxiliares**

Em `CalibrationInstrumentCertificates`:

```python
    def _uncertainty_from_line(self, linha):
        """Monta o dict de contribuições a partir de uma linha do certificado."""
        return {
            'status': 'ok',
            'message': '',
            'erro_value': linha.erro_value,
            'uncertainty': linha.uncertainty,
            'coverage_factor': linha.coverage_factor,
            'veff': linha.veff,
            'veff_infinito': linha.veff_infinito,
            'resolution': linha.resolution,
            'source_line_id': linha.id,
        }

    def _incerteza_padrao(self, linha):
        """u = U / k.

        Devolve 0.0 quando k é zero: cadastro incompleto não pode derrubar
        um compute store=True, e um k ausente torna a linha incomparável,
        não infinita.
        """
        if not linha.coverage_factor:
            return 0.0
        return linha.uncertainty / linha.coverage_factor

    def _pior_ponto(self, a, b):
        """O ponto de maior incerteza padrão entre dois.

        Empate resolve pelo menor id, para o resultado não depender da
        ordem de iteração do recordset (Review Focus 4).
        """
        casas = self.env['decimal.precision'].precision_get('Calibration')
        ua = self._incerteza_padrao(a)
        ub = self._incerteza_padrao(b)
        comparacao = float_compare(ua, ub, precision_digits=casas)
        if comparacao > 0:
            return a
        if comparacao < 0:
            return b
        return a if a.id <= b.id else b
```

- [ ] **Step 4: Implementar o seletor**

Ainda em `CalibrationInstrumentCertificates`:

```python
    def _select_uncertainty_at(self, unit, value):
        """Contribuições do padrão na grandeza `unit`, no ponto `value`.

        NUNCA levanta exceção — devolve sempre um dict com 'status'. Um
        compute store=True chama isto, e um compute que estoura derruba
        todo `-u` do módulo sobre dado histórico já gravado.
        """
        self.ensure_one()
        vazio = {
            'status': 'sem_unidade',
            'message': '',
            'erro_value': 0.0,
            'uncertainty': 0.0,
            'coverage_factor': 0.0,
            'veff': 0.0,
            'veff_infinito': False,
            'resolution': 0.0,
            'source_line_id': False,
        }
        if not unit:
            return dict(vazio, message=_("Unidade de medida não informada."))

        linhas = self.uncertainty_lines.filtered(
            lambda r: r.unit_of_measurement == unit)
        if not linhas:
            return dict(vazio, message=_(
                "O certificado %(cert)s não tem linha de incerteza para a "
                "unidade %(unidade)s.",
                cert=self.certificate_number or '',
                unidade=unit.display_name))

        genericas = linhas.filtered('is_generic')
        if genericas:
            return self._uncertainty_from_line(genericas[0])

        casas = self.env['decimal.precision'].precision_get('Calibration')
        pontos = linhas.sorted(key=lambda r: r.nominal_value)
        minimo = pontos[0].nominal_value
        maximo = pontos[-1].nominal_value

        if (float_compare(value, minimo, precision_digits=casas) < 0
                or float_compare(value, maximo, precision_digits=casas) > 0):
            return dict(vazio, status='fora_faixa', message=_(
                "Valor %(valor)s fora da faixa calibrada do certificado "
                "%(cert)s (%(minimo)s a %(maximo)s).",
                valor=value, cert=self.certificate_number or '',
                minimo=minimo, maximo=maximo))

        exatos = pontos.filtered(
            lambda r: float_compare(
                r.nominal_value, value, precision_digits=casas) == 0)
        if exatos:
            return self._uncertainty_from_line(exatos[0])

        inferior = pontos.filtered(
            lambda r: float_compare(
                r.nominal_value, value, precision_digits=casas) < 0)[-1]
        superior = pontos.filtered(
            lambda r: float_compare(
                r.nominal_value, value, precision_digits=casas) > 0)[0]

        resultado = self._uncertainty_from_line(
            self._pior_ponto(inferior, superior))

        intervalo = superior.nominal_value - inferior.nominal_value
        fracao = (value - inferior.nominal_value) / intervalo
        resultado['erro_value'] = (
            inferior.erro_value
            + fracao * (superior.erro_value - inferior.erro_value))
        return resultado
```

- [ ] **Step 5: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 9 testes PASS.

- [ ] **Step 6: Rodar a suíte inteira**

Esperado: só a falha pré-existente.

- [ ] **Step 7: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/tests/test_calibration_multipoint.py
mensagem: feat(engc_os): select standard uncertainty at the calibrated point

_select_uncertainty_at interpolates the error linearly between the two
bracketing points and takes uncertainty from the worse of them, measured by
u = U/k rather than by U alone — two points with different coverage factors
are not comparable by U. Coverage factor, veff and resolution all come from
that same point, so the set stays coherent with a point that exists on the
certificate.

It never raises. A stored compute calls it, and a compute that throws breaks
every future module upgrade over historical data, so failures come back as a
status the caller records instead.

A generic line short-circuits everything and serves any value, which is what
the entire existing catalogue does today.
```

---

## Task 3: Contribuições do padrão na linha de medição

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — classe `CalibrationMeasurementLines`, início na linha 473
- Modify: `engenapp/engc_os/tests/test_calibration_multipoint.py`

**Interfaces:**
- Consumes: `_select_uncertainty_at(unit, value)` da Task 2; `get_certificate_valid()` (já existe, linhas 184–192).
- Produces, em `engc.calibration.measurement.lines`, nove campos computados `store=True`: `standard_uncertainty`, `standard_erro`, `standard_resolution`, `standard_coverage_factor`, `standard_veff`, `standard_veff_infinito`, `standard_line_id`, `standard_status`, `standard_message`; e o método `_compute_standard_contribution`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `test_calibration_multipoint.py`:

```python
class TestStandardContributionOnLine(CalibrationCase):

    def _calibracao_com_medicao(self):
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id,
            'title': 'Tempo',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        return cal, medicao

    def test_valores_chegam_sem_onchange(self):
        """Review Focus 3: criação por RPC não dispara onchange. Antes desta
        fase os valores do padrão ficavam 0,0 em silêncio."""
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 60.0, 60.053, 60.055, 60.054)
        self.assertEqual(linha.standard_status, 'ok')
        self.assertAlmostEqual(linha.standard_uncertainty, 0.035, places=6)
        self.assertAlmostEqual(linha.standard_resolution, 0.01, places=6)
        self.assertEqual(linha.standard_line_id, self.unc_line)

    def test_cada_linha_pega_o_proprio_ponto(self):
        """O ponto desta fase: duas linhas, dois pontos, dois conjuntos."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.unc_line.erro_value = -0.002
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False,
            'nominal_value': 1200.0,
            'erro_value': -0.009,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'resolution': 0.01,
        })
        _, medicao = self._calibracao_com_medicao()
        curta = self.make_line(medicao, 60.0, 60.053, 60.055, 60.054)
        longa = self.make_line(medicao, 1200.0, 1200.043, 1200.046, 1200.044)
        self.assertAlmostEqual(curta.standard_erro, -0.002, places=6)
        self.assertAlmostEqual(longa.standard_erro, -0.009, places=6)

    def test_recalcula_ao_mudar_o_valor_real(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False, 'nominal_value': 120.0,
            'erro_value': -0.006, 'uncertainty': 0.045,
            'coverage_factor': 2.0, 'resolution': 0.01,
        })
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        self.assertAlmostEqual(linha.standard_uncertainty, 0.035, places=6)
        linha.true_quantity_value = 120.0
        self.assertAlmostEqual(linha.standard_uncertainty, 0.045, places=6)

    def test_sem_instrumento_nao_estoura(self):
        """get_certificate_valid() faz ensure_one(); com instrument_id vazio
        isso levantaria dentro de um compute store=True."""
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Sem padrão',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        medicao.instrument_id = False
        self.assertEqual(linha.standard_status, 'sem_certificado')
        self.assertEqual(linha.standard_uncertainty, 0.0)

    def test_certificado_vencido_nao_estoura(self):
        """O teste que protege todo -u futuro: o compute tem de ser total.

        O certificado vence ANTES de a linha existir, de propósito. Os campos
        standard_* são compute store=True e `validate_calibration` NÃO está no
        @api.depends — nem deve estar: pela decisão D5 da spec, editar o
        certificado amanhã não pode mudar retroativamente uma calibração já
        emitida. Vencer o certificado depois de criar a linha só deixaria o
        valor gravado intacto, e o teste não provaria nada.
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta
        self.certificate.validate_calibration = date.today() - relativedelta(days=1)
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        self.assertEqual(linha.standard_status, 'sem_certificado')
        self.assertEqual(linha.standard_uncertainty, 0.0)

    def test_unidade_ausente_no_certificado(self):
        """Review Focus 2."""
        outra = self.env['engc.calibration.measurement.unit'].create(
            {'name': 'Bar', 'simbolo': 'bar'})
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Pressão',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': outra.id,
        })
        linha = self.make_line(medicao, 1.0, 1.0, 1.0, 1.0)
        self.assertEqual(linha.standard_status, 'sem_unidade')

    def test_fora_da_faixa_marca_status(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False, 'nominal_value': 120.0,
            'erro_value': -0.006, 'uncertainty': 0.045,
            'coverage_factor': 2.0, 'resolution': 0.01,
        })
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 2000.0, 2000.0, 2000.0, 2000.0)
        self.assertEqual(linha.standard_status, 'fora_faixa')
        self.assertIn('2000', linha.standard_message)
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestStandardContributionOnLine 2>&1 | grep -E "Starting Test|FAIL|ERROR|tests.stats"
```
Esperado: `Invalid field` / `AttributeError` nos campos `standard_*`.

- [ ] **Step 3: Declarar os campos**

Em `CalibrationMeasurementLines` (a classe começa na linha 473), logo depois dos campos existentes e **antes** de `_compute_statistics` (linha 493). Seguir o precedente de `Selection` do arquivo, que declara a lista como constante de classe em maiúsculas antes do campo:

```python
    STANDARD_STATUS = [
        ('ok', 'OK'),
        ('sem_certificado', 'Sem certificado válido'),
        ('sem_unidade', 'Unidade não consta do certificado'),
        ('fora_faixa', 'Fora da faixa calibrada'),
    ]

    standard_status = fields.Selection(
        string="Situação do padrão", selection=STANDARD_STATUS,
        compute="_compute_standard_contribution", store=True)
    standard_message = fields.Char(
        string="Detalhe do padrão",
        compute="_compute_standard_contribution", store=True)
    standard_line_id = fields.Many2one(
        string="Ponto do certificado",
        comodel_name='engc.calibration.instruments.uncertainty.lines',
        ondelete='set null',
        compute="_compute_standard_contribution", store=True,
        help="Qual linha do certificado do padrão sustentou esta medição.")
    standard_uncertainty = fields.Float(
        string="Incerteza do padrão", digits='Calibration',
        compute="_compute_standard_contribution", store=True)
    standard_erro = fields.Float(
        string="Erro do padrão", digits='Calibration',
        compute="_compute_standard_contribution", store=True)
    standard_resolution = fields.Float(
        string="Resolução do padrão", digits='Calibration',
        compute="_compute_standard_contribution", store=True)
    standard_coverage_factor = fields.Float(
        string="Fator K do padrão",
        compute="_compute_standard_contribution", store=True)
    standard_veff = fields.Float(
        string="Veff do padrão",
        compute="_compute_standard_contribution", store=True)
    standard_veff_infinito = fields.Boolean(
        string="Veff do padrão infinito",
        compute="_compute_standard_contribution", store=True)
```

- [ ] **Step 4: Implementar o compute**

Ainda em `CalibrationMeasurementLines`, imediatamente antes de `_compute_statistics`:

```python
    @api.depends('true_quantity_value',
                 'measurement_id.instrument_id',
                 'measurement_id.unit_of_measurement')
    def _compute_standard_contribution(self):
        """Resolve as contribuições do padrão no ponto desta linha.

        NUNCA levanta. Este compute é store=True, e um compute que estoura
        derruba todo `-u` do módulo: o upgrade recomputa os campos de todas
        as linhas já gravadas, e basta uma com certificado vencido ou ponto
        fora de faixa para impedir qualquer atualização futura.

        O bloqueio do técnico mora no onchange e em action_done().
        """
        sem_padrao = {
            'status': 'sem_certificado',
            'message': _("Nenhum certificado válido para o padrão desta medição."),
            'erro_value': 0.0, 'uncertainty': 0.0, 'coverage_factor': 0.0,
            'veff': 0.0, 'veff_infinito': False, 'resolution': 0.0,
            'source_line_id': False,
        }
        for rec in self:
            padrao = rec.measurement_id.instrument_id
            certificado = padrao.get_certificate_valid() if padrao else padrao
            if not certificado:
                dados = sem_padrao
            else:
                dados = certificado._select_uncertainty_at(
                    rec.measurement_id.unit_of_measurement,
                    rec.true_quantity_value,
                )
            rec.standard_status = dados['status']
            rec.standard_message = dados['message']
            rec.standard_line_id = dados['source_line_id']
            rec.standard_uncertainty = dados['uncertainty']
            rec.standard_erro = dados['erro_value']
            rec.standard_resolution = dados['resolution']
            rec.standard_coverage_factor = dados['coverage_factor']
            rec.standard_veff = dados['veff']
            rec.standard_veff_infinito = dados['veff_infinito']
```

O `if padrao else padrao` devolve o recordset vazio sem chamar `get_certificate_valid()`, que faz `ensure_one()` e levantaria com instrumento vazio.

- [ ] **Step 5: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 7 testes PASS.

- [ ] **Step 6: Rodar a suíte inteira**

Esperado: só a falha pré-existente. Os testes de caracterização continuam verdes — nesta task `_compute_statistics` ainda não foi tocado.

- [ ] **Step 7: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/tests/test_calibration_multipoint.py
mensagem: feat(engc_os): resolve the standard's contribution per measurement line

Each line now carries the standard's uncertainty, error, resolution,
coverage factor and veff at its own true_quantity_value, plus the
certificate line that supplied them and a status. They live on the line
because the block holds one scalar for the whole table, which is why a
multipoint certificate had nowhere to put its numbers.

Being computed rather than an onchange snapshot also closes the silent
failure where a line created over RPC kept 0.0 for every standard
contribution and produced an optimistic uncertainty with no error.

The compute is total: it never raises, because a stored compute that throws
breaks every future module upgrade over historical data.
```

---

## Task 4: `_compute_statistics` lê da linha; os 5 campos antigos saem

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — remover linhas 389–413 (os 5 campos); reescrever as leituras em `_compute_statistics` (linhas 496–502)
- Modify: `engenapp/engc_os/views/calibration_views.xml` — remover as linhas 189, 190, 194, 195, 196; acrescentar colunas na tree de `measurement_lines` (linhas 204–217)
- Modify: `engenapp/engc_os/tests/test_calibration_characterization.py` — `test_padrao_preenchido_pelo_onchange`, linhas 17–22
- Modify: `engenapp/engc_os/tests/test_calibration_certificate.py` — linhas 101 e 115
- Modify: `engenapp/engc_os/tests/test_calibration_precision.py` — linhas 76–88

**Interfaces:**
- Consumes: os nove campos `standard_*` da Task 3.
- Produces: `engc.calibration.measurement` deixa de ter `uncertainty_instrument`, `erro_value_instrument`, `coverage_factor_instrument`, `resolution_instrument`, `veff_instrument`.

> **Verificado antes de remover:** grep no monorepo inteiro (`engenapp/` + `addons/`, incluindo submodules) confirma que os 5 campos só aparecem em `engc_calibration.py`, em `calibration_views.xml` e nos testes deste módulo. O template do certificado não os usa. `afr_qualificacao` expõe `measurement_point_ids` como `related` de `measurement_lines` — ou seja, é o **mesmo** `CalibrationMeasurementLines` — mas exibe apenas `true_quantity_value`, as três leituras, a média, `erro_value`, `uncertainty`, `coverage_factor`, `veff` e `resolutino_instrument`. Nenhum dos 5. Remover é seguro; **acrescentar** campos à linha também.

- [ ] **Step 1: Virar as asserções dos testes existentes**

Em `test_calibration_characterization.py`, o teste `test_padrao_preenchido_pelo_onchange` (linhas 17–22) fixa comportamento que **esta fase muda de propósito**. Substituir o corpo inteiro por:

```python
    def test_padrao_resolvido_na_linha(self):
        """VIRADO NA FASE 2, de propósito.

        Antes: os valores do padrão moravam em engc.calibration.measurement
        e só eram preenchidos pelo onchange da unidade. Agora moram em cada
        linha, resolvidos no ponto dela, por compute.

        A aritmética de _compute_statistics NÃO mudou — os outros testes
        desta classe continuam afirmando exatamente os mesmos números.
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertEqual(line.standard_status, 'ok')
        self.assertAlmostEqual(line.standard_uncertainty, 0.035, places=6)
        self.assertAlmostEqual(line.standard_coverage_factor, 2.0, places=6)
        self.assertAlmostEqual(line.standard_erro, 0.01, places=6)
        self.assertAlmostEqual(line.standard_resolution, 0.01, places=6)
```

Em `test_calibration_certificate.py`, trocar as duas asserções:
- linha 101: `self.assertEqual(measurement.resolution_instrument, 0.01)` → precisa de uma linha para observar. Substituir por:
```python
        linha = self.make_line(measurement, 60.0, 60.0, 60.0, 60.0)
        self.assertAlmostEqual(linha.standard_resolution, 0.01, places=6)
```
- linha 115: idem.

Em `test_calibration_precision.py`, no `test_campos_dimensionais_expoem_digits_calibration` (linhas 76–88), remover o bloco que faz `Meas.fields_get([...])` sobre os 5 campos e pôr no lugar o equivalente na linha:

```python
        Lines = self.env['engc.calibration.measurement.lines']
        fg_s = Lines.fields_get([
            'standard_uncertainty', 'standard_erro', 'standard_resolution',
            'standard_coverage_factor', 'standard_veff',
        ])
        self.assertEqual(tuple(fg_s['standard_uncertainty']['digits']), (16, 6))
        self.assertEqual(tuple(fg_s['standard_erro']['digits']), (16, 6))
        self.assertEqual(tuple(fg_s['standard_resolution']['digits']), (16, 6))
        self.assertFalse(fg_s['standard_coverage_factor'].get('digits'))
        self.assertFalse(fg_s['standard_veff'].get('digits'))
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestCalibrationCharacterization,/engc_os:TestCalibrationPrecision 2>&1 | grep -E "Starting Test|FAIL|ERROR|tests.stats"
```
Esperado: falham porque os campos `standard_*` ainda não têm `digits` conferido e o teste virado ainda referencia o comportamento novo que falta plugar em `_compute_statistics`.

- [ ] **Step 3: Trocar as leituras em `_compute_statistics`**

Nas linhas 496–502, substituir:

```python
            uncertainty_instrument = rec.measurement_id.uncertainty_instrument
            k_instrument = 2.0
            if rec.measurement_id.coverage_factor_instrument != 0: 
                k_instrument = rec.measurement_id.coverage_factor_instrument
        
            erro_instrument = rec.measurement_id.erro_value_instrument
            resolution_instrument= rec.measurement_id.resolution_instrument
```

por:

```python
            # Fase 2: os valores do padrão passaram a ser resolvidos por
            # linha, no ponto dela. A ARITMÉTICA ABAIXO NÃO MUDOU — só a
            # origem destes quatro números.
            uncertainty_instrument = rec.standard_uncertainty
            k_instrument = 2.0
            if rec.standard_coverage_factor != 0:
                k_instrument = rec.standard_coverage_factor

            erro_instrument = rec.standard_erro
            resolution_instrument = rec.standard_resolution
```

Acrescentar os quatro campos ao `@api.depends` de `_compute_statistics` (linha 493), trocando `'measurement_id.instrument_id','measurement_id.unit_of_measurement'` por `'standard_uncertainty','standard_coverage_factor','standard_erro','standard_resolution'`.

**Não tocar em mais nada dentro do método.** As expressões de `combined_uncertainty`, `veff` e `record.uncertainty` ficam byte a byte como estão.

- [ ] **Step 4: Remover os 5 campos**

Apagar as linhas 389–413 de `CalibrationMeasurement` (as cinco declarações `*_instrument` com seus `readonly=True` e `digits`).

Remover também, na mesma classe, os três métodos que existiam só para alimentar esses campos:

- `onchange_unit_of_measurement` (linhas 446–458) — seu corpo inteiro eram as cinco atribuições
- `_search_statistics` (linhas 425–439) — chamado só pelo onchange acima
- `_search_certificates_valid` (linhas 415–423) — chamado só por `_search_statistics`

O trabalho dos três passou para `_select_uncertainty_at` mais o compute da Task 3. O `ValidationError` de "calibração vencida" que `_search_certificates_valid` levantava vira `standard_status='sem_certificado'`, avisado pelo onchange da linha e bloqueado em `action_done` (Task 5) — o técnico continua sendo impedido, só que no momento certo e sem poder derrubar um `-u`.

**Manter** `onchange_instrument_id` (linhas 442–444): limpar a unidade ao trocar de padrão continua sendo comportamento útil.

**Manter** `_compute_unit_of_measurement_domain`, que também chama `get_certificate_valid()` mas serve ao domínio do campo, não aos valores.

Os dois testes que exercitavam `_search_certificates_valid` indiretamente (`test_search_certificates_valid_ignora_substituido` e `test_search_certificates_valid_ignora_certificado_sem_data`, em `test_calibration_certificate.py`) já foram reescritos no Step 1 desta task para observar `standard_resolution` na linha. Renomeá-los para `test_certificado_substituido_nao_alimenta_a_linha` e `test_certificado_sem_data_nao_alimenta_a_linha`, já que o método que davam nome deixou de existir.

- [ ] **Step 5: Acrescentar a identificação do certificado**

A decisão D4 da spec diz que o painel deixa de mostrar cinco valores e passa a mostrar **qual certificado sustenta a medição** — informação que hoje não aparece em tela nenhuma. Isso exige dois campos novos em `CalibrationMeasurement`, ambos computados e **não** armazenados (são só exibição):

```python
    certificate_id = fields.Many2one(
        string="Certificado do padrão",
        comodel_name='engc.calibration.instruments.certificates',
        compute='_compute_certificate_id',
        help="O certificado válido mais recente do padrão escolhido — o mesmo "
             "que o PDF do certificado de calibração cita.")
    certificate_validate = fields.Date(
        string="Validade do certificado",
        related='certificate_id.validate_calibration', readonly=True)

    @api.depends('instrument_id')
    def _compute_certificate_id(self):
        for rec in self:
            rec.certificate_id = (
                rec.instrument_id.get_certificate_valid()
                if rec.instrument_id else False)
```

O `if rec.instrument_id else False` evita o `ensure_one()` de `get_certificate_valid()` num instrumento vazio — mesmo cuidado da Task 3.

- [ ] **Step 6: Ajustar as views**

Em `engenapp/engc_os/views/calibration_views.xml`, no form da medição, remover as linhas 189, 190, 194, 195 e 196 (os cinco `*_instrument`) e pôr no lugar:

```xml
                <field name="certificate_id" readonly="1"
                       options="{'no_open': True, 'no_create': True}"/>
                <field name="certificate_validate" readonly="1"/>
```

E na tree de `measurement_lines` (linhas 204–217), acrescentar as colunas opcionais depois de `veff`:

```xml
                  <field name="standard_status" optional="show"/>
                  <field name="standard_message" optional="hide"/>
                  <field name="standard_line_id" optional="hide"/>
                  <field name="standard_uncertainty" optional="hide"/>
                  <field name="standard_erro" optional="hide"/>
                  <field name="standard_resolution" optional="hide"/>
                  <field name="standard_coverage_factor" optional="hide"/>
                  <field name="standard_veff" optional="hide"/>
```

- [ ] **Step 7: Rodar a suíte inteira**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "FAIL:|failures,|tests.stats"
```

**Esperado, e é o portão desta task:** só a falha pré-existente. Em especial, `test_incerteza_expandida_valor_atual`, `test_tipo_a_usa_divisor_2_e_nao_raiz_de_n`, `test_media_e_erro` e `test_veff_atual_usa_constante_3` têm de dar **exatamente os mesmos números de antes**. Se algum mudou de valor, a aritmética foi alterada sem querer — reverter e investigar.

- [ ] **Step 8: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/views/calibration_views.xml engenapp/engc_os/tests/
mensagem: refactor(engc_os): read the standard's values from the line, not the block

_compute_statistics now takes its four standard inputs from the line's own
resolved point. The arithmetic is untouched — the four characterization
tests that pin the numbers still produce identical values, which is what
they exist for.

The five *_instrument fields on engc.calibration.measurement are removed.
They held one scalar for a whole table of lines, and were only ever filled
by an onchange. Verified across the monorepo including submodules: nothing
outside this module read them.

One characterization test is deliberately flipped, since the behaviour it
pinned is exactly what this phase changes.
```

---

## Task 5: Bloqueio no lugar certo

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — `action_done` (linhas 128–144) e `CalibrationMeasurementLines`
- Modify: `engenapp/engc_os/tests/test_calibration_multipoint.py`

**Interfaces:**
- Consumes: `standard_status` e `standard_message` da Task 3.
- Produces: `EngcCalibration.action_done()` recusa com linha em status diferente de `ok`; `CalibrationMeasurementLines.onchange_true_quantity_value()` devolve `warning`.

- [ ] **Step 1: Escrever os testes que falham**

```python
class TestBlockingOnDone(CalibrationCase):

    def _cal_com_ponto_unico(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Tempo',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        return cal, medicao

    def test_done_recusa_linha_fora_da_faixa(self):
        cal, medicao = self._cal_com_ponto_unico()
        self.make_line(medicao, 2000.0, 2000.0, 2000.0, 2000.0)
        with self.assertRaises(ValidationError) as ctx:
            cal.action_done()
        self.assertIn('2000', str(ctx.exception))

    def test_done_aceita_tudo_resolvido(self):
        cal, medicao = self._cal_com_ponto_unico()
        self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        cal.action_done()
        self.assertEqual(cal.state, 'done')

    def test_done_sem_nenhuma_linha_nao_estoura(self):
        """Review Focus 5: a validação percorre linhas; com zero linhas não
        pode estourar nem aprovar em falso."""
        cal, _ = self._cal_com_ponto_unico()
        cal.action_done()
        self.assertEqual(cal.state, 'done')

    def test_onchange_avisa_sem_bloquear(self):
        cal, medicao = self._cal_com_ponto_unico()
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        linha.true_quantity_value = 2000.0
        aviso = linha.onchange_true_quantity_value()
        self.assertIn('warning', aviso)
        self.assertIn('2000', aviso['warning']['message'])
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestBlockingOnDone 2>&1 | grep -E "Starting Test|FAIL|ERROR|tests.stats"
```

- [ ] **Step 3: Acrescentar o onchange na linha**

Em `CalibrationMeasurementLines`:

```python
    @api.onchange('true_quantity_value')
    def onchange_true_quantity_value(self):
        """Avisa na hora quando o ponto não resolve. Não bloqueia: quem
        bloqueia é action_done()."""
        self.ensure_one()
        if self.standard_status and self.standard_status != 'ok':
            return {'warning': {
                'title': _("Padrão não resolvido neste ponto"),
                'message': self.standard_message or '',
            }}
```

- [ ] **Step 4: Acrescentar a validação em `action_done`**

Nas linhas 128–144, dentro do `for rec in self:`, **depois** da checagem de `technician_id` e **antes** do `rec.write(...)`:

```python
            pendentes = rec.measurement_ids.measurement_lines.filtered(
                lambda l: l.standard_status != 'ok')
            if pendentes:
                detalhe = "\n".join(
                    "- %s: %s" % (l.true_quantity_value, l.standard_message or l.standard_status)
                    for l in pendentes
                )
                raise ValidationError(_(
                    "Não é possível concluir: %(quantas)s linha(s) de medição "
                    "não resolvem os valores do padrão.\n\n%(detalhe)s",
                    quantas=len(pendentes), detalhe=detalhe))
```

Aproveitar e remover a **checagem duplicada** das linhas 134–135: `date_next_calibration` é validado duas vezes seguidas, com a mesma condição e a mesma mensagem.

- [ ] **Step 5: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 4 testes PASS.

- [ ] **Step 6: Rodar a suíte inteira**

Esperado: só a falha pré-existente.

- [ ] **Step 7: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/tests/test_calibration_multipoint.py
mensagem: feat(engc_os): block completion when a line's standard point is unresolved

action_done refuses a calibration holding any measurement line whose
standard status is not ok, naming the offending values, and an onchange
warns the technician as soon as the value leaves the calibrated range.

Both live outside the compute path on purpose: the compute stays total so a
module upgrade over historical data cannot fail.

Also drops a duplicated date_next_calibration check that validated the same
condition twice with the same message.
```

---

## Task 6: Migração, auditoria de `veff` e bump de versão

**Files:**
- Create: `engenapp/engc_os/migrations/16.0.3.0.0/post-migrate.py`
- Modify: `engenapp/engc_os/__manifest__.py`

**Interfaces:**
- Consumes: `is_generic`, `veff_infinito` da Task 1.
- Produces: nada consumido por tasks posteriores.

- [ ] **Step 1: Bump de versão**

Em `__manifest__.py`, trocar `'version': '16.0.2.0.0',` por `'version': '16.0.3.0.0',`. Sem isso a migração não roda.

- [ ] **Step 2: Escrever a migração**

Criar `engenapp/engc_os/migrations/16.0.3.0.0/post-migrate.py`:

```python
"""Rede de segurança do backfill da Fase 2 e auditoria de Veff.

Sobre o backfill: `is_generic` e `veff_infinito` são booleanos com
`default=True`, e o `_init_column` do Odoo 16 preenche coluna nova a partir
do default — para booleano, o UPDATE só roda quando o default é truthy, que
é o nosso caso (models.py, `_init_column`: `necessary = value` para
`field.type == 'boolean'`). Verificado no fonte do container, não suposto.

Logo, no caminho normal de upgrade este script não encontra nada a fazer.
Ele existe pelo mesmo motivo do script da 16.0.2.0.0: restauração parcial de
backup, ou coluna criada por DDL manual. É idempotente e não apaga nada.

Sobre o Veff: a convenção antiga do campo era "preencha qualquer número
maior que 100 para infinito", que é confusa e já produziu dado errado. Esta
migração converte SÓ o caso inequívoco (> 100) para o booleano novo. Não
converte valores finitos: `veff = 2` é legítimo do ponto de vista do modelo,
e só o certificado em papel sabe se está certo. Esses casos saem num WARNING
para conferência manual.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET is_generic = true
         WHERE is_generic IS NULL
    """)
    genericas = cr.rowcount
    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET veff_infinito = true
         WHERE veff_infinito IS NULL
    """)
    infinitos = cr.rowcount
    if genericas or infinitos:
        _logger.info(
            "engc_os: backfill defensivo — %s linha(s) is_generic, "
            "%s linha(s) veff_infinito.", genericas, infinitos)
    else:
        _logger.info(
            "engc_os: backfill já aplicado pelo _auto_init, nada a fazer.")

    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET veff_infinito = true, veff = 0
         WHERE veff > 100
    """)
    if cr.rowcount:
        _logger.info(
            "engc_os: %s linha(s) com veff > 100 convertidas para "
            "'Veff infinito' — era a convenção antiga do campo.", cr.rowcount)

    cr.execute("""
        SELECT l.id, l.veff, c.certificate_number, i.name
          FROM engc_calibration_instruments_uncertainty_lines l
          JOIN engc_calibration_instruments_certificates c
            ON c.id = l.certificate
          JOIN engc_calibration_instruments i
            ON i.id = c.instrument_id
         WHERE l.veff > 0 AND l.veff <= 100
    """)
    for linha_id, veff, numero, padrao in cr.fetchall():
        _logger.warning(
            "engc_os: linha de incerteza %s (padrão %s, certificado %s) tem "
            "Veff FINITO = %s. Conferir no certificado em papel: se o "
            "certificado declara infinito, marcar 'Veff infinito' na linha. "
            "A Fase 3 vai consumir este valor no Welch-Satterthwaite.",
            linha_id, padrao, numero, veff)
```

- [ ] **Step 3: Rodar o upgrade e ler o log da migração**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http -u engc_os --stop-after-init 2>&1 | grep -iE "engc_os:|migrat"
```
Esperado: a linha "backfill já aplicado pelo `_auto_init`, nada a fazer" — confirmando empiricamente o que a docstring afirma.

- [ ] **Step 4: Provar a idempotência**

Semear uma linha com `is_generic` NULL e `veff = 150` num savepoint, rodar `migrate()` duas vezes e confirmar que a segunda não muda nada:

```bash
cat > /tmp/teste_migracao.py <<'PY'
from odoo.modules.migration import load_script
env = env(user=1)
cr = env.cr
cr.execute("SAVEPOINT t2")
cr.execute("""
    UPDATE engc_calibration_instruments_uncertainty_lines
       SET is_generic = NULL, veff = 150 WHERE id = (
       SELECT MIN(id) FROM engc_calibration_instruments_uncertainty_lines)
""")
mod = load_script(
    '/mnt/engenapp/engc_os/migrations/16.0.3.0.0/post-migrate.py', 'post-migrate')
mod.migrate(cr, '16.0.2.0.0')
cr.execute("""SELECT is_generic, veff_infinito, veff
                FROM engc_calibration_instruments_uncertainty_lines
               WHERE id = (SELECT MIN(id) FROM engc_calibration_instruments_uncertainty_lines)""")
print("apos 1a:", cr.fetchone())
mod.migrate(cr, '16.0.2.0.0')
cr.execute("""SELECT is_generic, veff_infinito, veff
                FROM engc_calibration_instruments_uncertainty_lines
               WHERE id = (SELECT MIN(id) FROM engc_calibration_instruments_uncertainty_lines)""")
print("apos 2a:", cr.fetchone())
cr.execute("ROLLBACK TO SAVEPOINT t2")
print("rollback ok")
PY
docker exec -i odoo_engenapp-web-qualificacao-1 /entrypoint.sh odoo shell \
  -d qualificacao-dev --no-http --log-level=warn < /tmp/teste_migracao.py 2>&1 | grep -E "apos|rollback|WARNING engc_os"
```
Esperado: `apos 1a` e `apos 2a` idênticos — `(True, True, 0.0)`. Colar a saída real no relatório.

- [ ] **Step 5: Rodar a suíte inteira**

Esperado: só a falha pré-existente.

- [ ] **Step 6: Commit**

```
paths: engenapp/engc_os/migrations/ engenapp/engc_os/__manifest__.py
mensagem: chore(engc_os): add phase 2 migration and audit finite Veff values

The backfill is a safety net, not a necessity: Odoo's _init_column fills a
new boolean column from a truthy default, verified in the framework source
rather than assumed, so the normal upgrade path finds nothing to do. The
script covers partial restores and manually created columns, and is
idempotent.

Veff values above 100 are converted to the new explicit flag, since that was
the old convention. Finite values are left alone and logged as warnings: a
Veff of 2 is legitimate to the model and only the paper certificate knows
whether it is right. Phase 3 will consume this field, so the catalogue needs
human eyes before then.
```

---

## Task 7: Aceitação — os 6 pontos do cronômetro

**Files:**
- Modify: `engenapp/engc_os/tests/test_calibration_multipoint.py`

**Interfaces:**
- Consumes: tudo das Tasks 1–5.
- Produces: nada.

- [ ] **Step 1: Escrever o teste de aceitação**

```python
class TestAceitacaoCronometro(CalibrationCase):
    """O caso que motivou a fase: o certificado R0712/2026 do QPS-001,
    com os pontos e erros da tabela do PDF de exemplo."""

    PONTOS = [
        (0.0, 0.000), (60.0, -0.002), (120.0, -0.003),
        (480.0, -0.003), (600.0, -0.002), (1200.0, -0.002),
    ]

    def setUp(self):
        super().setUp()
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = self.PONTOS[0][0]
        self.unc_line.erro_value = self.PONTOS[0][1]
        Linha = self.env['engc.calibration.instruments.uncertainty.lines']
        for nominal, erro in self.PONTOS[1:]:
            Linha.create({
                'certificate': self.certificate.id,
                'unit_of_measurement': self.unit_tempo.id,
                'is_generic': False,
                'nominal_value': nominal,
                'erro_value': erro,
                'uncertainty': 0.035,
                'coverage_factor': 2.0,
                'resolution': 0.01,
                'veff_infinito': True,
            })
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        self.medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Tempo',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        self.cal = cal

    def test_seis_pontos_cadastrados(self):
        self.assertEqual(len(self.certificate.uncertainty_lines), 6)

    def test_sobre_um_ponto_usa_o_erro_dele(self):
        linha = self.make_line(self.medicao, 1200.0, 1200.043, 1200.046, 1200.044)
        self.assertEqual(linha.standard_status, 'ok')
        self.assertAlmostEqual(linha.standard_erro, -0.002, places=6)
        self.assertAlmostEqual(linha.standard_uncertainty, 0.035, places=6)

    def test_entre_dois_pontos_interpola(self):
        """300 s fica entre 120 (-0,003) e 480 (-0,003): erro constante."""
        linha = self.make_line(self.medicao, 300.0, 300.0, 300.0, 300.0)
        self.assertEqual(linha.standard_status, 'ok')
        self.assertAlmostEqual(linha.standard_erro, -0.003, places=6)

    def test_interpolacao_com_erros_diferentes(self):
        """90 s entre 60 (-0,002) e 120 (-0,003): meio do caminho."""
        linha = self.make_line(self.medicao, 90.0, 90.0, 90.0, 90.0)
        self.assertAlmostEqual(linha.standard_erro, -0.0025, places=6)

    def test_fora_da_faixa_bloqueia_a_conclusao(self):
        self.make_line(self.medicao, 2000.0, 2000.0, 2000.0, 2000.0)
        with self.assertRaises(ValidationError):
            self.cal.action_done()

    def test_pontos_diferentes_na_mesma_medicao(self):
        """A prova de que o escalar por bloco virou valor por linha."""
        curta = self.make_line(self.medicao, 60.0, 60.053, 60.055, 60.054)
        longa = self.make_line(self.medicao, 120.0, 120.043, 120.046, 120.044)
        self.assertAlmostEqual(curta.standard_erro, -0.002, places=6)
        self.assertAlmostEqual(longa.standard_erro, -0.003, places=6)
        self.assertNotEqual(curta.standard_line_id, longa.standard_line_id)
```

- [ ] **Step 2: Rodar**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestAceitacaoCronometro 2>&1 | grep -E "Starting Test|FAIL|ERROR|tests.stats"
```
Esperado: 6 testes PASS de primeira — as Tasks 1–5 já implementaram tudo de que este teste precisa. Se algum falhar, é defeito real de integração entre as tasks, não deste teste.

- [ ] **Step 3: Rodar a suíte inteira e conferir contra o baseline**

- [ ] **Step 4: Commit**

```
paths: engenapp/engc_os/tests/test_calibration_multipoint.py
mensagem: test(engc_os): accept the six-point stopwatch certificate end to end

Registers the certificate that motivated the phase and drives measurements
on a point, between two points with equal errors, between two with different
errors, and outside the calibrated range. Two lines in one measurement draw
from two different certificate points, which is the whole reason the
standard's values moved from the block down to the line.
```

---

## Fechamento da Fase 2

- [ ] Rodar a suíte completa e conferir contra o baseline (919 dos módulos dependentes + os do `engc_os`, uma falha pré-existente).
- [ ] Rodar `superpowers:requesting-code-review` sobre a branch inteira.
- [ ] Validar na UI por `agent-browser`: cadastrar os 6 pontos no certificado, criar uma medição com duas linhas em pontos distintos, e conferir que as colunas `standard_*` mostram valores diferentes por linha.
- [ ] Apresentar ao usuário e **parar**. A Fase 3 exige o congelamento antes.
