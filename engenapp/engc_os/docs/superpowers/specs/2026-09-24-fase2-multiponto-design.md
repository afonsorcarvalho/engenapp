# Fase 2 — Certificado de padrão multiponto — Design

**Data:** 24/09/2026
**Módulo:** `engenapp/engc_os` (monorepo, não submodule), Odoo 16
**Estado de partida:** Fases 0 e 1 entregues e mergeadas em `main-monorepo` (`1204ea0`), módulo `16.0.2.0.0`, 40 testes.

**Documentos relacionados:**
- Análise original: [../../2026-09-23-analise-calibracao-incerteza-precisao.md](../../2026-09-23-analise-calibracao-incerteza-precisao.md) — seção 3 é o esboço que esta spec detalha
- Fecho das Fases 0+1: [../plans/2026-09-23-calibracao-fase0-fase1.md](../plans/2026-09-23-calibracao-fase0-fase1.md)
- Levantamento dos dados reais: [../../2026-09-24-fase2-multiponto-design.md](../../2026-09-24-fase2-multiponto-design.md) — **a Parte 1 (dados) é válida e citada aqui; a Parte 2 (desenho de 3 modos) foi superada por esta spec**

---

## 1. Intenção

Permitir cadastrar o certificado do padrão como ele realmente é — uma tabela de pontos — e fazer cada linha de medição puxar a contribuição de incerteza do ponto correspondente ao valor que está sendo calibrado.

**Critério de sucesso:** cadastrar os 6 pontos do cronômetro QPS-001 (0, 60, 120, 480, 600, 1200 s) sem quebrar nada, e uma medição em 1200 s usar os números de 1200 s, não os de 60 s.

**Fora de escopo, explicitamente:** qualquer correção de fórmula GUM. `_compute_statistics` muda apenas de onde lê seus quatro insumos; a aritmética não muda uma vírgula. As correções metrológicas (divisor Tipo A, Welch-Satterthwaite, *k* derivado) são a Fase 3, e **exigem o congelamento antes** — ver seção 8.

## 2. O bloqueador, confirmado empiricamente

`_search_statistics` filtra `certificates.uncertainty_lines` por unidade e entrega o resultado a `onchange_unit_of_measurement`, que faz `uncertainty_id_line.resolution`. Com mais de uma linha na mesma unidade, o Odoo levanta `Expected singleton`.

Reproduzido em 24/09 num banco de teste: **um único certificado com os 6 pontos em segundos** — que é a definição de certificado multiponto — estoura com os 6 ids na mensagem. Não é que o multiponto esteja mal suportado: ele **inutiliza o padrão** no instante em que o segundo ponto é cadastrado.

Problema estrutural por trás: as cinco contribuições do padrão moram em `engc.calibration.measurement`, que é o **bloco inteiro** de medidas — um escalar para a tabela toda. Cada linha tem seu próprio `true_quantity_value` e precisa dos valores do padrão no ponto dela.

## 3. Decisões tomadas

| # | Decisão | Alternativas descartadas |
|---|---|---|
| D1 | **Só ponto discreto.** Sem modos `faixa`/`fórmula`. | Os três modos — YAGNI: não há certificado assim no acervo, e o modo pode ser acrescentado depois sem refazer nada |
| D2 | **Erro interpolado linearmente, incerteza pelo pior caso** do intervalo | Interpolar a incerteza (subestima); ponto mais próximo (salto descontínuo) |
| D3 | **Bloquear fora da faixa calibrada.** Linha sem ponto (`is_generic`) vale para tudo | Grampear no extremo (declara rastreabilidade inexistente); migrar antigos para faixa explícita (exigiria inventar dado metrológico) |
| D4 | **Painel da medição vira identificação do certificado**; os valores viram colunas opcionais nas linhas | Manter painel com valores do 1º ponto (meia-verdade); remover painel (perde rastreabilidade na tela) |
| D5 | **Campos computados `store=True` na linha** | JSON do orçamento (é Fase 4, e não vira coluna); não-armazenados (quebra rastreabilidade: reimprimir certificado antigo mostraria valores de hoje) |
| D6 | **Interpolar sobre `true_quantity_value`** | Média das leituras (recalcula a cada tecla; equipamento muito fora empurra para fora da faixa) |
| D7 | **Pior caso por `u = U/k`**, com U, k, veff e resolução todos do mesmo ponto | Maior `U` nu (incomparável entre pontos de k diferente) |
| D8 | **Contribuição vem de um único certificado** — o mais recente válido | Juntar todos os válidos (o PDF cita um certificado e usaria números de outro) |
| D9 | **`veff_infinito` booleano entra nesta fase** | Deixar para a Fase 3 (o dado errado continuaria crescendo) |

## 4. Modelo de dados

Em `engc.calibration.instruments.uncertainty.lines`:

```python
is_generic = fields.Boolean(
    string="Vale para toda a faixa", default=True,
    help="Marcado: a linha vale para qualquer valor medido — é o cadastro "
         "antigo, um conjunto de valores por unidade. Desmarcado: a linha "
         "vale para o ponto nominal indicado.")

nominal_value = fields.Float(
    string="Valor nominal", digits='Calibration',
    help="O ponto calibrado a que esta linha se refere. Só tem efeito com "
         "'Vale para toda a faixa' desmarcado.")

veff_infinito = fields.Boolean(
    string="Veff infinito", default=True,
    help="Marcado: graus de liberdade efetivos infinitos, o caso usual em "
         "certificado de padrão. Desmarcado: usar o valor de Veff.")
```

**Por que o booleano `is_generic` e não `nominal_value` vazio:** o certificado do cronômetro **tem um ponto em 0,000 s**. Em Odoo 16 um `Float` nunca grava `NULL` — grava `0.0`. Sem o booleano, "ponto em zero" e "não preenchido" seriam indistinguíveis.

`default=True` em `is_generic` é o que torna a migração de dados desnecessária: as linhas existentes nascem genéricas e se comportam exatamente como hoje.

### Constraints

Três `@api.constrains`. Não dá para usar `_sql_constraints`: unicidade condicional exige índice parcial, que o Odoo não expõe.

1. **Não misturar** genérica com pontos na mesma `(certificate, unit_of_measurement)` — seria ambíguo qual vence
2. **Não repetir** `nominal_value` dentro da mesma `(certificate, unit_of_measurement)`, comparando com `float_compare` na precisão `Calibration`
3. **No máximo uma** genérica por `(certificate, unit_of_measurement)`

A constraint 3 é a que fecha o bug: hoje nada impede duas linhas na mesma unidade. Depois dela, ou a unidade tem uma genérica só, ou tem N pontos distintos — e o seletor resolve ambos.

> Nota apurada no levantamento: a `_sql_constraints` de unicidade que existe hoje no modelo está **comentada e com typo** (`unit_of_measuremen`). Remover o bloco morto junto.

### View

A tabela de linhas do certificado ganha `is_generic`, `nominal_value` e `veff_infinito`, e passa a ordenar por `unit_of_measurement, nominal_value`.

## 5. Seleção e interpolação

Método puro em `engc.calibration.instruments.certificates`:

```python
def _select_uncertainty_at(self, unit, value):
    """Contribuições do padrão na grandeza `unit`, no ponto `value`.

    NUNCA levanta exceção — ver seção 6. Devolve sempre um dict com
    'status'; os valores numéricos vêm zerados quando status != 'ok'.
    """
```

Algoritmo:

1. Filtra as linhas pela unidade. Nenhuma → `status='sem_unidade'`.
2. Existe genérica? Devolve ela, `status='ok'`. **Todo o acervo atual cai aqui** e sai idêntico ao de hoje.
3. Ordena os pontos por `nominal_value`. Fora de `[primeiro, último]` → `status='fora_faixa'`, com a faixa no campo de mensagem.
4. Coincide com um ponto (`float_compare` na precisão `Calibration`)? Devolve ele inteiro.
5. Entre dois pontos:
   - `erro` = interpolação linear entre os dois
   - escolhe o ponto de maior `u = uncertainty / coverage_factor`; `uncertainty`, `coverage_factor`, `veff`, `veff_infinito` e `resolution` vêm **todos dele**

O passo 5 tem dois cuidados que importam:

- **`u = U/k`, não `U` nu.** Um ponto com U=0,040 e k=2,0 e outro com U=0,050 e k=2,5 têm o mesmo u=0,020. Escolher pelo U escolheria o segundo achando que é pior.
- **Valores do mesmo ponto.** Misturar U de um ponto com k de outro produz uma incerteza padrão que não existe em certificado nenhum.

Retorno:

```python
{'status': 'ok', 'erro_value': …, 'uncertainty': …, 'coverage_factor': …,
 'veff': …, 'veff_infinito': …, 'resolution': …, 'source_line_id': …,
 'message': ''}
```

`source_line_id` registra qual linha do certificado sustentou a medição — rastreabilidade barata, e embrião do orçamento JSON da Fase 4.

**Qual certificado (D8):** o seletor roda sobre `instrument.get_certificate_valid()` — o certificado válido mais recente, o mesmo que o PDF cita desde a Fase 0. `_search_certificates_valid()` deixa de juntar todos os válidos.

## 6. Onde o cálculo mora, e como falha

Em `engc.calibration.measurement.lines`, nove campos computados com `store=True`:

```python
standard_uncertainty     = Float(digits='Calibration')
standard_erro            = Float(digits='Calibration')
standard_resolution      = Float(digits='Calibration')
standard_coverage_factor = Float()
standard_veff            = Float()
standard_veff_infinito   = Boolean()
standard_line_id         = Many2one('engc.calibration.instruments.uncertainty.lines')
standard_status          = Selection([('ok', 'OK'),
                                      ('sem_certificado', 'Sem certificado válido'),
                                      ('sem_unidade', 'Unidade não consta do certificado'),
                                      ('fora_faixa', 'Fora da faixa calibrada')])
standard_message         = Char()
```

Um só `_compute_standard_contribution`, com
`@api.depends('true_quantity_value', 'measurement_id.instrument_id', 'measurement_id.unit_of_measurement')`.

### O compute é total: nunca levanta

Este é o requisito mais importante desta seção, e a razão de o seletor devolver `status` em vez de levantar.

Um compute `store=True` que levanta exceção **derruba qualquer `-u` do módulo**, porque o upgrade recomputa os campos de todas as linhas existentes. Uma única linha com certificado vencido, ou fora de faixa, bastaria para impedir toda atualização futura do módulo — inclusive as correções da Fase 3.

Quando não resolve, o compute grava zeros, `standard_line_id` vazio, e o `standard_status`/`standard_message` correspondentes.

### Onde o bloqueio acontece

Dois lugares, nenhum no caminho do compute:

- **`onchange` na linha** — retorno imediato na tela para o técnico
- **`action_done()`** — recusa concluir a calibração com qualquer linha em status diferente de `ok`, nomeando as linhas em falta

### `_compute_statistics`

Passa a ler `rec.standard_*` em vez de `rec.measurement_id.*_instrument`. **A aritmética não muda.** Os quatro testes de caracterização que fixam os números têm de continuar dando exatamente os mesmos valores — com linha genérica, o resultado é idêntico ao de hoje. São eles a rede de segurança desta mudança.

### Os cinco campos antigos

`uncertainty_instrument`, `erro_value_instrument`, `coverage_factor_instrument`, `resolution_instrument` e `veff_instrument` são **removidos** de `engc.calibration.measurement`.

Verificado por grep no monorepo inteiro: **nenhum consumidor externo**. As únicas referências são a view do próprio `engc_os`, os testes do próprio módulo, e `_compute_statistics`. (A única referência externa a campo desta família é `resolutino_instrument` em `addons/afr_qualificacao/views/qualificacao_subrecords_views.xml:130`, que é outro campo, na linha, e **não é tocado** nesta fase.)

Remover campo `store=True` deixa coluna órfã no banco. Sem perda de dado, sem erro.

O painel "Dados do Instrumento padrão" na view da medição passa a mostrar **qual certificado está sendo usado** — número, validade, faixa calibrada — informação que hoje não aparece em lugar nenhum. Os valores viram colunas `optional="hide"` na tabela de linhas.

## 7. Migração

**Nenhuma linha de dado precisa mudar.** `is_generic` e `veff_infinito` nascem com `default=True`, e o `_auto_init` do Odoo preenche coluna nova a partir do default — foi o comportamento observado com `display_decimals` na Fase 1.

Ainda assim o script existe, idempotente, pelo mesmo motivo da Fase 1: rede para restauração parcial ou coluna criada por DDL manual.

```
UPDATE ... SET is_generic = true    WHERE is_generic IS NULL;
UPDATE ... SET veff_infinito = true WHERE veff_infinito IS NULL;
```

> **O plano tem de verificar esse backfill empiricamente**, não assumir. Duas suposições dessa família saíram erradas nas fases anteriores (o tipo de coluna `numeric(16,6)` e o próprio mecanismo do `_auto_init`).

### O `veff` do acervo (D9)

O levantamento achou, nas 2 linhas com dado real:

| Instrumento | Unidade | `veff` no banco | Certificado físico |
|---|---|---|---|
| QPS-001 | Tempo | `2` | declara **Infinito** |
| QPT-003 | Celsius | `99999999999999` | infinito (convenção "> 100") |

A migração converte **apenas o caso inequívoco**: `veff > 100` → `veff_infinito = True`, `veff = 0`.

**O QPS-001 não é convertido em silêncio.** `veff = 2` é um valor finito legítimo do ponto de vista do modelo; só o papel diz que está errado. A migração deixa como está e **loga um WARNING** nomeando as linhas com `veff` finito, para conferência manual contra o certificado.

Sem `ALTER TABLE` de tipo nesta fase, diferente da Fase 1.

## 8. Ordem das fases

O relatório original lista o congelamento como Fase 4. **Está errado. A ordem é 0 → 1 → 2 → congelamento → 3.**

`uncertainty`, `erro_value` e `veff` em `measurement.lines` são `compute` com `store=True`, e esta fase acrescenta mais nove campos da mesma natureza. No primeiro `-u` depois de corrigir o divisor Tipo A, todo o histórico é recalculado e certificados já emitidos são reescritos em silêncio.

## 9. Testes

Os 40 testes atuais continuam verdes, com as exceções deliberadas da seção 6. Cinco frentes novas:

1. **Seleção** — ponto exato; entre dois pontos; fora da faixa; linha genérica (100% do acervo atual); unidade ausente do certificado
2. **Constraints** — misturar genérica com ponto; repetir `nominal_value`; duas genéricas
3. **O compute não levanta** — linha com certificado vencido, forçar recompute, afirmar que não estoura e que `standard_status` ficou preenchido. É o teste que protege todo `-u` futuro
4. **Bloqueio no lugar certo** — `action_done()` recusa com linha fora de faixa; o `onchange` avisa
5. **Aceitação** — cadastrar os 6 pontos do cronômetro e medir em três valores distintos (um sobre um ponto, um entre dois, um fora da faixa), conferindo o ponto que cada linha puxou

Baseline a preservar: 919 testes dos módulos dependentes, com a única falha pré-existente conhecida (`afr_qualificacao ... test_fleet_single_logger_two_temp_standards`).

## 10. Pendências operacionais (fora do escopo desta fase)

Apuradas no levantamento, na mesa do usuário:

1. **O `labquali` ainda roda o `engc_os` de antes das Fases 0 e 1** — os campos novos não existem no schema de lá. O PDF do QPT-014 está quebrado ao vivo naquela base. O merge não chega sozinho; alguém precisa rodar o `-u`.
2. **18 dos 24 certificados não têm nenhuma linha de incerteza.** Esses padrões já bloqueiam qualquer medição hoje.
3. **6 das 8 linhas existentes parecem dado de teste** (erro e incerteza zerados, nomes fora do padrão `QPx-NNN`).
4. **O typo `resolutino_instrument`** continua, à espera de mudança coordenada com a view do submodule `afr_qualificacao`.
