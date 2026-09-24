# Análise — Calibração de instrumentos no `engc_os`: erro, incerteza e precisão numérica

**Data:** 23/09/2026
**Escopo:** `engenapp/engc_os` — modelos `engc.calibration.*`, views de calibração e o template do certificado.
**Natureza:** relatório de análise. Nenhum código foi alterado.
**Verificação:** as afirmações sobre comportamento em execução foram checadas contra a base
`odoo-labquali` (`engc_os` 16.0.0.1, instalado), não só por leitura de código.

---

## 1. Sumário executivo

Você levantou duas questões. As duas são legítimas, e a investigação do código mostrou que
ambas esbarram no mesmo ponto: **o módulo modela o certificado do padrão como um único conjunto
de valores, quando na prática ele é uma tabela de pontos.**

**Questão 1 — vários valores por ponto de medição.** Hoje é literalmente impossível cadastrar
um certificado multiponto. O modelo permite uma linha de incerteza por unidade de medida, e o
código que busca essa linha (`_search_statistics`) faz `uncertainty_id_line.resolution` num
recordset — se houver duas linhas com a mesma unidade (que é exatamente o caso de um certificado
com 6 pontos em segundos), o Odoo levanta `Expected singleton`. A solução exige acrescentar o
valor nominal do ponto ao cadastro e interpolar a contribuição do padrão **por linha de medição**,
no valor medido daquela linha.

**Questão 2 — casas decimais.** Boa notícia primeiro: **nenhum dado foi perdido.** Os campos são
`fields.Float` sem `digits`, o que no Odoo gera coluna PostgreSQL `double precision`. O `60,053`
da sua imagem está gravado inteiro no banco; o que trunca é só a exibição (padrão de 2 casas na
web) e seis `"precision": 2` escritos à mão no QWeb do certificado. É um ajuste de apresentação,
não uma migração de dados.

**O que a investigação encontrou além do pedido — e que muda a ordem de prioridade:**

1. **O PDF do certificado quebra para instrumentos com mais de um certificado válido — confirmado
   na base `odoo-labquali`.** `get_certificate_valid()` devolve um *recordset*, e o template faz
   `t-field` em cima dele (linhas 137–139). O instrumento **QPT-014 – Registrador Digital** tem
   hoje **três certificados válidos** (R1661/2025, R1236/2026 e R1236/2026 – Inglês): qualquer
   calibração que o use como padrão levanta `Expected singleton` ao gerar o PDF. **P0, com
   reprodutor pronto.**
2. **As contribuições do padrão são preenchidas só por `onchange`.** Um registro criado por RPC,
   importação ou `create()` recebe **0,0** em incerteza, erro e resolução do padrão — e o sistema
   emite silenciosamente uma incerteza otimista, sem erro nenhum. Este repositório já faz escrita
   por RPC a partir do PWA; não é hipótese remota.
3. **`is_valid` quebra em acesso direto — corrigido em 23/09/2026, era mais grave do que escrevi aqui
   primeiro, mas não tão espalhado quanto eu disse na primeira correção.** O método
   `_compute_is_valid` não atribui o campo (só faz `return`). Minha verificação inicial foi por RPC
   (`search_read`), que devolveu valores corretos, e eu concluí "funciona por acidente, não é P0".
   **Estava brando demais.** Ao escrever os testes, o acesso direto ao atributo (`rec.is_valid`)
   levantou `ValueError: Compute method failed to assign` — e é exatamente isso que
   `get_certificate_valid()` faz, via `self.certificate_ids.filtered(lambda rec: rec.is_valid)`.
   Ou seja, o método já levantava exceção em qualquer recordset **quando `engc_os` roda sozinho**:
   **também era P0**, real, e alguém já tinha esbarrado nele antes de mim. `afr_qualificacao`
   (`addons/afr_qualificacao/models/calibration_instruments.py:122-135`) já carrega um hotfix que
   sobrescreve `_compute_is_valid` com a mesma implementação corrigida — o docstring de lá é
   explícito: "o compute `_compute_is_valid` no engc_os não itera self nem atribui valor — gera
   CacheMiss/ValueError em qualquer leitura". É esse override que fazia a leitura por RPC contra
   `labquali` (que tem `afr_qualificacao` instalado) devolver valor correto — não foi o `read()`
   "resolvendo por fallback" como eu descrevi antes: era outro código, num módulo diferente,
   silenciosamente mascarando o bug. Em qualquer base SEM `afr_qualificacao` instalado, o bug batia
   direto. Com o compute corrigido no próprio `engc_os` (Task 2 desta fase), o override em
   `afr_qualificacao` virou código morto duplicado — removê-lo é mudança em submodule e fica para
   uma fase posterior.
4. **Três colunas fixas de leitura.** Se o técnico preencher duas, a terceira entra como `0,0` no
   `mean()` e no `stdev()`. A média e o erro saem errados com aparência de corretos. Note que o
   certificado da sua imagem tem **uma leitura por ponto**, ITM constante de 0,035 e Veff = Inf —
   ou seja, o orçamento real de vocês é Tipo B puro, sem termo de repetitividade. O código atual
   não consegue expressar isso.

Ordem sugerida de ataque: **bugs P0 → precisão decimal (barato, alto impacto visível) →
certificado multiponto → correções do GUM → congelamento dos valores emitidos.**

---

## 2. Como o módulo funciona hoje

O encadeamento dos modelos em [models/engc_calibration.py](../models/engc_calibration.py):

```
engc.calibration                          (a calibração em si)
 └─ engc.calibration.measurement          (um bloco de medidas; escolhe 1 padrão + 1 unidade)
     └─ engc.calibration.measurement.lines (uma linha por ponto: 3 leituras, erro, incerteza, k, Veff)

engc.calibration.instruments              (o padrão)
 └─ ...instruments.certificates           (certificado do padrão)
     └─ ...uncertainty.lines              (HOJE: uma linha por unidade de medida)
```

O cálculo vive em `_compute_statistics` ([linha 449](../models/engc_calibration.py#L449)):

```python
combined_uncertainty = sqrt((stdev(values)/2)**2
        + (uncertainty_instrument/k_instrument)**2
        + (erro_instrument/sqrt(3))**2
        + (resolution_instrument/sqrt(12))**2
        )
record.uncertainty = record.coverage_factor * combined_uncertainty
record.veff = 3*(combined_uncertainty/(stdev(values)/2))**4
```

A estrutura geral está certa (soma quadrática de contribuições, expansão por *k*). Os detalhes
têm problemas, tratados na seção 5.

---

## 3. Questão 1 — certificado do padrão com vários pontos

### 3.1 O problema

O certificado do seu padrão de tempo tem uma linha por ponto: 60 s, 120 s, 480 s, 600 s, 1200 s…
cada uma com seu erro, sua ±ITM, seu *k* e seu Veff. O modelo
`engc.calibration.instruments.uncertainty.lines` ([linha 241](../models/engc_calibration.py#L241))
tem `erro_value`, `uncertainty`, `coverage_factor`, `veff`, `resolution` e
`unit_of_measurement` — **mas não tem o valor nominal do ponto.** Não há onde registrar que
"este erro de −0,002 s vale para 60 s".

E o consumidor desses dados agrava: em `_search_statistics`
([linha 376](../models/engc_calibration.py#L376)) o filtro é só por unidade, e logo depois
`onchange_unit_of_measurement` faz `uncertainty_id_line.resolution` — acesso a campo de um
recordset. Com um ponto, funciona. Com seis pontos em segundos, `Expected singleton`.

Há ainda um erro de arquitetura mais sutil: as contribuições do padrão
(`uncertainty_instrument`, `erro_value_instrument`, `resolution_instrument`,
`coverage_factor_instrument`, `veff_instrument`) moram em `engc.calibration.measurement`, que é
**um bloco inteiro de medidas** — um escalar só para a tabela toda. Não existe lugar onde guardar
"a incerteza do padrão vale X no ponto de 60 s e Y no de 1200 s". Acrescentar uma coluna de ponto
no certificado não resolve nada sozinho: **a contribuição do padrão precisa ser calculada por
linha de medição, no `true_quantity_value` daquela linha.**

### 3.2 A evidência na sua própria base

Consultei a base `odoo-labquali` (engc_os instalado, v16.0.0.1). O padrão de tempo da sua imagem
está lá: **QPS-001 – Cronômetro Digital**, certificado **R0712/2026**, válido até 02/06/2027. Ele
tem **exatamente uma** linha de incerteza:

| unidade | erro | incerteza | k | Veff | resolução |
|---|---|---|---|---|---|
| Tempo | 0,01 | **0,035** | **2,0** | 2 | 0,01 |

A incerteza 0,035 e o k = 2,0 batem com a coluna **±ITM** da sua imagem — mas os **seis pontos
(60 s, 120 s, 480 s, 600 s, 1200 s…) foram achatados numa linha só**, e o erro virou um único
0,01 conservador em vez dos valores por ponto (−0,002, −0,003, 0,000…). Não foi descuido de quem
cadastrou: **o modelo não oferece outra opção.** É a confirmação prática do diagnóstico.

> ⚠️ **Risco de migração descoberto de quebra:** esse registro tem **`veff = 2`**, quando o
> certificado real declara **Inf**. O campo pede "para valores infinitos preencha com qualquer
> número maior que 100" — convenção confusa, e o dado já está errado. Hoje isso é inofensivo
> porque `veff_instrument` **nunca é usado** no cálculo. Mas na Fase 3, ao fazer o
> Welch-Satterthwaite consumir esse campo, um `veff = 2` degradaria o *k* drasticamente. **Antes
> da Fase 3 é obrigatório auditar e recadastrar os Veff existentes** — e trocar a convenção
> "> 100" por um booleano explícito `veff_infinito`.

### 3.3 O modelo proposto

Acrescentar ao `uncertainty.lines` um campo de **valor nominal** e um seletor de modo, cobrindo as
três formas em que certificados reais são emitidos:

| Modo | Campos | Exemplo típico |
|---|---|---|
| `point` — ponto discreto | `nominal_value` | o seu certificado de tempo: 60 s, 120 s, 480 s… |
| `range` — faixa | `range_min`, `range_max` | "de 0 a 100 °C: U = 0,15 °C" |
| `formula` — proporcional | `u_rel` (% da leitura), `u_abs` (parcela fixa) | "U = 0,5 % da leitura + 0,02 mV" |

> ⚠️ **Correção de 23/09/2026, descoberta na implementação:** qualquer migração que pretenda copiar
> o arquivo de um certificado **não pode usar SQL cru**. `certificate_calibration` — e todo campo
> `fields.Binary` sem `attachment=False` — é guardado em `ir_attachment`, **sem coluna na tabela**.
> Um `SELECT certificate_calibration` falha com `column does not exist`. A cópia do binário tem de
> passar pelo ORM; SQL cru só serve para detectar os grupos de duplicatas, que usam colunas reais
> (`instrument_id`, `date_calibration`, `validate_calibration`).

Campos novos sugeridos na linha do certificado:

```
nominal_value        Float   valor nominal do ponto calibrado
line_mode            Selection('point', 'range', 'formula')
range_min/range_max  Float   (modo range)
u_rel / u_abs        Float   (modo formula)
```

Com `nominal_value` preenchido, a constraint de unicidade passa a ser
`(certificate, unit_of_measurement, nominal_value)` em vez de proibir repetição de unidade.

### 3.4 Como obter a incerteza do padrão num ponto qualquer

O ponto medido raramente coincide com um ponto do certificado. Regra recomendada, alinhada com a
prática de laboratórios acreditados:

- **Erro (tendência):** interpolação linear entre os dois pontos que cercam o valor medido.
- **Incerteza (U):** **o maior** dos dois pontos que cercam — conservador. Interpolar a incerteza
  subestima; laboratórios acreditados usam o pior caso do intervalo.
- **Resolução, *k*, Veff:** do ponto mais próximo.
- **Fora da faixa calibrada:** **levantar `ValidationError`.** Extrapolar certificado de padrão não
  é defensável tecnicamente nem perante auditoria. Melhor travar do que emitir número inválido.

Nota importante sobre o vocabulário, para o relatório não confundir quem for ler depois: o
**erro do padrão** (tendência do instrumento de referência, vinda do certificado dele) e a coluna
**ERRO** da sua imagem (que é `VIT − VR`, o erro do equipamento sob calibração) são grandezas
diferentes. A primeira entra no orçamento de incerteza; a segunda é o resultado da calibração.

### 3.5 Onde o cálculo deve morar

Mover as contribuições do padrão de `engc.calibration.measurement` para
`engc.calibration.measurement.lines`, **como campos computados** — e não mais como *snapshot* de
`onchange`. Isso resolve de uma vez três coisas: a interpolação por ponto, o bug do RPC que
zera tudo, e a não-propagação quando o certificado do padrão é corrigido depois.

---

## 4. Questão 2 — casas decimais

### 4.1 Diagnóstico

Todos os campos numéricos da cadeia de calibração são `fields.Float` sem `digits`. No Odoo isso
significa coluna `double precision` no PostgreSQL. **Os dados estão íntegros.** O que trunca:

- **Na interface:** sem `digits`, o widget web usa 2 casas por padrão. Você digita `60,053`,
  aparece `60,05`.
- **No certificado:** seis ocorrências de `t-options='{"widget": "float", "precision": 2}'` em
  [reports/calibration_certificate_template.xml](../reports/calibration_certificate_template.xml),
  linhas 170–197, fixadas no XML.

### 4.2 Proposta

**a) Precisão de armazenamento/edição — um `decimal.precision` dedicado.**

```xml
<record id="decimal_calibration" model="decimal.precision">
    <field name="name">Calibration</field>
    <field name="digits">6</field>
</record>
```

E aplicar `digits='Calibration'` em todos os Float da cadeia: `true_quantity_value`, as três
leituras, `measurement_quantity_value_mean`, `erro_value`, `uncertainty`, `resolution`, e os
correspondentes no certificado do padrão.

> ⚠️ **Efeito colateral a planejar:** no Odoo, `Float` **com** `digits` muda o tipo da coluna de
> `double precision` para `numeric`. Ao atualizar o módulo, o ORM roda um `ALTER TABLE` e os
> valores históricos são arredondados para a escala escolhida. Com 6 casas, nada do seu uso real
> se perde — mas é uma alteração de esquema, e merece backup do banco antes do `-u`.

**b) Precisão de exibição — por unidade de medida.**

Uma precisão global não serve para um módulo que mede segundos (3 casas), temperatura (2 casas) e
pressão. E o `digits=` do Odoo não varia por registro. O caminho prático é: digits global generoso
(6) para armazenar, e **formatação por unidade** na apresentação. Acrescentar em
`engc.calibration.measurement.unit` ([linha 598](../models/engc_calibration.py#L598)):

```
display_decimals = fields.Integer('Casas decimais', default=3)
```

e no QWeb trocar o `2` fixo por:

```xml
<span t-field="l.erro_value"
      t-options-widget="'float'"
      t-options-precision="l.unit_of_measurement.display_decimals"/>
```

**c) Arredondamento metrológico.** O GUM e o DOQ-CGCRE-008 pedem que a incerteza expandida seja
declarada com **2 algarismos significativos** e que o valor medido seja arredondado à mesma casa
decimal da incerteza. Isso é diferente de "mostrar N casas" — é uma regra que depende da magnitude
de cada valor. Convém implementar como *helper* aplicado na emissão do certificado, não como
formatação de campo.

---

## 5. Revisão do cálculo de incerteza (GUM)

Esta seção lista divergências em relação ao GUM / ISO GUM 1995 / INMETRO DOQ-CGCRE-008. Recomendo
conferir cada fórmula contra o documento antes de implementar — abaixo está o raciocínio, não uma
autoridade.

### 5.1 Repetitividade com divisor errado

```python
(stdev(values)/2)**2
```

A incerteza padrão Tipo A da média de *n* leituras é `s/√n`, não `s/2`. Com n = 3 o divisor
correto é √3 ≈ 1,732. Como `s/2 = 0,500·s` e `s/√3 = 0,577·s`, o código **subestima o termo Tipo A
em ~13 %**. Não é um erro conservador: a incerteza declarada sai **menor** do que deveria, o que é
o pior lado para errar, e indefensável em auditoria.

### 5.2 Graus de liberdade efetivos (Welch-Satterthwaite) incorretos

```python
record.veff = 3*(combined_uncertainty/(stdev(values)/2))**4
```

A fórmula é `ν_eff = u_c⁴ / Σ(uᵢ⁴/νᵢ)`. O código usa constante 3 num lugar onde deveria haver o
somatório sobre todas as contribuições com graus de liberdade finitos. Para n = 3 leituras,
ν_A = n − 1 = 2. E o `veff_instrument`, que existe no cadastro do certificado, **nunca é usado** —
é exatamente ele que deveria entrar no denominador como `u_cert⁴/ν_cert` quando finito.
Reconstruir o denominador como somatório resolve os dois problemas.

### 5.3 *k* é digitado, não derivado

`coverage_factor` é campo de entrada com default 2,0. O procedimento GUM correto é: calcular
ν_eff → consultar a t-Student para 95,45 % → obter *k*. Hoje o Veff é calculado e **ignorado**, e o
*k* é chutado. Vale implementar a tabela de t-Student (é uma tabela pequena, ~15 linhas), com
ν_eff → ∞ resultando em k = 2,00 — que é o caso do seu certificado da imagem.

Vale notar que o template já trata a convenção do infinito (`t-if="l.veff >= 100.0"` → imprime
"Infinito"), coerente com o *help* do campo no cadastro do padrão. Só falta o cálculo produzir
esse valor em vez de cair no `except` e devolver 0.

### 5.4 Resolução do equipamento sob calibração está faltando

O orçamento inclui `resolution_instrument/sqrt(12)` — a resolução do **padrão**. Está correto
(meia largura r/2 sobre distribuição retangular: `(r/2)/√3 = r/√12`). Mas **a resolução do
equipamento que está sendo calibrado não entra em lugar nenhum** — e em muitas calibrações ela é o
termo dominante. Se o timer sob teste mostra 3 casas, a resolução dele é 0,001 s e contribui
0,000289 s. Falta um campo de resolução no equipamento (ou na linha de medição).

### 5.5 Tendência do padrão — escolha a documentar, não bug

```python
(erro_instrument/sqrt(3))**2
```

Isto trata o erro do padrão como tendência **não corrigida**, com distribuição retangular de meia
largura igual ao erro. É um tratamento defensável e usado na prática. A alternativa preferida pelo
GUM é **corrigir a leitura** por −erro e usar apenas U_cert. Recomendo tornar isso uma opção
explícita e documentada no procedimento de medição (`bias_treatment`: `correct` / `include`), em
vez de ficar implícito no código.

### 5.6 Leituras fixas em três — e a impossibilidade do Tipo B puro

`measurement_quantity_value_1/2/3` são três colunas fixas. Duas consequências:

- Preencher só duas leituras faz a terceira entrar como `0,0` no `mean()`/`stdev()`. Média e erro
  saem **silenciosamente errados**.
- O modo do seu certificado real — **uma leitura por ponto, sem repetitividade** — não existe.
  Nesse caso `stdev([0,0,0]) = 0`, o Veff divide por zero, cai no `except` nu e vira `0`, impresso
  como `0,00` onde deveria constar `Inf`.

Proposta: substituir as três colunas por um `One2many` de leituras (n variável) ou, se quiser
manter a simplicidade da tabela editável, adotar um campo `reading_count` e ignorar as posições
não preenchidas. E suportar explicitamente `n = 1` → orçamento Tipo B puro, sem termo de
repetitividade, ν_eff = ∞, k = 2.

Um detalhe menor no mesmo método: há um `for record in rec` aninhado dentro de `for rec in self`
([linha 449](../models/engc_calibration.py#L449)), resquício de refatoração. Funciona por acidente
porque `rec` é singleton, mas a variável `values` vaza do laço.

---

## 6. Rastreabilidade: congelar o que já foi emitido

`uncertainty`, `erro_value`, `veff` e `measurement_quantity_value_mean` são campos computados com
`store=True`. **No momento em que você corrigir `/2` para `/√n` ou consertar o Welch-Satterthwaite,
todos os registros históricos serão recalculados** — reescrevendo silenciosamente certificados já
emitidos e entregues a clientes.

Num fluxo com pretensão de ISO/IEC 17025, isso não é um inconveniente, é um problema de
conformidade: o PDF no arquivo do cliente deixa de bater com o banco.

Recomendação:

1. Trocar os computados por campos comuns, recalculados por `onchange`, por botão "Recalcular" e
   obrigatoriamente antes de `action_done`. Dá controle explícito sobre quando o número muda.
2. Gravar o **orçamento completo** num campo JSON na linha de medição: cada contribuição, seu
   valor, distribuição, divisor e graus de liberdade. Isso permite (a) imprimir a tabela de
   orçamento de incerteza no certificado, que auditoria costuma exigir, e (b) provar depois como
   aquele número foi obtido.
3. Bloquear edição de linhas quando `calibration_id.state == 'done'` (hoje a view protege, o
   modelo não).

---

## 7. Bugs que impedem funcionamento hoje

| # | Local | Problema | Severidade |
|---|---|---|---|
| 1 | [`get_certificate_valid`](../models/engc_calibration.py#L176) | Devolve *recordset*; o template faz `t-field` no resultado → `Expected singleton`. **Confirmado em `odoo-labquali`:** QPT-014 tem 3 certificados válidos. O `TODO` do código já reconhece. | **P0** |
| 2 | [`_compute_is_valid`](../models/engc_calibration.py#L221) | Não atribui o campo (só `return`) e faz `if self.x` em recordset. **Correção 23/09: era P0, não "baixa", em qualquer base sem `afr_qualificacao` instalado.** Acesso direto (`rec.is_valid`, que é o que `get_certificate_valid()` faz via `.filtered`) levantava `ValueError: Compute method failed to assign`. Em `labquali` o bug ficava mascarado por um hotfix já existente em `afr_qualificacao/models/calibration_instruments.py:122-135` que sobrescreve o compute — não por fallback do `read()`. Esse override agora é código morto duplicado (remoção fica para fase posterior, é mudança em submodule). | **P0** (corrigido) |
| 3 | [`_search_statistics`](../models/engc_calibration.py#L376) | `uncertainty_id_line.resolution` em recordset multi-linha → `Expected singleton` assim que houver certificado multiponto. É o bloqueio da questão 1. | **P0** |
| 4 | [`onchange_unit_of_measurement`](../models/engc_calibration.py#L398) | Única via de preenchimento das contribuições do padrão. Criação por RPC/import → tudo 0,0 → incerteza otimista **sem erro visível**. | **Alta** |
| 5 | [`_compute_statistics`](../models/engc_calibration.py#L449) | `@api.depends` não inclui os campos `*_instrument`; alterar o padrão não recalcula as medidas. | **Alta** |
| 6 | [`create`](../models/engc_calibration.py#L96) | Chama `self.action_confirmed()` (recordset vazio, nível de modelo) e usa `self.id` em vez de `result.id`; falta `@api.model_create_multi`. | Média |
| 7 | [`_check_date_calibration`](../models/engc_calibration.py#L61) | Compara com `date_next_calibration` sem checar `False` → `TypeError`. | Média |
| 8 | [`_compute_instrument_id_domain`](../models/engc_calibration.py#L320) | Condiciona ao próprio valor (`if rec.instrument_id_domain`) → domínio nasce vazio; o padrão não fica restrito aos da calibração. | Média |
| 9 | [linha 432](../models/engc_calibration.py#L432) | Bloco solto `related='field_name', readonly=True, store=True` no corpo da classe — atributos órfãos, sem campo. | Baixa |
| 10 | [linha 446](../models/engc_calibration.py#L446) | `resolutino_instrument` — typo; e o campo é calculado mas nunca atribuído em `_compute_statistics`. | Baixa |
| 11 | [linha 298](../models/engc_calibration.py#L298) | `uncertainty = fields.Char` em `measurement` — campo morto, confunde com o Float das linhas. | Baixa |
| 12 | [linhas 176 e 367](../models/engc_calibration.py#L176) | Duas regras divergentes de validade: `is_valid` (via `validate_calibration`) e o filtro direto por data em `_search_certificates_valid`. | Baixa |
| 13 | [linha 485](../models/engc_calibration.py#L485) | `except` nu engolindo qualquer exceção do cálculo de Veff. | Baixa |
| 14 | [`onchange_measurement_ids`](../models/engc_calibration.py#L85) | Onchange que só faz `_logger.info` — remover. | Baixa |

---

## 8. Roadmap sugerido

### Fase 0 — Destravar (≈ 0,5 dia)
Itens 1, 2, 6, 7 e 13 da tabela. O item 1 é o único realmente urgente e já tem reprodutor:
gere o certificado de uma calibração que use o **QPT-014** como padrão. Decidir a regra de
desempate entre certificados válidos (sugestão: o de `date_calibration` mais recente) e aplicá-la
dentro de `get_certificate_valid()`.

### Fase 1 — Precisão decimal (≈ 1 dia)
`decimal.precision` "Calibration" com 6 dígitos; `digits=` nos Float da cadeia;
`display_decimals` na unidade de medida; QWeb parametrizado. **Backup do banco antes do `-u`**
(muda tipo de coluna). Entrega visível e imediata: `60,053` deixa de virar `60,05`.

### Fase 2 — Certificado multiponto (≈ 3–4 dias)
`nominal_value` + `line_mode` no `uncertainty.lines`; migração dos certificados existentes
(as linhas atuais viram modo `range` cobrindo toda a faixa, preservando o comportamento);
mover as contribuições do padrão para a linha de medição como computados; implementar a
interpolação com erro fora de faixa; ajustar views. **É o núcleo da sua pergunta 1.**

### Fase 3 — Correção do GUM (≈ 2–3 dias)
`s/√n`; Welch-Satterthwaite como somatório, consumindo `veff_instrument`; tabela t-Student →
*k* derivado; resolução do equipamento sob calibração; `n` variável com suporte a Tipo B puro
(n = 1, Veff = Inf); tratamento de tendência configurável. **Pré-requisito obrigatório:** auditar
os `veff` já cadastrados (ver o alerta na seção 3.2 — o QPS-001 está com 2 onde deveria ser Inf) e
trocar a convenção "> 100" por um booleano explícito. **Cobrir com testes unitários usando
exatamente a tabela da sua imagem como caso de referência** — ITM 0,035, k 2,0, Veff Inf é um
ótimo teste de aceitação.

### Fase 4 — Rastreabilidade (≈ 2 dias)
Congelamento em `action_done`; orçamento em JSON; tabela de orçamento de incerteza no certificado;
bloqueio de edição no modelo.

**Total estimado: 9 a 11 dias de trabalho.** As fases 0 e 1 entregam valor imediato e são
independentes das demais — dá para fazer só elas e parar, se quiser.

---

## 9. Oportunidades futuras (fora do escopo pedido)

Registrado aqui para não se perder, explicitamente **fora** do que você pediu:

- **Declaração de conformidade com regra de decisão** (ILAC-G8): comparar `|erro| + U` contra o
  erro máximo admissível do equipamento e emitir Aprovado/Reprovado, com faixa de guarda. Exige
  um campo de EMA/tolerância em `engc.equipment`, que hoje não existe.
- **Deriva do padrão:** contribuição estimada a partir do histórico de certificados do próprio
  padrão — vocês já guardam vários certificados por instrumento, o dado está lá.
- **CMC** (melhor capacidade de medição) do laboratório, como piso da incerteza declarada.
- **Coeficientes de sensibilidade** — hoje todos implicitamente 1, o que só vale quando padrão e
  equipamento medem a mesma grandeza na mesma unidade.
- **Contribuição de temperatura/condições ambientais** — `environmental_conditions` é `Char` livre
  hoje, não entra em cálculo nenhum.
- **Conversão de unidades** entre o padrão e a medição (hoje exige igualdade exata do registro de
  unidade, sem verificação de coerência dimensional).

---

## 10. Referências

- **GUM** — *Guide to the Expression of Uncertainty in Measurement*, JCGM 100:2008. Anexo G para
  Welch-Satterthwaite e a tabela de t-Student.
- **INMETRO DOQ-CGCRE-008** — Orientação sobre estimativa da incerteza de medição. Referência
  nacional, inclui as regras de arredondamento e apresentação.
- **ABNT NBR ISO/IEC 17025:2017** — requisitos de rastreabilidade e conteúdo de certificado.
- **ILAC-G8:09/2019** — regras de decisão e declaração de conformidade.
