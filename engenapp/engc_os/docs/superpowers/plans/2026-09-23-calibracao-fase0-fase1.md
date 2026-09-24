# Calibração `engc_os` — Fase 0 + Fase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Destravar a geração do certificado de calibração (P0 confirmado no QPT-014) e passar o módulo a exibir/armazenar as medidas com a precisão decimal real, sem alterar nenhuma fórmula de incerteza.

**Architecture:** Três movimentos. (1) Criar do zero a infraestrutura de testes do `engc_os` — o módulo não tem nenhuma — começando por testes de **caracterização** que fixam o comportamento numérico atual, para que as fases seguintes só mudem números de propósito. (2) Tornar `get_certificate_valid()` determinístico e singleton, modelando o "mesmo certificado em dois idiomas" como **um registro com N arquivos de idioma**, com migração **não destrutiva** (nada é apagado; duplicatas ficam marcadas como substituídas). (3) Introduzir `decimal.precision` dedicado e casas decimais por unidade de medida, trocando os `precision: 2` fixos do QWeb.

**Tech Stack:** Odoo 16.0, Python 3.9, PostgreSQL 12, QWeb. Testes via `odoo.tests.common.TransactionCase`, executados no container `odoo_engenapp-web-qualificacao-1` contra o banco `qualificacao-dev`.

**Spec:** [../../2026-09-23-analise-calibracao-incerteza-precisao.md](../../2026-09-23-analise-calibracao-incerteza-precisao.md)

## Global Constraints

- **Odoo 16.0.** Nada de sintaxe de 17+.
- **NÃO alterar nenhuma fórmula de incerteza neste plano.** `_compute_statistics` fica intocado a não ser pelo `except` nu (Task 4) e pelo `digits` dos campos (Task 5). As correções de GUM (`s/√n`, Welch-Satterthwaite, *k* derivado) são Fase 3 e **exigem** o congelamento da Fase 4 antes — ver "Ordem das fases" abaixo.
- **Comando de teste** (memória `reference_odoo_test_command` — precisa de `/entrypoint.sh` e `--no-http`):
  ```bash
  docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
    --no-http --test-enable -u engc_os --stop-after-init 2>&1 | tail -40
  ```
  Para uma classe só, acrescentar `--test-tags /engc_os:NomeDaClasse`.
- **Baseline de testes:** 919 testes, **1 falha pré-existente conhecida** —
  `afr_qualificacao.tests.test_resource_plan.TestResourcePlan.test_fleet_single_logger_two_temp_standards`.
  Qualquer outra falha é regressão. O erro de log `duplicate key ... afr_qualificacao_os_name_company_uniq` também é ruído pré-existente.
- **Commits:** sempre via subagente especialista (`git-commit-push`, model haiku), nunca `git commit` direto — regra do CLAUDE.md. Commitar a partir de `/home/afonso/docker/odoo_engenapp` (o `engenapp/` é do monorepo, **não** é submodule).
- **Branch:** `feat/calibracao-incerteza-precisao`, criada em cima de `main-monorepo`. **Sem worktree** — o container monta `/home/afonso/docker/odoo_engenapp/engenapp` em `/mnt/engenapp`; uma worktree em outro caminho não seria vista pelo Odoo e os testes rodariam contra o código errado.
- **Stage cirúrgico:** a árvore tem muita coisa não commitada e alheia. Cada commit só pode adicionar caminhos sob `engenapp/engc_os/`. Nunca `git add -A`.
- **`__manifest__.py`:** a versão sai de `'0.1'` para `'16.0.1.0.0'` na Task 3 (necessário para migração rodar) e para `'16.0.2.0.0'` na Task 6.

### Ordem das fases (correção em relação ao relatório)

O relatório lista o congelamento como Fase 4, por último. **Está errado e deve ser lido como 0 → 1 → 2 → congelamento → 3.** Motivo: `uncertainty`, `erro_value` e `veff` são `compute` com `store=True`; no primeiro `-u` depois de corrigir `s/2 → s/√n`, todo o histórico é recalculado e certificados já emitidos são reescritos em silêncio. Este plano cobre só 0 e 1, que não tocam em fórmula — mas quem executar a Fase 3 precisa saber disso.

## Review Focus

1. **Instrumento sem nenhum certificado válido.** `get_certificate_valid()` devolve recordset vazio e o QWeb faz `t-field` nele → o PDF quebra do mesmo jeito que quebra hoje com vários. Coberto na Task 3, Step 1.
2. **Certificado com `validate_calibration` vazio.** `verify_is_valid()` compara `False >= date.today()` → `TypeError`. Registro assim é criável hoje (o campo não é `required`). Coberto na Task 2, Step 1.
3. **Calibração com `date_next_calibration` vazio.** `_check_date_calibration` compara `date > False` → `TypeError` ao salvar. Coberto na Task 4, Step 1.
4. **`display_decimals` zero, vazio ou não configurado** na unidade de medida → QWeb recebe `precision=0`/`None` e imprime valor truncado ou estoura. Coberto na Task 6, Step 1.
5. **Valores históricos após a troca de coluna `double precision` → `numeric`.** Medidas gravadas com mais de 6 casas são arredondadas pelo `ALTER TABLE`. Coberto na Task 5, Step 6 (verificação pós-upgrade em dado real).

---

## Estrutura de arquivos

**Criar:**
- `engenapp/engc_os/tests/__init__.py` — registro dos módulos de teste
- `engenapp/engc_os/tests/common.py` — `CalibrationCase`, fixture compartilhada (padrão QPS-001 real)
- `engenapp/engc_os/tests/test_calibration_characterization.py` — fixa a matemática atual
- `engenapp/engc_os/tests/test_calibration_certificate.py` — validade e seleção de certificado
- `engenapp/engc_os/tests/test_calibration_bugs.py` — create/constraint/domain
- `engenapp/engc_os/tests/test_calibration_precision.py` — precisão decimal (Fase 1)
- `engenapp/engc_os/migrations/16.0.1.0.0/post-migrate.py` — consolidação não destrutiva de certificados duplicados
- `engenapp/engc_os/data/decimal_precision.xml` — registro `decimal.precision` "Calibration"

**Modificar:**
- `engenapp/engc_os/models/engc_calibration.py` — o grosso das correções
- `engenapp/engc_os/reports/calibration_certificate_template.xml` — singleton + precisão por unidade
- `engenapp/engc_os/views/calibration_instruments_views.xml` — arquivos de idioma
- `engenapp/engc_os/views/calibration_views.xml` — casas decimais nas colunas
- `engenapp/engc_os/security/ir.model.access.csv` — ACL do modelo novo
- `engenapp/engc_os/__manifest__.py` — versão e `data`

---

## Task 1: Infraestrutura de testes + caracterização da matemática atual

Sem isto nada mais é seguro: o módulo não tem um único teste, e as tasks seguintes mexem em código que produz números já impressos em certificados de cliente.

**Files:**
- Create: `engenapp/engc_os/tests/__init__.py`
- Create: `engenapp/engc_os/tests/common.py`
- Create: `engenapp/engc_os/tests/test_calibration_characterization.py`

**Interfaces:**
- Consumes: nada.
- Produces: `CalibrationCase` (classe base em `tests/common.py`) expondo, criados em `setUp`:
  - `self.unit_tempo` → `engc.calibration.measurement.unit` (name "Tempo", simbolo "s")
  - `self.instrument` → `engc.calibration.instruments` (name "QPS-001 - Cronômetro Digital")
  - `self.certificate` → certificado válido do instrumento (validade hoje + 1 ano)
  - `self.unc_line` → linha de incerteza: `uncertainty=0.035, coverage_factor=2.0, erro_value=0.01, resolution=0.01, veff=2.0`
  - `self.make_measurement(**kw)` → cria `engc.calibration.measurement` já com `instrument_id` e `unit_of_measurement`, disparando o onchange
  - `self.make_line(measurement, true_value, r1, r2, r3)` → cria `engc.calibration.measurement.lines`
  - `self.make_equipment(name='Autoclave 001')` → cria `engc.equipment` com os 6 obrigatórios resolvidos
  - `self.make_calibration_vals(**kw)` → dict pronto para `engc.calibration.create()`
  
  Números do fixture são os reais do certificado R0712/2026 lidos da base `odoo-labquali`.

- [ ] **Step 1: Criar o pacote de testes**

`engenapp/engc_os/tests/__init__.py`:
```python
from . import test_calibration_characterization
```

- [ ] **Step 2: Escrever a fixture compartilhada**

`engenapp/engc_os/tests/common.py`:
```python
from dateutil.relativedelta import relativedelta
from datetime import date

from odoo.tests.common import TransactionCase


class CalibrationCase(TransactionCase):
    """Fixture com os valores reais do padrão QPS-001 (cert. R0712/2026).

    Lidos da base odoo-labquali em 23/09/2026:
        incerteza 0,035 | k 2,0 | erro 0,01 | resolução 0,01 | veff 2 | unidade Tempo
    """

    def setUp(self):
        super().setUp()
        self.unit_tempo = self.env['engc.calibration.measurement.unit'].create({
            'name': 'Tempo',
            'simbolo': 's',
        })
        self.instrument = self.env['engc.calibration.instruments'].create({
            'name': 'QPS-001 - Cronômetro Digital',
            'id_number': 'QPS-001',
            'marca': 'Minipa',
            'modelo': 'MTH-1501',
        })
        self.certificate = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'R0712/2026',
            'date_calibration': date.today(),
            'validate_calibration': date.today() + relativedelta(years=1),
        })
        self.unc_line = self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'erro_value': 0.01,
            'resolution': 0.01,
            'veff': 2.0,
        })

    def make_measurement(self, **kw):
        """Cria uma medição já com o onchange do padrão disparado."""
        vals = {
            'title': 'Tempo',
            'date_measurement': date.today(),
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        }
        vals.update(kw)
        measurement = self.env['engc.calibration.measurement'].create(vals)
        # O preenchimento dos campos *_instrument só acontece via onchange hoje.
        measurement.onchange_unit_of_measurement()
        return measurement

    def make_line(self, measurement, true_value, r1, r2, r3):
        return self.env['engc.calibration.measurement.lines'].create({
            'measurement_id': measurement.id,
            'true_quantity_value': true_value,
            'measurement_quantity_value_1': r1,
            'measurement_quantity_value_2': r2,
            'measurement_quantity_value_3': r3,
            'coverage_factor': 2.0,
        })

    def make_equipment(self, name='Autoclave 001'):
        """engc.equipment tem 6 campos obrigatórios além do nome; todos
        precisam de registro próprio. Conferido no código do modelo."""
        return self.env['engc.equipment'].create({
            'name': name,
            'category_id': self.env['engc.equipment.category'].create(
                {'name': 'Categoria Teste'}).id,
            'means_of_aquisition_id': self.env[
                'engc.equipment.means.of.aquisition'].create(
                {'name': 'Compra'}).id,
            'location_id': self.env['engc.equipment.location'].create(
                {'name': 'Sala Teste'}).id,
            'marca_id': self.env['engc.equipment.marca'].create(
                {'name': 'Marca Teste'}).id,
            'model': 'MOD-001',
            'serial_number': 'SN-%s' % name,
        })

    def make_calibration_vals(self, **kw):
        """Dicionário mínimo que satisfaz os required de engc.calibration."""
        vals = {
            'client_id': self.env['res.partner'].create(
                {'name': 'Hospital Teste'}).id,
            'equipment_id': self.make_equipment().id,
            'technician_id': self.env['hr.employee'].create(
                {'name': 'Técnico Teste'}).id,
            'measurement_procedure': self.env[
                'engc.calibration.measurement.procedure'].create({
                    'codigo': 'PM-001',
                    'description': 'Procedimento de teste',
                }).id,
            'date_calibration': date.today(),
            'date_next_calibration': date.today() + relativedelta(years=1),
            'instruments_ids': [(6, 0, [self.instrument.id])],
        }
        vals.update(kw)
        return vals
```

> **Nota para quem implementa:** os modelos auxiliares
> (`engc.equipment.category`, `.means.of.aquisition`, `.location`, `.marca`)
> foram conferidos como tendo só `name` obrigatório. Se algum recusar a
> criação, ler o modelo em `models/engc_equipments.py` e completar — **não**
> contornar removendo o campo obrigatório do equipamento.

- [ ] **Step 3: Escrever os testes de caracterização (devem passar de primeira)**

Estes testes **fixam o comportamento atual**, inclusive o que o relatório aponta como errado. Não é engano: é a rede de segurança. A Fase 3 vai virar cada asserção de propósito, uma por uma.

`engenapp/engc_os/tests/test_calibration_characterization.py`:
```python
from math import sqrt

from .common import CalibrationCase


class TestCalibrationCharacterization(CalibrationCase):
    """Fixa a matemática ATUAL de _compute_statistics.

    ATENÇÃO: várias destas asserções fixam fórmulas que o relatório
    2026-09-23-analise-calibracao-incerteza-precisao.md aponta como
    incorretas (seção 5). É intencional. Elas são a rede de segurança das
    Fases 0 e 1, que não podem mudar número nenhum. Quem executar a Fase 3
    deve alterar cada asserção DE PROPÓSITO, registrando o delta na mensagem
    de commit.
    """

    def test_padrao_preenchido_pelo_onchange(self):
        m = self.make_measurement()
        self.assertAlmostEqual(m.uncertainty_instrument, 0.035, places=6)
        self.assertAlmostEqual(m.coverage_factor_instrument, 2.0, places=6)
        self.assertAlmostEqual(m.erro_value_instrument, 0.01, places=6)
        self.assertAlmostEqual(m.resolution_instrument, 0.01, places=6)

    def test_media_e_erro(self):
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertAlmostEqual(line.measurement_quantity_value_mean, 60.054, places=6)
        self.assertAlmostEqual(line.erro_value, 0.054, places=6)

    def test_incerteza_expandida_valor_atual(self):
        """Valor conferido à mão a partir da fórmula vigente.

        uc = sqrt((s/2)^2 + (0.035/2)^2 + (0.01/sqrt(3))^2 + (0.01/sqrt(12))^2)
        U  = k * uc, com k = 2,0
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertAlmostEqual(line.uncertainty, 0.037318, places=5)

    def test_veff_atual_usa_constante_3(self):
        """Fórmula vigente: 3*(uc/(s/2))**4 — não é Welch-Satterthwaite."""
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertGreater(line.veff, 100.0)

    def test_tipo_a_usa_divisor_2_e_nao_raiz_de_n(self):
        """Pino explícito do divisor errado, para a Fase 3 ter o que virar.

        Se o termo Tipo A usasse s/sqrt(3), U seria maior. Este teste falha
        no instante em que alguém corrigir a fórmula — que é exatamente o
        sinal desejado.
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        s = 0.001
        esperado_atual = 2.0 * sqrt(
            (s / 2) ** 2
            + (0.035 / 2.0) ** 2
            + (0.01 / sqrt(3)) ** 2
            + (0.01 / sqrt(12)) ** 2
        )
        # places=5 de propósito, NÃO 6: a Task 5 passa a gravar com
        # digits='Calibration' (6 casas), e o valor gravado (0.037318) fica a
        # 4,49e-7 do calculado — dentro da tolerância de places=6 por apenas
        # 5e-8. Margem de 10% é armadilha de teste intermitente.
        self.assertAlmostEqual(line.uncertainty, esperado_atual, places=5)

    def test_leitura_faltando_entra_como_zero(self):
        """Documenta o defeito da seção 5.6: só duas leituras preenchidas
        envenenam a média. Não é comportamento desejado — é o atual.

        mean([60.053, 60.055, 0.0]) = 40.036. O 40 não é erro de digitação:
        é a terceira leitura vazia entrando como zero.

        NA FASE 3 este teste deve virar: com duas leituras preenchidas a
        média tem que ser 60.054 (média das duas de verdade), e o n usado
        no termo Tipo A passa a ser 2.
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 0.0)
        self.assertAlmostEqual(line.measurement_quantity_value_mean, 40.036, places=3)
```

- [ ] **Step 4: Declarar o pacote de testes e rodar**

O Odoo descobre `tests/` sozinho; não precisa entrar no `data` do manifest. Rodar:

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestCalibrationCharacterization 2>&1 | tail -30
```

Esperado: 6 testes, todos PASS. Se algum falhar, **não ajustar o teste para passar** — investigar, porque significa que o comportamento real difere do que o relatório apurou.

- [ ] **Step 5: Commit**

Delegar ao subagente `git-commit-push` com `cwd=/home/afonso/docker/odoo_engenapp`:

```
paths: engenapp/engc_os/tests/
mensagem: test(engc_os): add calibration test harness with characterization tests

Pins current uncertainty math (including the known-wrong s/2 divisor and
the constant-3 veff) so phases 0 and 1 cannot change numbers by accident.
Fixture uses the real QPS-001 standard values read from odoo-labquali.
```

---

## Task 2: Corrigir `is_valid` e unificar a regra de validade

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py:218-238`
- Create: `engenapp/engc_os/tests/test_calibration_certificate.py`
- Modify: `engenapp/engc_os/tests/__init__.py`

**Interfaces:**
- Consumes: `CalibrationCase` da Task 1.
- Produces:
  - `CalibrationInstrumentCertificates.is_valid` — `fields.Boolean(compute='_compute_is_valid', store=False)`, agora sempre atribuído, `False` quando `validate_calibration` é vazio.
  - `CalibrationInstrumentCertificates.verify_is_valid()` — mantida, agora segura contra data vazia e contra recordset múltiplo.

- [ ] **Step 1: Escrever os testes que falham**

`engenapp/engc_os/tests/test_calibration_certificate.py`:
```python
from datetime import date

from dateutil.relativedelta import relativedelta

from .common import CalibrationCase


class TestCertificateValidity(CalibrationCase):

    def test_certificado_vencido_nao_e_valido(self):
        self.certificate.validate_calibration = date.today() - relativedelta(days=1)
        self.assertFalse(self.certificate.is_valid)

    def test_certificado_no_prazo_e_valido(self):
        self.assertTrue(self.certificate.is_valid)

    def test_certificado_vence_hoje_ainda_e_valido(self):
        self.certificate.validate_calibration = date.today()
        self.assertTrue(self.certificate.is_valid)

    def test_certificado_sem_data_de_validade_nao_estoura(self):
        """Review Focus 2: validate_calibration vazio comparava False com date."""
        cert = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'SEM-DATA',
        })
        self.assertFalse(cert.is_valid)

    def test_is_valid_em_lote(self):
        """O compute precisa atribuir todos os registros do recordset."""
        cert2 = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'R9999/2026',
            'validate_calibration': date.today() - relativedelta(days=1),
        })
        lote = self.certificate | cert2
        self.assertEqual(lote.mapped('is_valid'), [True, False])
```

Acrescentar em `engenapp/engc_os/tests/__init__.py`:
```python
from . import test_calibration_characterization
from . import test_calibration_certificate
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestCertificateValidity 2>&1 | tail -30
```
Esperado: FAIL em `test_certificado_sem_data_de_validade_nao_estoura` (TypeError) e em `test_is_valid_em_lote` (Expected singleton).

- [ ] **Step 3: Corrigir o compute**

Em `models/engc_calibration.py`, substituir o bloco atual (linhas ~218-238):

```python
    is_valid = fields.Boolean(string="É válido", compute="_compute_is_valid")

    @api.depends('validate_calibration')
    def _compute_is_valid(self):
        if self.validate_calibration :
            return self.verify_is_valid()
```

por:

```python
    is_valid = fields.Boolean(
        string="É válido",
        compute="_compute_is_valid",
        help="Certificado dentro do prazo de validade na data de hoje.",
    )

    @api.depends('validate_calibration')
    def _compute_is_valid(self):
        hoje = date.today()
        for rec in self:
            rec.is_valid = bool(rec.validate_calibration) and rec.validate_calibration >= hoje
```

E tornar `verify_is_valid` segura (mantida porque é API pública do modelo):

```python
    def verify_is_valid(self):
        self.ensure_one()
        return bool(self.validate_calibration) and self.validate_calibration >= date.today()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 5 testes PASS.

- [ ] **Step 5: Rodar a suíte inteira**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "(ERROR|FAIL|tests.stats)"
```
Esperado: só a falha pré-existente `test_fleet_single_logger_two_temp_standards`.

- [ ] **Step 6: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/tests/
mensagem: fix(engc_os): make certificate is_valid assign on every record

_compute_is_valid returned instead of assigning and dereferenced a
recordset field, so it only worked through read()'s per-record fallback and
raised TypeError when validate_calibration was empty.
```

---

## Task 3: Certificado singleton + variantes de idioma + P0 do PDF

Esta é a task que fecha o P0 confirmado no QPT-014.

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py:156-240`
- Modify: `engenapp/engc_os/reports/calibration_certificate_template.xml:128-142`
- Modify: `engenapp/engc_os/security/ir.model.access.csv`
- Modify: `engenapp/engc_os/views/calibration_instruments_views.xml`
- Modify: `engenapp/engc_os/__manifest__.py`
- Create: `engenapp/engc_os/migrations/16.0.1.0.0/post-migrate.py`
- Modify: `engenapp/engc_os/tests/test_calibration_certificate.py`

**Interfaces:**
- Consumes: `is_valid` corrigido na Task 2.
- Produces:
  - Modelo novo `engc.calibration.instruments.certificates.file` com campos
    `certificate_id` (M2o, required, ondelete cascade), `lang_id` (M2o `res.lang`),
    `name` (Char), `file` (Binary), `filename` (Char).
  - `CalibrationInstrumentCertificates.certificate_file_ids` — O2m para o modelo acima.
  - `CalibrationInstrumentCertificates.superseded_by_id` — M2o para o próprio modelo; quando preenchido, o certificado é ignorado pelas buscas de validade.
  - `CalibrationInstrument.get_valid_certificates()` — **novo**, devolve recordset de todos os válidos e não substituídos, ordenado por `date_calibration desc, id desc`.
  - `CalibrationInstrument.get_certificate_valid()` — **assinatura mantida**, agora devolve **no máximo um** registro (o primeiro de `get_valid_certificates()`). O nome fica porque o QWeb e `_compute_unit_of_measurement_domain` já o chamam.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `engenapp/engc_os/tests/test_calibration_certificate.py`:
```python
class TestCertificateSelection(CalibrationCase):

    def _novo_certificado(self, numero, validade_anos=1, calibrado_em=None):
        return self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': numero,
            'date_calibration': calibrado_em or date.today(),
            'validate_calibration': date.today() + relativedelta(years=validade_anos),
        })

    def test_um_certificado_valido_devolve_ele(self):
        self.assertEqual(self.instrument.get_certificate_valid(), self.certificate)

    def test_varios_validos_devolve_singleton(self):
        """O caso QPT-014 real: 3 certificados válidos quebravam o PDF."""
        self._novo_certificado('R1236/2026')
        self._novo_certificado('R1236/2026 - Inglês')
        escolhido = self.instrument.get_certificate_valid()
        self.assertEqual(len(escolhido), 1)

    def test_escolhe_o_de_calibracao_mais_recente(self):
        antigo = self.certificate
        antigo.date_calibration = date.today() - relativedelta(years=2)
        novo = self._novo_certificado('R1236/2026', calibrado_em=date.today())
        self.assertEqual(self.instrument.get_certificate_valid(), novo)

    def test_certificado_substituido_e_ignorado(self):
        dup = self._novo_certificado('R0712/2026 - Inglês')
        dup.superseded_by_id = self.certificate.id
        self.assertEqual(self.instrument.get_certificate_valid(), self.certificate)
        self.assertNotIn(dup, self.instrument.get_valid_certificates())

    def test_sem_certificado_valido_devolve_vazio_sem_estourar(self):
        """Review Focus 1: instrumento sem certificado válido."""
        self.certificate.validate_calibration = date.today() - relativedelta(days=1)
        self.assertEqual(len(self.instrument.get_certificate_valid()), 0)

    def test_arquivos_de_idioma_no_mesmo_certificado(self):
        en = self.env['res.lang'].search([('code', '=', 'en_US')], limit=1)
        arquivo = self.env['engc.calibration.instruments.certificates.file'].create({
            'certificate_id': self.certificate.id,
            'name': 'R0712/2026 - Inglês',
            'lang_id': en.id if en else False,
        })
        self.assertIn(arquivo, self.certificate.certificate_file_ids)
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestCertificateSelection 2>&1 | tail -30
```
Esperado: FAIL — o modelo `...certificates.file` não existe e `get_valid_certificates` não existe.

- [ ] **Step 3: Criar o modelo de arquivos de idioma**

Em `models/engc_calibration.py`, logo **depois** da classe `CalibrationInstrumentCertificates`:

```python
class CalibrationInstrumentCertificateFile(models.Model):
    _name = 'engc.calibration.instruments.certificates.file'
    _description = 'Arquivos do certificado (variantes de idioma)'
    _order = 'id'

    certificate_id = fields.Many2one(
        string='Certificado',
        comodel_name='engc.calibration.instruments.certificates',
        ondelete='cascade',
        required=True,
        index=True,
    )
    lang_id = fields.Many2one(
        string='Idioma', comodel_name='res.lang', ondelete='restrict')
    name = fields.Char(
        string='Identificação',
        help="Como este arquivo é identificado. Ex.: o número do certificado "
             "na versão em inglês.")
    file = fields.Binary(string='Arquivo')
    filename = fields.Char(string='Nome do arquivo')
```

- [ ] **Step 4: Acrescentar os campos no certificado e a seleção singleton**

Em `CalibrationInstrumentCertificates`, acrescentar junto aos demais campos:

```python
    certificate_file_ids = fields.One2many(
        string='Arquivos / idiomas',
        comodel_name='engc.calibration.instruments.certificates.file',
        inverse_name='certificate_id',
        help="Versões do MESMO certificado em outros idiomas. Não cadastre "
             "aqui um certificado diferente — crie outro registro.")
    superseded_by_id = fields.Many2one(
        string='Substituído por',
        comodel_name='engc.calibration.instruments.certificates',
        ondelete='set null',
        help="Preenchido quando este registro é duplicata de outro (ex.: a "
             "mesma calibração cadastrada duas vezes, em idiomas diferentes). "
             "Certificados substituídos são ignorados na escolha do válido.")
```

Em `CalibrationInstrument`, substituir `get_certificate_valid`:

```python
    def get_certificate_valid(self):
        return  self.certificate_ids.filtered(lambda rec: rec.is_valid)
```

por:

```python
    def get_valid_certificates(self):
        """Todos os certificados válidos e não substituídos, do mais recente
        para o mais antigo."""
        self.ensure_one()
        validos = self.certificate_ids.filtered(
            lambda rec: rec.is_valid and not rec.superseded_by_id)
        return validos.sorted(
            key=lambda rec: (rec.date_calibration or date.min, rec.id),
            reverse=True,
        )

    def get_certificate_valid(self):
        """Certificado válido a usar — no máximo UM registro.

        Devolvia o recordset inteiro, o que quebrava o `t-field` do template
        do certificado em qualquer instrumento com mais de um válido (caso
        real: QPT-014, com três). Assinatura mantida por causa do QWeb.
        """
        self.ensure_one()
        return self.get_valid_certificates()[:1]
```

- [ ] **Step 5: ACL do modelo novo**

Acrescentar a `engenapp/engc_os/security/ir.model.access.csv`:
```csv
access_engc_calibration_instruments_certificates_file_user,engc_os.engc.calibration.instruments.certificates.file,model_engc_calibration_instruments_certificates_file,base.group_user,1,1,1,1
```

- [ ] **Step 6: Rodar e confirmar que passa**

Mesmo comando do Step 2. Esperado: 6 testes PASS.

- [ ] **Step 7: Corrigir o QWeb (o P0 propriamente dito)**

Em `reports/calibration_certificate_template.xml`, substituir o bloco do `t-foreach` dos padrões (linhas ~133-140):

```xml
                            <t t-foreach="o.instruments_ids" t-as="i">
                                <span t-field="i.display_name" /> marca <span t-field="i.marca" />,
                                modelo <span t-field="i.modelo" />, número de série <span
                                    t-field="i.id_number" />.<br /> Certificado de calibração
                                 emitido por <span t-field="i.get_certificate_valid().certificate_partner" /> sob o número <span
                                    t-field="i.get_certificate_valid().certificate_number" /> com validade até <span 
                                    t-field="i.get_certificate_valid().validate_calibration" /><br />
                            </t>
```

por:

```xml
                            <t t-foreach="o.instruments_ids" t-as="i">
                                <t t-set="cert" t-value="i.get_certificate_valid()" />
                                <span t-field="i.display_name" /> marca <span t-field="i.marca" />,
                                modelo <span t-field="i.modelo" />, número de série <span
                                    t-field="i.id_number" />.<br />
                                <t t-if="cert">
                                    Certificado de calibração emitido por <span
                                        t-field="cert.certificate_partner" /> sob o número <span
                                        t-field="cert.certificate_number" /> com validade até <span
                                        t-field="cert.validate_calibration" /><br />
                                </t>
                                <t t-else="">
                                    <span class="text-danger">Sem certificado de calibração
                                        válido cadastrado para este padrão.</span><br />
                                </t>
                            </t>
```

Três ganhos: uma chamada em vez de três, recordset singleton garantido, e o caso "sem certificado válido" (Review Focus 1) deixa de quebrar o PDF.

- [ ] **Step 8: Expor os arquivos de idioma na view**

Em `views/calibration_instruments_views.xml`, dentro do `<form>` do certificado, logo depois da `<page string="Certificado">`, acrescentar:

```xml
                      <page string="Outros idiomas">
                        <field name="superseded_by_id"
                               domain="[('instrument_id','=',parent.id),('id','!=',id)]"
                               options="{'no_create': True}" />
                        <field name="certificate_file_ids">
                          <tree editable="bottom">
                            <field name="name" />
                            <field name="lang_id" />
                            <field name="file" widget="file" filename="filename" />
                            <field name="filename" invisible="1" />
                          </tree>
                        </field>
                      </page>
```

- [ ] **Step 9: Bump de versão e migração não destrutiva**

Em `__manifest__.py`, trocar `'version': '0.1',` por `'version': '16.0.1.0.0',`.

Criar `engenapp/engc_os/migrations/16.0.1.0.0/post-migrate.py`:

```python
"""Consolida certificados duplicados de um mesmo padrão — sem apagar nada.

Motivo (relatório 2026-09-23, seção 3 e item P0 da seção 7): o QWeb do
certificado fazia `t-field` no recordset devolvido por
get_certificate_valid(). Em instrumentos com mais de um certificado válido
isso levanta `Expected singleton` e o PDF não sai. Caso real na base
labquali: QPT-014 - Registrador Digital, com R1661/2025, R1236/2026 e
"R1236/2026 - Inglês" simultaneamente válidos.

A decisão de modelagem foi tratar "mesmo certificado em outro idioma" como
UM registro com vários arquivos. Esta migração aplica isso ao que já existe.

NÃO DESTRUTIVA de propósito: num contexto ISO/IEC 17025 não se apaga
registro de certificado. As duplicatas continuam na base, apenas marcadas
com superseded_by_id; o binário de cada uma é copiado para uma linha de
`certificate_file_ids` do certificado mantido, com o número original
preservado no campo `name`. Nada se perde e dá para desfazer limpando o
superseded_by_id.

Critério de duplicata (conservador — os três têm que bater):
    mesmo instrument_id, mesmo date_calibration, mesmo validate_calibration.
Mantém-se o de menor id. Certificados que não batem nos três campos são
deixados em paz, mesmo que o número seja parecido: adivinhar por string
("- Inglês") apagaria diferenças legítimas.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Sem predicado sobre superseded_by_id: nesta primeira migração a coluna
    # acabou de ser criada por este mesmo upgrade e está toda NULL, então o
    # filtro seria no-op — e evitá-lo tira a dependência da ordem entre a
    # atualização do schema e o post-migrate.
    cr.execute(
        """
        SELECT instrument_id, date_calibration, validate_calibration,
               array_agg(id ORDER BY id)
          FROM engc_calibration_instruments_certificates
      GROUP BY instrument_id, date_calibration, validate_calibration
        HAVING count(*) > 1
        """
    )
    grupos = cr.fetchall()
    if not grupos:
        _logger.info("engc_os: nenhum certificado duplicado a consolidar.")
        return

    total = 0
    for instrument_id, _data_cal, _validade, ids in grupos:
        mantido, duplicatas = ids[0], ids[1:]
        for dup_id in duplicatas:
            cr.execute(
                """
                SELECT certificate_number, certificate_calibration
                  FROM engc_calibration_instruments_certificates
                 WHERE id = %s
                """,
                (dup_id,),
            )
            numero, binario = cr.fetchone()
            cr.execute(
                """
                INSERT INTO engc_calibration_instruments_certificates_file
                            (certificate_id, name, file, create_uid, create_date,
                             write_uid, write_date)
                     VALUES (%s, %s, %s, 1, now() at time zone 'UTC',
                             1, now() at time zone 'UTC')
                """,
                (mantido, numero, binario),
            )
            cr.execute(
                """
                UPDATE engc_calibration_instruments_certificates
                   SET superseded_by_id = %s
                 WHERE id = %s
                """,
                (mantido, dup_id),
            )
            total += 1
        _logger.info(
            "engc_os: padrão %s — certificado %s mantido, %s marcado(s) como "
            "substituído(s): %s",
            instrument_id, mantido, len(duplicatas), duplicatas,
        )

    _logger.info(
        "engc_os: %s certificado(s) duplicado(s) consolidado(s) em %s grupo(s). "
        "Nada foi apagado.", total, len(grupos),
    )

    cr.execute(
        """
        SELECT c.instrument_id, count(*)
          FROM engc_calibration_instruments_certificates c
         WHERE c.superseded_by_id IS NULL
           AND c.validate_calibration >= CURRENT_DATE
      GROUP BY c.instrument_id
        HAVING count(*) > 1
        """
    )
    restantes = cr.fetchall()
    for instrument_id, quantos in restantes:
        _logger.warning(
            "engc_os: padrão %s ainda tem %s certificados válidos com datas "
            "DIFERENTES. O PDF vai usar o de calibração mais recente. Conferir "
            "se algum deveria ser variante de idioma de outro.",
            instrument_id, quantos,
        )
```

- [ ] **Step 10: Rodar a suíte inteira**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "(ERROR|FAIL|tests.stats|engc_os:)"
```
Esperado: só a falha pré-existente. As linhas de log da migração devem aparecer.

- [ ] **Step 11: Validar o PDF de verdade**

Regra do CLAUDE.md: testar a UI eu mesmo, não delegar o clique ao user. Via `agent-browser`, abrir uma calibração no estado `done` em `http://localhost:8084` e gerar o certificado. Confirmar que o PDF sai e que o bloco "Padrões utilizados" mostra um certificado por padrão.

- [ ] **Step 12: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/reports/calibration_certificate_template.xml engenapp/engc_os/security/ir.model.access.csv engenapp/engc_os/views/calibration_instruments_views.xml engenapp/engc_os/__manifest__.py engenapp/engc_os/migrations/ engenapp/engc_os/tests/
mensagem: fix(engc_os): make calibration certificate PDF render with multiple standards

get_certificate_valid() returned a recordset and the QWeb template did
t-field on it, so any standard with more than one valid certificate raised
Expected singleton and the PDF never rendered (real case: QPT-014, three
valid certificates). It now returns at most one record, chosen by most
recent date_calibration.

Same-certificate-different-language is now modelled as one certificate with
N language files. The 16.0.1.0.0 migration consolidates existing duplicates
without deleting anything: duplicates keep their row, get superseded_by_id
set, and their binary is copied into the kept certificate's file list.

Also handles the standard with no valid certificate, which broke the PDF the
same way.
```

---

## Task 4: Bugs restantes de `engc.calibration`

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — linhas 59-64, 93-105, 84-87, 318-327, 424-446, 483-487, 298
- Create: `engenapp/engc_os/tests/test_calibration_bugs.py`
- Modify: `engenapp/engc_os/tests/__init__.py`

**Interfaces:**
- Consumes: `CalibrationCase` da Task 1.
- Produces: nenhuma API nova. `EngcCalibration.create` passa a `@api.model_create_multi` e aceita lista de dicts.

- [ ] **Step 1: Escrever os testes que falham**

`engenapp/engc_os/tests/test_calibration_bugs.py`:
```python
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError

from .common import CalibrationCase


class TestCalibrationBugs(CalibrationCase):

    def test_create_confirma_o_registro_criado(self):
        """create() chamava action_confirmed() em self (recordset vazio)."""
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        self.assertEqual(cal.state, 'confirmed')
        self.assertNotEqual(cal.name, 'New')

    def test_create_multi(self):
        cals = self.env['engc.calibration'].create([
            self.make_calibration_vals(), self.make_calibration_vals(),
        ])
        self.assertEqual(len(cals), 2)
        self.assertEqual(len(set(cals.mapped('name'))), 2)

    def test_proxima_calibracao_vazia_nao_estoura(self):
        """Review Focus 3: comparava date > False."""
        cal = self.env['engc.calibration'].create(
            self.make_calibration_vals(date_next_calibration=False))
        self.assertFalse(cal.date_next_calibration)

    def test_proxima_calibracao_anterior_e_rejeitada(self):
        with self.assertRaises(ValidationError):
            self.env['engc.calibration'].create(self.make_calibration_vals(
                date_calibration=date.today(),
                date_next_calibration=date.today() - relativedelta(days=1),
            ))

    def test_dominio_do_padrao_restringe_aos_da_calibracao(self):
        """_compute_instrument_id_domain condicionava ao próprio valor."""
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id,
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        self.assertIn(str(self.instrument.id), medicao.instrument_id_domain)
```

Acrescentar o import em `tests/__init__.py`.

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestCalibrationBugs 2>&1 | tail -40
```

- [ ] **Step 3: Corrigir a constraint de datas**

```python
    @api.constrains("date_next_calibration", "date_calibration", )
    def _check_date_calibration(self):
        for rec in self:
            if not rec.date_calibration or not rec.date_next_calibration:
                continue
            if rec.date_calibration > rec.date_next_calibration:
                raise ValidationError(_("A data de calibração não pode ser maior que a data da próxima calibração"))
```

- [ ] **Step 4: Corrigir o `create`**

```python
    @api.model_create_multi
    def create(self, vals_list):
        """Gera a sequência e já confirma as calibrações criadas."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                sequencia = self.env['ir.sequence']
                if vals.get('company_id'):
                    sequencia = sequencia.with_company(vals['company_id'])
                vals['name'] = sequencia.next_by_code('engc.calibration_sequence') or _('New')

        registros = super(EngcCalibration, self).create(vals_list)
        registros.action_confirmed()
        return registros
```

E em `action_confirmed`, trocar `rec.os_id.calibration_id = self.id` por `rec.os_id.calibration_id = rec.id`:

```python
    def action_confirmed(self):
        for rec in self:
            resp = rec.write({
                'state': 'confirmed',
            })
            if resp:
                if rec.os_id:
                    rec.os_id.calibration_created = True
                    rec.os_id.calibration_id = rec.id
```

- [ ] **Step 5: Corrigir o domínio do padrão**

```python
    @api.depends('calibration_id')
    def _compute_instrument_id_domain(self):
        for rec in self:
            ids_permitidos = rec.calibration_id.instruments_ids.ids
            rec.instrument_id_domain = json.dumps([('id', 'in', ids_permitidos)])
```

- [ ] **Step 6: Limpar código morto**

1. Remover o onchange que só loga (linhas ~84-87):
```python
    @api.onchange('measurement_ids')
    def onchange_measurement_ids(self):
        if self.measurement_ids:
            _logger.info(self.measurement_ids)
```
2. Remover o bloco de atributos órfãos em `CalibrationMeasurementLines` (linhas ~430-434): `related='field_name',` / `readonly=True,` / `store=True`.
3. Remover o campo morto `uncertainty = fields.Char('Incerteza')` de `CalibrationMeasurement` (linha ~298) — o valor real vive nas linhas. **Confirmar antes com `grep -rn "\.uncertainty" engenapp/engc_os/` que nada de `measurement` o usa.**
4. Renomear `resolutino_instrument` → `resolution_instrument_line` em `CalibrationMeasurementLines` e passar a atribuí-lo em `_compute_statistics` (`record.resolution_instrument_line = resolution_instrument`).

   ⚠️ **O campo é `store=True`, então renomear cria coluna nova e abandona a antiga — o Odoo não copia valor.** Hoje isso é inofensivo porque `_compute_statistics` nunca o atribui, ou seja, a coluna existente é toda zero. **Confirmar isso ANTES de renomear**, não depois:
   ```bash
   docker exec odoo_engenapp-db-qualificacao-1 psql -U odoo -d qualificacao-dev -tAc \
     "SELECT count(*) FROM engc_calibration_measurement_lines
       WHERE resolutino_instrument IS NOT NULL AND resolutino_instrument != 0;"
   ```
   Esperado: `0`. Se vier diferente de zero, **parar e avisar** — há dado real na coluna e o rename precisa de migração que o copie.

   Conferir também com `grep -rn "resolutino" engenapp/` que não há outra referência. Atenção: passar a atribuir um `store=True` que antes ficava sem atribuição é justamente a mudança que pode levantar "compute method failed to assign" — a suíte completa do Step 8 é o portão disso.

- [ ] **Step 7: Trocar o `except` nu**

Em `_compute_statistics`, trocar:
```python
                try:
                    record.veff = 3*(combined_uncertainty/(stdev(values)/2))**4
                except:
                    record.veff = 0
```
por:
```python
                # Fórmula vigente (NÃO é Welch-Satterthwaite — ver seção 5.2 do
                # relatório; a correção é da Fase 3). Aqui só se troca o except
                # nu por um específico: leituras idênticas zeram o desvio padrão.
                try:
                    record.veff = 3*(combined_uncertainty/(stdev(values)/2))**4
                except ZeroDivisionError:
                    record.veff = 0
```

- [ ] **Step 8: Rodar os testes da task e a suíte inteira**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "(ERROR|FAIL|tests.stats)"
```
Esperado: só a falha pré-existente. **Os testes de caracterização da Task 1 têm que continuar passando** — se algum mudou de valor, uma fórmula foi mexida sem querer.

- [ ] **Step 9: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/tests/
mensagem: fix(engc_os): correct calibration create, date constraint and standard domain

create() confirmed an empty recordset and wrote self.id into the OS link;
it is now model_create_multi and acts on the created records. The date
constraint compared a date against False when next calibration was empty.
_compute_instrument_id_domain gated on its own value, so the standard was
never restricted to the ones on the calibration. Also drops dead fields and
narrows a bare except. No uncertainty formula changed.
```

---

## Task 5: `decimal.precision` e `digits` nos campos

**Files:**
- Create: `engenapp/engc_os/data/decimal_precision.xml`
- Modify: `engenapp/engc_os/__manifest__.py`
- Modify: `engenapp/engc_os/models/engc_calibration.py`
- Create: `engenapp/engc_os/tests/test_calibration_precision.py`
- Modify: `engenapp/engc_os/tests/__init__.py`

**Interfaces:**
- Consumes: `CalibrationCase` da Task 1.
- Produces: registro `decimal.precision` com `name='Calibration'`, xmlid `engc_os.decimal_calibration`, `digits=6`. Todos os Float da cadeia de calibração passam a usar `digits='Calibration'`.

> ⚠️ **Este passo troca o tipo da coluna de `double precision` para `numeric(16,6)`.** O `ALTER TABLE` roda sozinho no `-u`. Fazer **backup do banco antes**:
> ```bash
> docker exec odoo_engenapp-db-qualificacao-1 pg_dump -U odoo qualificacao-dev \
>   > /tmp/claude-1000/qualificacao-dev-pre-digits.sql
> ```

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar em `engenapp/engc_os/tests/__init__.py` — **sem isto o Odoo não descobre o arquivo e os testes desta task nunca rodam**, dando falso verde:
```python
from . import test_calibration_precision
```

`engenapp/engc_os/tests/test_calibration_precision.py`:
```python
from .common import CalibrationCase


class TestCalibrationPrecision(CalibrationCase):

    def test_precisao_decimal_configurada(self):
        precisao = self.env.ref('engc_os.decimal_calibration')
        self.assertEqual(precisao.name, 'Calibration')
        self.assertGreaterEqual(precisao.digits, 6)

    def test_leitura_com_tres_casas_e_preservada(self):
        """O caso da imagem do relatório: 60,053 não pode virar 60,05."""
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertAlmostEqual(line.measurement_quantity_value_1, 60.053, places=6)
        self.assertAlmostEqual(line.measurement_quantity_value_2, 60.055, places=6)

    def test_valor_de_mil_segundos_com_tres_casas(self):
        """Ponto de 1200,043 s da imagem — 7 algarismos significativos."""
        m = self.make_measurement()
        line = self.make_line(m, 1200.0, 1200.043, 1200.046, 1200.044)
        self.assertAlmostEqual(line.measurement_quantity_value_mean, 1200.044333, places=5)

    def test_incerteza_do_padrao_com_tres_casas(self):
        """0,035 precisa sobreviver ao round-trip no banco."""
        self.assertAlmostEqual(self.unc_line.uncertainty, 0.035, places=6)
        self.assertAlmostEqual(self.unc_line.resolution, 0.01, places=6)

    def test_erro_pequeno_nao_vira_zero(self):
        """Erros da imagem são da ordem de -0,002 s."""
        m = self.make_measurement()
        line = self.make_line(m, 60.055, 60.053, 60.053, 60.053)
        self.assertAlmostEqual(line.erro_value, -0.002, places=6)
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestCalibrationPrecision 2>&1 | tail -30
```
Esperado: FAIL em `test_precisao_decimal_configurada` (xmlid não existe).

- [ ] **Step 3: Criar o registro de precisão**

`engenapp/engc_os/data/decimal_precision.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="decimal_calibration" model="decimal.precision">
            <field name="name">Calibration</field>
            <field name="digits">6</field>
        </record>
    </data>
</odoo>
```

`noupdate="1"` de propósito: se o usuário ajustar os dígitos pela interface, um `-u` não deve desfazer.

Em `__manifest__.py`, acrescentar no `data`, **antes** de `views/calibration_views.xml`:
```python
        'data/decimal_precision.xml',
```

- [ ] **Step 4: Aplicar `digits` nos campos**

Em `models/engc_calibration.py`, acrescentar `digits='Calibration'` nos Float da cadeia.

Em `CalibrationIntrumentUncertaintyLines`:
```python
    erro_value = fields.Float(string="Erro fiducial", digits='Calibration')
    uncertainty = fields.Float('Incerteza', required=True, digits='Calibration')
    resolution = fields.Float(
        string="Resolução", help="Resolução do padrão", required=True,
        digits='Calibration')
```
(`coverage_factor` e `veff` ficam como estão — são adimensionais e 2 casas bastam.)

Em `CalibrationMeasurement`, nos cinco campos `*_instrument`:
```python
    uncertainty_instrument = fields.Float(readonly=True, digits='Calibration')
    erro_value_instrument = fields.Float(readonly=True, digits='Calibration')
    coverage_factor_instrument = fields.Float(readonly=True)
    resolution_instrument = fields.Float(readonly=True, digits='Calibration')
    veff_instrument = fields.Float(readonly=True)
```

Em `CalibrationMeasurementLines`:
```python
    true_quantity_value = fields.Float(string="Valor Real", digits='Calibration')
    measurement_quantity_value_1 = fields.Float(string="Leitura 01", digits='Calibration')
    measurement_quantity_value_2 = fields.Float(string="Leitura 02", digits='Calibration')
    measurement_quantity_value_3 = fields.Float(string="Leitura 03", digits='Calibration')
    measurement_quantity_value_mean = fields.Float(
        string="Média", compute="_compute_statistics", store=True, digits='Calibration')
    erro_value = fields.Float(
        string="Valor Erro", compute="_compute_statistics", store=True, digits='Calibration')
    uncertainty = fields.Float(
        string="Incerteza", compute="_compute_statistics", store=True, digits='Calibration')
```

- [ ] **Step 5: Backup, rodar e confirmar que passa**

Fazer o `pg_dump` do aviso acima **antes** de rodar. Depois:
```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "(ERROR|FAIL|tests.stats)"
```
Esperado: 5 testes novos PASS, caracterização continua PASS, só a falha pré-existente.

> ⚠️ **Correção de 23/09: os 5 testes acima NÃO guardam a mudança.** Apurado na execução e confirmado
> por revisão contra o `fields.py` do Odoo 16: todos passam com `digits='Calibration'` removido de
> todos os campos. O armazenamento (`double precision`) nunca esteve quebrado — o bug só aparece no
> widget web, que lê `fields_get()['digits']`. É **obrigatório** acrescentar uma asserção
> discriminante via `fields_get`, exigindo `(16, 6)` nos campos dimensionais e vazio nos adimensionais,
> e vê-la falhar com o `digits` removido de propósito antes de confiar nela.

- [ ] **Step 6: Conferir o dado histórico depois do ALTER TABLE**

Review Focus 5 — confirmar que a coluna mudou de tipo e que nada virou NULL:
```bash
docker exec odoo_engenapp-db-qualificacao-1 psql -U odoo -d qualificacao-dev -c "
  SELECT column_name, data_type, numeric_precision, numeric_scale
    FROM information_schema.columns
   WHERE table_name = 'engc_calibration_measurement_lines'
     AND column_name IN ('true_quantity_value','uncertainty','erro_value');"
docker exec odoo_engenapp-db-qualificacao-1 psql -U odoo -d qualificacao-dev -c "
  SELECT count(*) AS total,
         count(true_quantity_value) AS com_valor
    FROM engc_calibration_measurement_lines;"
```
Esperado: tipo `numeric` e `com_valor` igual ao que era antes do upgrade.

> **Correção de 23/09, apurada na execução:** a coluna vira `numeric` **sem escala no typmod** — não
> `numeric(16,6)` como este plano previa. É comportamento padrão do Odoo: `Float.column_type` devolve
> sempre `('numeric','numeric')` quando há `digits`, e o arredondamento é imposto na camada ORM
> (`convert_to_column`/`convert_to_cache` via `float_round`), não por constraint de coluna. Portanto
> `numeric_scale` vem **vazio** nessa consulta, e isso está certo.

- [ ] **Step 7: Commit**

```
paths: engenapp/engc_os/data/decimal_precision.xml engenapp/engc_os/__manifest__.py engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/tests/
mensagem: feat(engc_os): add Calibration decimal precision with 6 digits

Calibration floats had no digits, so the web widget rendered them with the
default 2 decimals and a 60.053 s reading showed as 60.05. Storage was
never the problem (double precision); this makes the UI match the data.

Note this changes the affected columns from double precision to
numeric(16,6) on upgrade.
```

---

## Task 6: Casas decimais por unidade de medida no certificado

**Files:**
- Modify: `engenapp/engc_os/models/engc_calibration.py` — `CalibrationMeasurementUnit`
- Modify: `engenapp/engc_os/reports/calibration_certificate_template.xml:164-200`
- Modify: `engenapp/engc_os/views/calibration_views.xml`
- Modify: `engenapp/engc_os/__manifest__.py` — versão
- Modify: `engenapp/engc_os/tests/test_calibration_precision.py`

**Interfaces:**
- Consumes: `decimal.precision` da Task 5.
- Produces: `CalibrationMeasurementUnit.display_decimals` — `fields.Integer`, default 3, com constraint `0 <= valor <= 6`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `engenapp/engc_os/tests/test_calibration_precision.py`:
```python
from odoo.exceptions import ValidationError


class TestUnitDisplayDecimals(CalibrationCase):

    def test_default_de_tres_casas(self):
        unidade = self.env['engc.calibration.measurement.unit'].create({
            'name': 'Pressão', 'simbolo': 'bar',
        })
        self.assertEqual(unidade.display_decimals, 3)

    def test_aceita_zero_casas(self):
        """Review Focus 4: zero é valor legítimo (ex.: contagem de ciclos)."""
        unidade = self.env['engc.calibration.measurement.unit'].create({
            'name': 'Ciclos', 'simbolo': 'un', 'display_decimals': 0,
        })
        self.assertEqual(unidade.display_decimals, 0)

    def test_rejeita_valor_negativo(self):
        with self.assertRaises(ValidationError):
            self.env['engc.calibration.measurement.unit'].create({
                'name': 'Inválida', 'simbolo': 'x', 'display_decimals': -1,
            })

    def test_rejeita_acima_do_armazenado(self):
        with self.assertRaises(ValidationError):
            self.env['engc.calibration.measurement.unit'].create({
                'name': 'Inválida', 'simbolo': 'x', 'display_decimals': 7,
            })

    def test_unidade_tempo_do_fixture_tem_tres_casas(self):
        self.assertEqual(self.unit_tempo.display_decimals, 3)
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init \
  --test-tags /engc_os:TestUnitDisplayDecimals 2>&1 | tail -30
```

- [ ] **Step 3: Acrescentar o campo na unidade**

Em `CalibrationMeasurementUnit`:
```python
    display_decimals = fields.Integer(
        string="Casas decimais",
        default=3,
        required=True,
        help="Quantas casas decimais usar ao imprimir valores desta unidade no "
             "certificado. Tempo em segundos costuma pedir 3; temperatura, 2.",
    )

    @api.constrains('display_decimals')
    def _check_display_decimals(self):
        for rec in self:
            if rec.display_decimals < 0 or rec.display_decimals > 6:
                raise ValidationError(
                    _("As casas decimais devem ficar entre 0 e 6 — 6 é a "
                      "precisão com que os valores são armazenados."))
```

- [ ] **Step 4: Parametrizar o QWeb**

Em `reports/calibration_certificate_template.xml`, dentro do `t-foreach` das linhas, começar com:
```xml
                                <tr t-foreach="m.measurement_lines" t-as="l">
                                    <t t-set="casas"
                                       t-value="l.unit_of_measurement.display_decimals or 0" />
```

e trocar **cada** `t-options='{"widget": "float", "precision": 2}'` dos valores com unidade por:
```xml
                                            t-options-widget="'float'"
                                            t-options-precision="casas"
```

Vale para `measurement_quantity_value_mean`, `erro_value` e `uncertainty`. Acrescentar o mesmo em `true_quantity_value`, que hoje imprime sem `t-options` nenhum.

**Não** mexer nos `precision: 2` de `coverage_factor` e `veff` — são adimensionais e 2 casas é o certo.

O `or 0` cobre o Review Focus 4: unidade não preenchida na linha devolve recordset vazio, cujo `display_decimals` é `False`.

- [ ] **Step 5: Mostrar o campo na view da unidade**

Em `views/calibration_views.xml`, no form de `engc.calibration.measurement.unit`:
```xml
          <group string="">
            <group>
              <field name="simbolo"/>
              <field name="display_decimals"/>
            </group>
          </group>
```

- [ ] **Step 6: Bump de versão**

Em `__manifest__.py`, trocar `'version': '16.0.1.0.0',` por `'version': '16.0.2.0.0',`.

- [ ] **Step 7: Rodar a suíte inteira**

```bash
docker exec odoo_engenapp-web-qualificacao-1 /entrypoint.sh -d qualificacao-dev \
  --no-http --test-enable -u engc_os --stop-after-init 2>&1 | grep -E "(ERROR|FAIL|tests.stats)"
```
Esperado: só a falha pré-existente.

- [ ] **Step 8: Validar o PDF com as casas certas**

Via `agent-browser` em `http://localhost:8084`: criar/abrir uma calibração com unidade Tempo e uma linha de 60,053 s, gerar o certificado e **conferir no PDF que aparece `60,053 s` e não `60,05 s`**. É o critério de aceitação da Fase 1.

- [ ] **Step 9: Commit**

```
paths: engenapp/engc_os/models/engc_calibration.py engenapp/engc_os/reports/calibration_certificate_template.xml engenapp/engc_os/views/calibration_views.xml engenapp/engc_os/__manifest__.py engenapp/engc_os/tests/
mensagem: feat(engc_os): print certificate values with per-unit decimal places

The certificate template hardcoded precision 2 on every measured value, so a
time reading of 60.053 s printed as 60.05 s. Decimals are now configured per
unit of measurement (default 3), leaving the dimensionless k and veff at 2.
```

---

## Fechamento da Fase 0 + Fase 1

- [ ] Rodar a suíte completa uma última vez e conferir contra o baseline (919 testes, 1 falha pré-existente).
- [ ] Rodar `superpowers:requesting-code-review` sobre a branch inteira.
- [ ] Apresentar ao usuário: o PDF do QPT-014 gerando, e uma medida de tempo com 3 casas no certificado.
- [ ] **Parar.** A Fase 2 (multiponto) altera o modelo de dados de certificados em uso no labquali e precisa de autorização explícita.

---

# Fecho da execução — 23/09/2026

Fases 0 e 1 entregues em 14 commits (`c922ec8..fb58cad`), branch `feat/calibracao-incerteza-precisao`.
Suíte: 40 métodos de teste no `engc_os` onde antes havia **zero**; baseline dos módulos dependentes
(919 testes) inalterada, com a única falha pré-existente conhecida.

## Defeitos deste plano apurados na execução

Registrados porque quem executar a Fase 2 vai reler este documento:

1. **A migração raw-SQL da Task 3 não funcionava.** `certificate_calibration` e o novo `file` são
   `fields.Binary` com `attachment=True` (padrão do Odoo) — moram em `ir_attachment`, **sem coluna**.
   `SELECT`/`INSERT` cru falha com `column does not exist`. Cópia de binário tem de passar pelo ORM.
2. **Os testes da Task 5 não guardavam nada.** Os cinco passavam com `digits='Calibration'` removido
   de todos os campos: o armazenamento (`double precision`) nunca esteve quebrado, o bug só aparecia
   no widget web. Guarda real = asserção sobre `fields_get()['digits']`.
3. **A Task 6 tinha o mesmo buraco no QWeb.** Reverter o template para `precision: 2` deixava os 959
   testes verdes. Guarda real = renderizar com `_render_qweb_html` e asserir na saída, ancorando a
   asserção negativa na tag inteira (`<span>60,05</span>`), porque `60,05` é prefixo de `60,054`.
4. **O grep do rename da Task 4 estava escopado errado** (`engenapp/` em vez do monorepo):
   `resolutino_instrument` é referenciado por `addons/afr_qualificacao/views/qualificacao_subrecords_views.xml:130`.
5. **A coluna não vira `numeric(16,6)`** e sim `numeric` sem escala; o arredondamento é do ORM.
6. **O predicado omitido na migração 16.0.1.0.0 foi um erro meu**, justificado por uma suposta
   dependência de ordem de schema que não existe — `post-migrate` roda depois do `_auto_init`.

## Pendências herdadas (nenhuma bloqueia merge)

| # | Item | Quando |
|---|---|---|
| 1 | `_search_statistics` estoura `Expected singleton` com 2+ certificados válidos distintos que tenham linha de incerteza na mesma unidade. **Reproduzido na prática.** | **Fase 2** (é o bloqueador dela) |
| 2 | Rename `resolutino_instrument` → `resolution_instrument_line`, coordenado com a view do submodule `afr_qualificacao` | Fase 2+ |
| 3 | Remover o hotfix duplicado `_compute_is_valid` em `addons/afr_qualificacao/models/calibration_instruments.py:122-135` — virou código morto | Fase 2+ |
| 4 | `_compute_has_valid_certificate` e `_compute_coverage` (mesmo arquivo, :192 e :222) ignoram `superseded_by_id` — 3ª e 4ª definições de "certificado válido" | Fase 2 |
| 5 | `CalibrationMeasurement.create` e `CalibrationMeasurementProcedure.create` continuam `@api.model`, tratam `vals_list` como dict e usam `force_company` (depreciado no 16) | cedo, é barato |
| 6 | `_compute_statistics` sem os campos `*_instrument` no `@api.depends` (item #5 da spec, severidade Alta) | Fase 2 |
| 7 | Sem guarda server-side contra auto-supersede / ciclo de supersede | qualquer hora |
| 8 | `make_equipment(name=...)` do fixture: `engc.equipment.name` é compute store sem inverse, o valor é descartado | quando alguém asserir `equipment.name` |

## Mudança de comportamento visível ao usuário

Calibração criada por `afr_qualificacao.action_create_engc_calibration()` agora nasce em
**"Em andamento"** e não mais em "Rascunho" — consequência intencional da correção do item #6
(o `create()` chamava `action_confirmed()` num recordset vazio, então nunca confirmava nada).

## Pergunta em aberto

A base `odoo-labquali` tem 24 certificados de padrão mas **zero calibrações emitidas**. A tabela da
imagem que originou esta análise (60,053 s, ±ITM 0,035, Veff Inf) veio de outra base, ainda não
identificada. **Antes de rodar `-u engc_os` em qualquer base com calibração real**, identificar qual
é: as garantias de segurança apuradas aqui (ALTER TABLE sobre tabela vazia, nenhum certificado
reescrito) valem só para o labquali.
