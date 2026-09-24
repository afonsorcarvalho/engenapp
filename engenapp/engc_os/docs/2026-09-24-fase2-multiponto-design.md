# Desenho detalhado — Fase 2: certificado multiponto (`engc_os`)

> ⚠️ **AVISO DE ESTADO — 24/09/2026**
>
> Este documento é o **levantamento de dados** que alimentou o brainstorm da Fase 2.
> A **Parte 1 (dados reais do labquali) é válida e continua sendo a referência.**
>
> A **Parte 2 (desenho) foi SUPERADA**: ela propõe três modos de linha
> (`point`/`range`/`formula`), e a decisão tomada no brainstorm foi **só ponto
> discreto** (YAGNI — não há certificado de faixa nem de fórmula no acervo).
>
> O desenho aprovado está em
> [superpowers/specs/2026-09-24-fase2-multiponto-design.md](superpowers/specs/2026-09-24-fase2-multiponto-design.md).
> Em caso de divergência, a spec vence.

**Data:** 24/09/2026
**Escopo:** detalhar a seção 3 de
[2026-09-23-analise-calibracao-incerteza-precisao.md](2026-09-23-analise-calibracao-incerteza-precisao.md)
em um desenho concreto, implementável, para a Fase 2 do roadmap.
**Natureza:** documento de investigação e desenho. **Nenhum código foi alterado.** As fórmulas de
incerteza (`_compute_statistics`) permanecem intocadas — correções de GUM são Fase 3.
**Base de dados consultada:** `odoo-labquali` (perfil MCP `odoo-labquali`), somente leitura.

---

## 0. Achado que muda o ponto de partida

A base `odoo-labquali` está rodando uma versão do `engc_os` **anterior** à Fase 0+1
(`16.0.2.0.0`, mergeada em `main-monorepo` no commit `1204ea0`). Os campos introduzidos nessa
fase — `superseded_by_id`, `certificate_file_ids` (modelo
`engc.calibration.instruments.certificates.file`), `display_decimals` — **não existem** no schema
remoto; as leituras abaixo devolveram `Invalid field` para eles. `is_valid` funciona corretamente
mesmo assim porque o hotfix de `afr_qualificacao/models/calibration_instruments.py:122-135`
(que sobrescreve `_compute_is_valid`) continua instalado e ativo — exatamente o mecanismo de
mascaramento que o relatório de 23/09 descreveu.

Consequência prática: **o `-u engc_os` da Fase 0+1 ainda não rodou em `labquali`.** O
`get_certificate_valid()` ali em produção ainda devolve recordset (não singleton) e o PDF do
QPT-014 ainda quebra hoje, ao vivo, nessa base. Qualquer migração da Fase 2 depende de rodar antes,
em sequência, as migrações `16.0.1.0.0` e `16.0.2.0.0` já existentes. Isto é a primeira questão em
aberto da seção 3.

---

## 1. Levantamento de dados reais

### 1.1 Certificados (`engc.calibration.instruments.certificates`) — 24 registros

| instrumento | certificados | válidos hoje | com linhas de incerteza |
|---|---|---|---|
| Validador (id 1) | 1 | 0 | 1 |
| Qualificador (id 2) | 1 | 1 | 1 |
| Termohigrometro (id 3) | 1 | 1 | 1 |
| Termohigrometro (id 4) | 1 | 1 | 1 |
| QPO-002 – Anemômetro de pás rotativas | 1 | 1 | 0 |
| QPP-004 – Transdutor de pressão | 1 | 1 | 0 |
| QPP-002 – Manômetro Analógico | 1 | 1 | 0 |
| QPT-012 – Registrador Digital | 1 | 1 | 0 |
| QPTH-001 – Termohigrômetro Digital | 1 | 1 | 0 |
| QPT-004 – Registrador Digital | 1 | 1 | 0 |
| QPP-005 – Transdutor de pressão | 1 | 1 | 0 |
| QPT-010 – Registrador Digital | 1 | 1 | 0 |
| **QPT-014 – Registrador Digital** | **3** (R1661/2025, R1236/2026, R1236/2026‑Inglês) | **3** | 0 |
| QPS-001 – Cronômetro Digital | 1 (R0712/2026) | 1 | 1 |
| QPT-003 – Termoresistência Pt-100 4 fios | 1 | 1 | 1 |
| QPT-001 – Simulador de temperatura | 2 | 1 | 0 |
| QPT-008 – Registrador Digital | 1 | 0 (vencido) | 0 |
| Datalogger Temp/Umidade (id 18) | 1 | 1 | 0 |
| Datalogger Temp/Umidade (id 19) | 1 | 1 | 0 |
| QPD-001 – Trena | 1 | 1 | 0 |
| QPF-001 – Dinamômetro | 1 | 1 | 0 |

Total: 24 certificados, 21 instrumentos, **6 certificados têm alguma linha de incerteza** (18 não
têm nenhuma). **Só o QPT-014 tem mais de um certificado válido simultâneo** — é exatamente o caso
P0 já corrigido na Fase 0 (não deployado ainda em `labquali`, ver seção 0).

### 1.2 Linhas de incerteza (`engc.calibration.instruments.uncertainty.lines`) — 8 registros, todas

| id | certificado (instrumento) | unidade | erro | incerteza | k | veff | resolução |
|---|---|---|---|---|---|---|---|
| 1 | #1 Validador | Celsius | 3 | 0,03 | 2 | 0 | 0 |
| 2 | #1 Validador | Bar | 0 | 0 | 2 | 0 | 0 |
| 3 | #2 Qualificador | Celsius | 0 | 0 | 2 | 0 | 0 |
| 4 | #2 Qualificador | Bar | 0 | 0 | 2 | 0 | 0 |
| 5 | #3 Termohigrometro | %UR | 0 | 0 | 2 | 0 | 0 |
| 6 | #4 Termohigrometro | %UR | 0 | 0 | 2 | 0 | 0 |
| **7** | **#14 QPS-001** | **Tempo** | **0,01** | **0,035** | **2** | **2** | **0,01** |
| **8** | **#15 QPT-003** | **Celsius** | **0,06** | **0,08** | **2** | **99999999999999** | **0,01** |

Leitura: **6 das 8 linhas são dado de demonstração/placeholder** — instrumentos chamados
genericamente "Validador", "Qualificador", "Termohigrometro" (sem o padrão de nome `QPx-NNN` usado
no resto do acervo), erro e incerteza zerados. Só as linhas **7** e **8** parecem carregar valores
de certificado real. A linha 7 é exatamente o QPS-001 citado no relatório de 23/09.

### 1.3 Unidades (`engc.calibration.measurement.unit`) — 4 registros

| id | nome | símbolo |
|---|---|---|
| 1 | Celsius | C |
| 2 | Bar | Bar |
| 3 | %UR | %UR |
| 4 | Tempo | s |

(`display_decimals` não existe ainda nesta base — ver seção 0.)

### 1.4 Instrumentos com mais de uma linha na mesma unidade hoje

**Zero.** Nenhum certificado tem duas linhas de incerteza na mesma unidade, e nenhum instrumento
com mais de um certificado válido (só o QPT-014) tem linha de incerteza em nenhum dos três.

**Correção importante em relação à primeira leitura do código:** isso **não** é porque existe uma
trava que impede cadastrar duas linhas na mesma unidade. Em
`models/engc_calibration.py:315-321`, o `_sql_constraints` de unicidade por unidade está **comentado
no código, e mesmo se fosse ativado tem um typo** (`unit_of_measuremen`, faltando o `t`) que o
deixaria inofensivo de qualquer forma:

```python
    # _sql_constraints = [
    #     (
    #         'instrument_id_unit_of_measurement_uniq',
    #         'unique (unit_of_measuremen)',
    #         'A unidade de medida deve ser unica para cada instrumento'
    #     ),
    # ]
```

Ou seja: **hoje já é tecnicamente possível cadastrar 6 linhas de "Tempo" no mesmo certificado** —
nada no banco impede. É exatamente por isso que o usuário conseguiu reproduzir o `Expected
singleton` com um único certificado de 6 pontos (bloqueador citado no enunciado desta tarefa). O
motivo do acervo real estar achatado numa linha por unidade não é uma trava technique, é a
**ausência de `nominal_value`**: não há onde o cadastrante registrar "este erro vale para 60 s"
distinto de "este erro vale para 1200 s", então na prática só se cadastra um valor conservador por
unidade — exatamente como a seção 3.2 do relatório descreve para o QPS-001. O P0 já corrigido na
Fase 0 (`get_certificate_valid()` devolvendo recordset) é uma causa raiz **diferente** do mesmo tipo
de exceção; o bloqueador multiponto propriamente dito (`_search_statistics` /
`onchange_unit_of_measurement`) segue de pé e é estrutural, não observado ainda no acervo cadastrado
— mas comprovadamente reproduzível, como o usuário já demonstrou.

### 1.5 Auditoria de `veff`

Convenção do campo: "para valores infinitos preencha com qualquer número maior que 100". Achados:

- **6 de 8 linhas têm `veff = 0`** — não é a convenção de infinito nem um grau de liberdade finito
  plausível; são as linhas placeholder da seção 1.2, sem significado metrológico.
- **Linha 7 (QPS-001, Tempo) tem `veff = 2`.** Esta é a suspeita registrada no relatório de
  23/09: o certificado real do QPS-001 declara Veff = Infinito (coerente com um orçamento Tipo B
  puro, k = 2,0 fixo), mas o campo guarda 2 — um valor baixo que, se um dia entrar no
  Welch-Satterthwaite da Fase 3, degradaria o *k* efetivo drasticamente. **Confirmado: 1 caso.**
- **Linha 8 (QPT-003, Celsius) tem `veff = 99999999999999`.** Tecnicamente já usa a convenção
  "> 100" para dizer "infinito", mas com uma magnitude absurda (14 dígitos) — tem cara de erro de
  digitação (dedo colado no 9) mais do que de escolha deliberada, ainda que funcionalmente hoje seja
  inofensivo porque `veff` nunca é consumido em cálculo.

Total: **de 8 linhas, 2 usam o campo para algo além de zero; dessas, 1 está provavelmente errada
(QPS-001) e 1 é tecnicamente "certa" mas com valor grotesco (QPT-003).** Isso é evidência direta a
favor da recomendação do relatório de trocar a convenção "> 100" por um booleano explícito antes de
qualquer fórmula consumir `veff` — ver questão em aberto nº 3 adiante.

---

## 2. Desenho

### 2.a Modelo de dados do certificado multiponto

Estender `engc.calibration.instruments.uncertainty.lines` (`CalibrationIntrumentUncertaintyLines`)
com um seletor de modo e os campos de cada modo:

```python
LINE_MODES = [
    ('point', 'Ponto discreto'),
    ('range', 'Faixa'),
    ('formula', 'Fórmula (proporcional à leitura)'),
]

line_mode = fields.Selection(
    LINE_MODES, string='Modo', required=True, default='point',
    help="Como este erro/incerteza se aplica: em um valor nominal exato, "
         "em toda uma faixa, ou como fórmula proporcional à leitura.")

nominal_value = fields.Float(
    string='Valor nominal', digits='Calibration',
    help="Ponto calibrado ao qual este erro/incerteza se refere. "
         "Obrigatório no modo Ponto discreto.")

range_min = fields.Float(string='Faixa — de', digits='Calibration')
range_max = fields.Float(string='Faixa — até', digits='Calibration')
range_min_open = fields.Boolean(
    string='Sem limite inferior',
    help="Quando marcado, ignora range_min — a faixa vale para qualquer "
         "valor abaixo de range_max.")
range_max_open = fields.Boolean(
    string='Sem limite superior',
    help="Quando marcado, ignora range_max — a faixa vale para qualquer "
         "valor acima de range_min.")
# Os dois "open" marcados = faixa totalmente aberta, que é o alvo da
# migração (seção 2.d). Ver nota logo abaixo sobre por que NÃO dá para usar
# range_min/range_max em branco (False) para representar "sem limite".

u_rel = fields.Float(
    string='U relativa (%)', digits='Calibration',
    help="Parcela da incerteza proporcional ao módulo da leitura. "
         "Ex.: 0,5 em '0,5% da leitura'.")
u_abs = fields.Float(
    string='U absoluta', digits='Calibration',
    help="Parcela fixa da incerteza, somada à parcela relativa. "
         "Ex.: 0,02 em '+ 0,02 mV'.")
```

Os campos já existentes (`erro_value`, `uncertainty`, `coverage_factor`, `veff`, `resolution`,
`unit_of_measurement`) continuam existindo e **mudam de leitura conforme o modo**:

| Modo | Campos obrigatórios | O que `erro_value`/`uncertainty`/`resolution`/`coverage_factor`/`veff` significam | Exemplo real |
|---|---|---|---|
| `point` | `nominal_value` | valores exatos naquele ponto | O certificado do padrão de tempo da imagem do usuário: 60 s, 120 s, 480 s, 600 s, 1200 s… cada um com seu erro e ±ITM próprios. **Não existe ainda no acervo cadastrado** — é o caso que motivou toda a Fase 2, hoje achatado em uma linha `range`. |
| `range` | `range_min`/`range_min_open`, `range_max`/`range_max_open` | valores fixos válidos em toda a faixa | **As 8 linhas do acervo atual, tal como estão hoje** — ex. linha 7 (QPS-001, Tempo, incerteza 0,035) e linha 8 (QPT-003, Celsius, incerteza 0,08): nenhuma delas tem noção de ponto, então a migração as expressa como faixa totalmente aberta dos dois lados (seção 2.d). |
| `formula` | pelo menos um de `u_rel`/`u_abs` não-zero | `uncertainty` é ignorado; usa-se `u_abs + (u_rel/100)·\|valor lido\|`. `erro_value`/`resolution`/`coverage_factor`/`veff` continuam fixos, como no modo `range` | Hipotético, do relatório ("U = 0,5% da leitura + 0,02 mV") — **não há exemplo real no acervo atual do labquali.** Comum em certificados de manômetros/transdutores de pressão, nenhum dos quais (QPP-002, QPP-004, QPP-005) tem linha de incerteza cadastrada hoje. |

**Por que `range_min_open`/`range_max_open` como booleanos, e não simplesmente deixar
`range_min`/`range_max` em branco.** No Odoo 16, `fields.Float` não distingue "não preenchido" de
zero: `Float.convert_to_column` faz `float(value or 0.0)`, então um campo `Float` não setado grava
**`0.0`, nunca `NULL`**. Se a semântica de "lado aberto" dependesse de `range_min`/`range_max`
estarem vazios, qualquer linha `range` criada pela UI sem digitar nada ali passaria a valer
"de 0 até X" — um limite inferior fechado em zero, não "sem limite". Os dois booleanos tornam a
intenção explícita e imune a esse comportamento do ORM.

**Constraint de unicidade — por que não dá para ser só `_sql_constraints`.** A mesma semântica
Float-nunca-NULL quebra um índice único ingênuo: um
`unique(certificate, unit_of_measurement, line_mode, nominal_value)` trataria **toda linha `range`
ou `formula`** como tendo `nominal_value = 0.0` (porque esse campo não se aplica a elas e fica no
default), e bloquearia a segunda faixa legítima na mesma unidade — por exemplo, duas linhas `range`
adjacentes tipo "0–100 °C" e "100–200 °C" colidiriam no índice mesmo sem se sobrepor de verdade. Um
índice único **parcial**, restrito a `line_mode = 'point'`, resolve isso — só pontos entram no
índice, então só pontos duplicados são bloqueados no nível de banco:

```python
class CalibrationIntrumentUncertaintyLines(models.Model):
    _name = 'engc.calibration.instruments.uncertainty.lines'
    ...

    def init(self):
        self._cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                engc_calib_uncertainty_line_point_uniq
            ON engc_calibration_instruments_uncertainty_lines
                (certificate, unit_of_measurement, nominal_value)
            WHERE line_mode = 'point'
        """)
```

Isso cobre só a duplicata exata de ponto — defesa em profundidade barata, não a regra completa. A
regra completa (faixas sobrepostas, mais de uma `formula` por unidade, modos misturados) precisa
mesmo de Python, via `@api.constrains('nominal_value', 'range_min', 'range_max', 'range_min_open',
'range_max_open', 'line_mode', 'unit_of_measurement')`, agrupando por `(certificate,
unit_of_measurement)`, que:

1. barra dois `point` com o mesmo `nominal_value` (mensagem amigável; o índice parcial pega o caso
   de corrida/RPC, mas a maioria dos usuários vai ver o erro do Python primeiro);
2. barra duas `range` cujos intervalos se sobrepõem (incluindo os lados marcados como abertos);
3. barra mais de uma `formula` por `(certificate, unit_of_measurement)` — não há necessidade
   metrológica de duas fórmulas concorrentes para a mesma grandeza no mesmo certificado;
4. **barra misturar modos dentro do mesmo `(certificate, unit_of_measurement)`** — ver seção 2.b,
   é uma escolha deliberada de simplificação para esta fase, não uma limitação técnica.

### 2.b Regra de seleção e interpolação

Centralizada num método novo em `CalibrationInstrumentCertificates`, chamado uma vez por linha de
medição (não mais uma vez por bloco):

```python
def _resolve_standard_contribution(self, unit, value):
    """Devolve o dict {erro_value, uncertainty, resolution, coverage_factor, veff}
    do padrão, no valor `value` (grandeza `unit`), a partir das
    uncertainty_lines deste certificado. self é singleton."""
    self.ensure_one()
```

Algoritmo:

1. **Filtrar** `self.uncertainty_lines` pela `unit` pedida. Zero linhas → `ValidationError`
   ("Verifique a unidade de medida selecionada..." — mensagem já existe hoje, mantida).
2. **Modos misturados no mesmo certificado/unidade: proibidos por constraint** (seção 2.a, item 4).
   Logo, dentro deste método, todas as linhas filtradas têm o mesmo `line_mode` — o método nunca
   precisa decidir entre modos concorrentes.
3. **Uma linha só** (é o caso de **100% do acervo real hoje**, seção 1.4): devolve os valores dessa
   linha diretamente, **independente de `value`** — reproduz bit a bit o comportamento atual (que
   também ignora `true_quantity_value` ao escolher a contribuição do padrão). É o caso que a Fase 2
   **não pode regredir**; vira o teste de caracterização mais importante desta fase.
4. **Modo `range`, várias linhas:** encontra a linha cujo `[range_min, range_max]` (tratando
   `range_min_open`/`range_max_open` como "sem limite daquele lado" — não o valor 0.0 de
   `range_min`/`range_max`, ver seção 2.a) contém `value`. Nenhuma contém → `ValidationError`
   ("valor fora da faixa calibrada deste padrão"). Mais de uma contém → não deveria acontecer
   (bloqueado pela constraint de sobreposição), mas defensivamente: pega a de menor `id` e loga um
   warning.
5. **Modo `point`, várias linhas:**
   - ordena as linhas por `nominal_value`;
   - **`value` bate exatamente** (tolerância `abs(value - nominal_value) < 10**-6`, coerente com
     `digits='Calibration'` = 6 casas) num ponto → usa os valores desse ponto;
   - **`value` fora do intervalo `[min(nominal_value), max(nominal_value)]`** → `ValidationError`
     ("fora da faixa calibrada deste padrão — não é possível extrapolar certificado de padrão").
     Decisão explícita do relatório (seção 3.4), mantida aqui.
   - **`value` entre dois pontos consecutivos `P1 < value < P2`:**
     - `erro_value`: interpolação linear entre os dois;
     - `uncertainty`: **o maior** dos dois — conservador, por recomendação do relatório
       (interpolar a incerteza subestimaria o pior caso do intervalo);
     - `resolution`, `coverage_factor`, `veff`: do ponto mais próximo (`P1` se
       `value - P1 <= P2 - value`, senão `P2`); em empate exato de distância, usa o lado de maior
       `uncertainty` (critério conservador, mesmo raciocínio do item anterior).
6. **Modo `formula`, uma linha (é o único caso sensato — item 4 da seção 2.a barra mais de uma):**
   `uncertainty = u_abs + (u_rel / 100.0) * abs(value)`; `erro_value`, `resolution`,
   `coverage_factor`, `veff` vêm fixos da própria linha, sem cálculo. Sem checagem de faixa — é
   próprio de fórmulas não ter limite superior/inferior explícito; se um certificado real precisar
   de limite, isso fica para quando o modo `formula` tiver um caso real (não há nenhum hoje, seção
   1.2/2.a).

### 2.c Onde o cálculo mora

Mover os cinco campos `*_instrument` de `engc.calibration.measurement` (bloco inteiro, hoje
preenchido só por `onchange_unit_of_measurement`) para `engc.calibration.measurement.lines`, como
computados `store=True`, dependentes do `true_quantity_value` **daquela linha**.

**Campos novos em `CalibrationMeasurementLines`:**

```python
standard_certificate_id = fields.Many2one(
    comodel_name='engc.calibration.instruments.certificates',
    compute='_compute_standard_contribution', store=True, readonly=True,
    string='Certificado do padrão usado',
    help="Qual certificado forneceu a contribuição do padrão nesta linha — "
         "rastreabilidade para a Fase 4.")
erro_value_instrument_line = fields.Float(
    string='Erro do padrão', digits='Calibration',
    compute='_compute_standard_contribution', store=True, readonly=True)
uncertainty_instrument_line = fields.Float(
    string='Incerteza do padrão', digits='Calibration',
    compute='_compute_standard_contribution', store=True, readonly=True)
resolution_instrument_line = fields.Float(
    string='Resolução do padrão', digits='Calibration',
    compute='_compute_standard_contribution', store=True, readonly=True)
coverage_factor_instrument_line = fields.Float(
    string='Fator K do padrão',
    compute='_compute_standard_contribution', store=True, readonly=True)
veff_instrument_line = fields.Float(
    string='Veff do padrão',
    compute='_compute_standard_contribution', store=True, readonly=True)
```

Nomeados `*_line` para não colidir com os campos antigos durante a transição e para deixar claro
que agora são por-linha. Aproveita para corrigir de vez o typo pendente `resolutino_instrument`
(item 2 das "Pendências herdadas" do fecho da Fase 0+1) — ele deixa de ser usado; o substituto é
`resolution_instrument_line`.

**Cuidado apurado nas Fases 0/1 e que se aplica de novo aqui, de forma mais séria:** um compute
`store=True` é recalculado em massa por qualquer `-u`, sobre **todos** os registros existentes,
fora do fluxo de um usuário salvando um formulário. Se esse método lançar `ValidationError` — por
exemplo, porque o certificado do padrão daquela linha histórica já venceu, ou porque o valor daquela
linha ficou fora da faixa calibrada depois que alguém editou o certificado — o `-u` inteiro falha.
No acervo consultado isso não aparece só por sorte: `labquali` tem **zero calibrações emitidas**
(fecho da Fase 0+1, "Pergunta em aberto"), mas já tem 3 certificados vencidos (`is_valid=false`,
ids 1, 17, 18) — numa base com calibrações reais e um padrão vencido, a mesma classe de erro que já
mordeu em `_compute_is_valid` ("compute method failed to assign") se repetiria aqui como "compute
method raised". **O compute nunca pode lançar exceção.** Ele registra o problema num campo próprio,
e o bloqueio de verdade acontece em outro lugar — no botão `action_done()` (ação explícita do
usuário, segura de rodar), não durante recompute em lote:

```python
standard_contribution_error = fields.Char(
    compute='_compute_standard_contribution', store=True, readonly=True,
    help="Motivo pelo qual a contribuição do padrão não pôde ser calculada "
         "nesta linha (padrão vencido, fora da faixa calibrada, etc). Vazio "
         "quando o cálculo foi bem-sucedido.")

@api.depends('measurement_id.instrument_id', 'measurement_id.unit_of_measurement',
             'true_quantity_value')
def _compute_standard_contribution(self):
    for rec in self:
        rec.standard_certificate_id = False
        rec.erro_value_instrument_line = 0.0
        rec.uncertainty_instrument_line = 0.0
        rec.resolution_instrument_line = 0.0
        rec.coverage_factor_instrument_line = 2.0
        rec.veff_instrument_line = 0.0
        rec.standard_contribution_error = False
        instrument = rec.measurement_id.instrument_id
        unit = rec.measurement_id.unit_of_measurement
        if not instrument or not unit:
            rec.standard_contribution_error = _('Padrão ou unidade não definidos.')
            continue
        certificate = instrument.get_certificate_valid()
        if not certificate:
            rec.standard_contribution_error = _(
                'Instrumento sem certificado de calibração válido.')
            continue
        try:
            contrib = certificate._resolve_standard_contribution(
                unit, rec.true_quantity_value)
        except ValidationError as exc:
            rec.standard_contribution_error = str(exc)
            continue
        rec.standard_certificate_id = certificate
        rec.erro_value_instrument_line = contrib['erro_value']
        rec.uncertainty_instrument_line = contrib['uncertainty']
        rec.resolution_instrument_line = contrib['resolution']
        rec.coverage_factor_instrument_line = contrib['coverage_factor']
        rec.veff_instrument_line = contrib['veff']
```

`_resolve_standard_contribution` (seção 2.b) continua podendo levantar `ValidationError` — ela é
chamada também fora do compute (ex. num botão "Recalcular", ou validação interativa) onde uma
exceção é o comportamento certo. É só dentro do compute `store=True` que ela é capturada e vira
dado, nunca propagada. `action_done()` em `engc.calibration` ganha uma checagem nova, essa sim
bloqueante:

```python
for line in rec.measurement_ids.mapped('measurement_lines'):
    if line.standard_contribution_error:
        raise ValidationError(_(
            "Linha de medição com problema na contribuição do padrão: %s"
        ) % line.standard_contribution_error)
```

`_compute_statistics` passa a ler `rec.uncertainty_instrument_line` etc. em vez de
`rec.measurement_id.uncertainty_instrument` etc., e ganha essas cinco dependências no
`@api.depends` — resolvendo de quebra o item 6 das "Pendências herdadas" (`@api.depends` sem os
campos `*_instrument`, severidade Alta no relatório original).

**O que acontece com os cinco campos antigos em `measurement`:**
`uncertainty_instrument`, `erro_value_instrument`, `resolution_instrument`,
`coverage_factor_instrument`, `veff_instrument`. Busquei referência a eles no monorepo inteiro,
incluindo `addons/`:

```
grep -rn "uncertainty_instrument\|erro_value_instrument\|resolution_instrument\|coverage_factor_instrument\|veff_instrument\|resolutino_instrument" \
  --include="*.py" --include="*.xml" .
```

Resultado: **os cinco campos do bloco `measurement` só são referenciados dentro do próprio
`engc_os`** (definição em `models/engc_calibration.py`, uso em `views/calibration_views.xml:189-196`
e nos testes de Fase 0/1). A única referência externa encontrada é **`resolutino_instrument`** (o
campo com typo, que fica em `measurement.lines`, não em `measurement`) em
`addons/afr_qualificacao/views/qualificacao_subrecords_views.xml:130` — já catalogada como pendência
2 do fecho da Fase 0+1.

Com isso, **recomendo remover** os cinco campos de `measurement` (não manter como `related`): eles
não têm mais sentido no nível de bloco assim que a contribuição do padrão passa a variar por ponto,
e mantê-los como "resumo" (ex. valor da primeira linha) é mais confuso do que ausente — convidaria
alguém a usá-los de novo achando que ainda valem para o bloco inteiro.

Na view, o grupo `calibration_views.xml:179-199` ("Dados do Instrumento padrão") **não** é removido
inteiro — ele também contém `unit_of_measurement` e `unit_of_measurement_domain` (linhas 183-188),
que continuam em `measurement` (a unidade é escolhida uma vez por bloco, isso não muda). Só os cinco
campos `*_instrument` (linhas 189-196) saem desse grupo; os cinco novos `*_instrument_line`
correspondentes passam a aparecer na `tree` de `measurement_lines` (linhas 203-217), junto de
`erro_value`/`uncertainty`/`veff`. `resolutino_instrument` (o campo com typo em
`measurement.lines`) é removido e sua referência em `afr_qualificacao` precisa ser coordenada — ver
questão em aberto nº 4.

**Efeito colateral que este redesenho introduz e que o relatório original não previu para estes
cinco campos especificamente:** hoje, `uncertainty_instrument` e companhia em `measurement` são
preenchidos por `onchange` — um **snapshot congelado** no momento da criação da linha. Editar o
certificado do padrão depois **não** muda medições já lançadas. Ao virarem `compute` `store=True`
dependente das `uncertainty_lines` do certificado, esse congelamento desaparece: corrigir um erro de
digitação no certificado do padrão passa a **reescrever retroativamente** a contribuição do padrão
(e, em cascata, `uncertainty`/`erro_value`/`veff`) de toda medição histórica que usou aquele padrão
naquele ponto — o mesmo risco de rastreabilidade que a seção 6 do relatório original já apontava
para `uncertainty`/`erro_value`/`veff` em `measurement.lines` (que já são `store=True` hoje), agora
estendido também à entrada do lado do padrão. Não é motivo para recuar do desenho — é exatamente o
comportamento que resolve o bug do RPC zerando tudo (item 2 dos achados do relatório) — mas reforça
por que a ordem 0 → 1 → 2 → **congelamento** → 3 do plano anterior precisa valer também aqui: o
congelamento (Fase 4 do relatório original, mas reordenado para antes da Fase 3) deve cobrir estes
cinco campos novos, não só os três que já existiam.

### 2.d Migração

**Não altera tipo de coluna** (diferente da Fase 1): `line_mode`, `nominal_value`, `range_min`,
`range_max`, `u_rel`, `u_abs` são campos novos, então é só `ADD COLUMN`. O risco da Fase 1
(`double precision` → `numeric`) não se repete aqui.

**Passo 1 — pré-requisito.** Confirmar que a base alvo já rodou as migrações `16.0.1.0.0` e
`16.0.2.0.0` (Fase 0+1). Em `labquali` isso ainda não aconteceu (seção 0) — rodar nessa ordem antes
de tentar a migração da Fase 2, ou a Fase 2 herda os P0 ainda abertos (PDF quebrando no QPT-014).

**Passo 2 — schema.** Bump de `__manifest__.py` para `16.0.3.0.0`. Os campos novos entram com
`line_mode` obrigatório e `default='point'` — isso é o default para **criação de linha nova a
partir de agora**, não para as 8 linhas existentes, que a migração trata explicitamente no passo 3.

**Passo 3 — `migrations/16.0.3.0.0/post-migrate.py`, não destrutivo:**

```python
def migrate(cr, version):
    if not version:
        return
    # As linhas existentes não têm noção de ponto/faixa — hoje se aplicam
    # incondicionalmente a qualquer valor medido na unidade. Isso É uma
    # faixa totalmente aberta: dos dois lados sem limite. Usa os booleanos
    # *_open, não range_min/range_max em branco — Float do Odoo 16 grava
    # "vazio" como 0.0, não NULL (seção 2.a), então marcar só os dois
    # booleanos é a única forma de expressar "sem limite" que sobrevive a
    # uma leitura posterior pelo ORM.
    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET line_mode = 'range',
               range_min = 0.0, range_max = 0.0,
               range_min_open = true, range_max_open = true
         WHERE line_mode IS NULL
    """)
```

Diferente da migração de certificados da Fase 0 (que precisou copiar um `fields.Binary`
attachment-backed via ORM, não SQL cru — pendência 1 do fecho anterior), aqui **todos os campos
tocados são `Float`/`Selection` reais, com coluna própria** — `UPDATE` cru é seguro e não esbarra
naquele problema. Nada é apagado; a migração só preenche colunas novas em linhas existentes.

**Passo 4 — auditoria de `veff`, não automatizada.** A seção 1.5 encontrou 1 `veff` provavelmente
errado (QPS-001 = 2, deveria ser Infinito) e 1 tecnicamente certo mas grotesco (QPT-003 =
99999999999999). **A migração não corrige isso sozinha** — decidir se um certificado real diz
"Infinito" exige olhar o PDF físico, não é dado que a migração possa inferir do banco. Seguindo o
mesmo padrão não-destrutivo da migração da Fase 0 (que logava grupos suspeitos em vez de decidir por
conta própria), o `post-migrate` deve só **logar** as linhas com `0 < veff < 1000` como candidatas a
conferência manual:

```python
    cr.execute("""
        SELECT id, certificate, veff FROM engc_calibration_instruments_uncertainty_lines
         WHERE veff > 0 AND veff < 1000
    """)
    for line_id, certificate_id, veff in cr.fetchall():
        _logger.warning(
            "engc_os: linha de incerteza %s (certificado %s) tem veff=%s — "
            "conferir contra o certificado físico se não deveria ser Infinito "
            "antes da Fase 3 consumir este campo.", line_id, certificate_id, veff)
```

**Passo 5 — verificação pós-migração.** Reexecutar, para cada uma das 8 linhas migradas, o novo
`_resolve_standard_contribution(unit, value)` com **dois valores de `value` bem diferentes** (ex.
0 e 10000) e confirmar que devolve exatamente os mesmos 5 valores nos dois casos — é o teste
funcional de que "faixa totalmente aberta" reproduz "ignora o valor", que é o comportamento atual.

---

## 3. Questões em aberto — decisões do usuário

1. **A base `labquali` ainda não recebeu o `-u` da Fase 0+1.** Antes de sequer planejar a Fase 2
   nessa base, alguém precisa rodar `16.0.1.0.0` + `16.0.2.0.0`. Opções: (a) rodar agora, isolado da
   Fase 2; (b) empacotar as três migrações numa janela só. **Recomendo (a)** — a Fase 0+1 já está
   testada e mergeada há tempo; adiar mais só aumenta o desalinhamento entre código e produção, e o
   PDF do QPT-014 está quebrado ao vivo nessa base agora mesmo.

2. **Restringir a busca da contribuição do padrão a um único certificado (o mais recente, via
   `get_certificate_valid()`) em vez de combinar linhas de todos os certificados válidos do
   instrumento (comportamento atual de `_search_certificates_valid`)?** Hoje, se um instrumento
   tivesse 2 certificados válidos com linhas na mesma unidade, o código as combinaria como se
   fossem uma curva de calibração só — metrologicamente questionável (dois documentos diferentes,
   possivelmente de datas/incertezas diferentes). Opções: (a) manter combinando todos os válidos;
   (b) restringir a um único certificado, o mesmo que o PDF usa. **Recomendo (b)** — consistência
   com a escolha já feita na Fase 0 para o PDF, e evita misturar pontos de dois certificados
   distintos numa mesma interpolação.

3. **Introduzir agora um `veff_infinito` booleano (troca a convenção "> 100"), ou deixar para a
   Fase 3 como o relatório original propunha?** A seção 1.5 achou 2 casos reais que usam (ou
   deveriam usar) essa convenção, um deles provavelmente errado. Como a Fase 2 já mexe na tabela de
   linhas de incerteza para acrescentar `line_mode`, fazer a troca agora evita uma segunda migração
   no mesmo lugar. Opções: (a) incluir `veff_infinito` na Fase 2; (b) esperar a Fase 3.
   **Recomendo (a)** — o custo marginal é baixo (mais uma coluna na mesma migração) e resolve um
   dado já comprovadamente ambíguo antes que a Fase 3 dependa dele.

4. **Coordenar a remoção de `resolutino_instrument` com o submodule `afr_qualificacao`.**
   `addons/afr_qualificacao/views/qualificacao_subrecords_views.xml:130` referencia esse campo
   (`optional="hide"`, então nem aparece por padrão). Opções: (a) renomear/remover no `engc_os` e
   atualizar a view do submodule no mesmo PR de Fase 2, exigindo push coordenado nos dois repos
   (regra do CLAUDE.md: submodule primeiro, bump do pointer depois); (b) manter
   `resolutino_instrument` como campo morto (não computado) só para a view não quebrar, e resolver
   a limpeza depois. **Recomendo (a)** — é uma linha de XML no submodule, baixo custo, e evita
   acumular mais uma pendência "para depois" sobre um campo que já é uma pendência (item 2 do fecho
   anterior).

5. **O que fazer com os 6 certificados sem nenhuma linha de incerteza que hoje bloqueiam qualquer
   medição (eles disparam a `ValidationError` "Verifique a unidade de medida...")?** 18 dos 24
   certificados do acervo estão nessa situação — a maioria dos instrumentos padrão cadastrados
   nunca poderia ser usada numa medição real sem alguém cadastrar linha primeiro. Isso é esperado
   (cadastro incompleto) ou é sinal de que esses instrumentos não são realmente usados como padrão
   em medições? Não é algo que dá para inferir só do banco. **Sem recomendação técnica** — é uma
   pergunta de processo/operação para o usuário confirmar antes de decidir se vale automatizar
   algum alerta de "certificado sem linha de incerteza" na Fase 2.

6. **As 6 linhas de incerteza com valores zerados (Validador/Qualificador/Termohigrometro,
   seção 1.2) são dado de teste esquecido ou registros reais mal preenchidos?** Zero incerteza é
   metrologicamente inválido (equivale a dizer que o padrão é perfeito). Se forem lixo de teste,
   convém removê-las (ou marcar) antes da migração da Fase 2, para não migrarem como "faixa aberta,
   incerteza zero" e conviverem silenciosamente com dado real. Opções: (a) usuário confirma e
   remove/corrige manualmente antes do `-u` da Fase 2; (b) a migração loga essas 6 como suspeitas
   (mesmo padrão do passo 4 da seção 2.d) e segue sem alterar. **Recomendo (b)** como piso mínimo
   sempre, mas a decisão de apagar é do usuário — migração não destrutiva não apaga por conta
   própria.
