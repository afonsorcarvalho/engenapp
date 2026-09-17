# Modo Semana da Agenda no PWA Técnico — design

**Data:** 2026-09-17
**Módulos:** `afr_qualificacao_agendamento` (backend), `afr_qualificacao/pwa` (front)
**Versão alvo do módulo:** `16.0.1.2.0` (feat)
**Antecede:** `2026-09-16-pwa-agenda-tecnico-design.md` (a aba Agenda e os métodos `pwa_*`)

## Problema

A aba Agenda entregue em 2026-09-16 responde "o que eu tenho pela frente". Não
responde a pergunta de quem **programa** a semana: *onde há folga para encaixar
esta visita?*

O Quadro de Agenda (board OWL) do backend já responde isso — grade técnico × dia
com arrastar-e-soltar. Mas é view de backend Odoo, inutilizável no celular, e sua
interação é `draggable` + `t-on-drop`, que **não dispara em tela de toque**.

Some-se a isso o recurso escasso: os instrumentos metrológicos. Programar sem
ver onde eles estão, e quais estão com calibração vencida, é programar no escuro.

## Decisões de produto

1. **O Gestor faz isso no celular.** Grade de 7 colunas não cabe em ~375px —
   seriam ~45px por célula, sem espaço para OS, cliente e horário. O modo semana
   é, portanto, uma **faixa de dias com carga** mais o detalhe do dia escolhido,
   não uma grade.
2. **Modo dentro da aba Agenda**, não rota nova: um botão alterna Lista ⇄ Semana
   na mesma `/agenda`. Reusa janela, filtro "Só minhas", guard de
   disponibilidade e `VisitaSheet`.
3. **Duas dimensões de recurso:** Técnico e Instrumento, alternáveis no mesmo
   painel.
4. **Remanejar por toque, nunca por arrasto.**
5. **O modo é visível a todos; as ações são só do Gestor** (`can_manage`),
   como o cadeado do card já faz.

## Escopo absorvido

Este design absorve o seletor de instrumento da folha, que havia sido desenhado
em separado e ficou sem aprovação. Os dois precisavam exatamente das mesmas duas
peças de backend — os ids dos instrumentos por visita e a lista de instrumentos
cadastrados —, e ver a distribuição de um recurso sem poder atribuí-lo ali seria
meia funcionalidade.

## Backend

Três mudanças em `models/os_visita.py`. **Nenhum método de mutação novo:** mover
dia, trocar técnico e ligar/desligar instrumento são todos `pwa_visita_update`,
que já existe e já é guardado por Gestor.

### 1. `_pwa_serialize` ganha `instrument_ids`

```python
"instrument_ids": self.instrument_ids.ids,
```

ao lado do `instrument_list` (nomes) que já existe. Sem os ids, nem a folha sabe
o que marcar, nem o painel sabe qual visita ocupa qual instrumento.

`equipment_ids` **não** entra: não foi pedido, e o painel não tem dimensão de
equipamento. YAGNI.

### 2. `pwa_instrumento_options()`

`@api.model`, sem guard (leitura), sem `sudo`:
`engc.calibration.instruments` é legível por `base.group_user`
(`engenapp/engc_os/security/ir.model.access.csv`) — ao contrário do
`hr.employee`, que exigiu o `sudo` do `pwa_tecnico_options`.

Retorno, um item por instrumento:

```python
{"id": 3, "name": "Q001", "validade": "2026-12-31"}
```

- `name` segue o mesmo fallback do serializer: `tag or id_number or name`.
- `validade` é a **maior** `validate_calibration` entre `certificate_ids`, ou
  `False` quando não há certificado. Um campo só, comparado no cliente com o dia
  selecionado — evita o servidor devolver uma matriz instrumento × dia.

O modelo já tem `_instrument_valid_on(instrument, day)`, que é
`any(c.validate_calibration >= day)`. A `validade` acima é a forma serializável
da mesma verdade: se `validade < dia`, nenhum certificado alcança aquele dia.

### 3. `instrument_ids` entra em `_PWA_WRITABLE_FIELDS`

A whitelist passa a ser
`{date, time_start, time_stop, tecnico_id, note, instrument_ids}`.

`pwa_visita_update` aceita **lista simples de ids** e converte no servidor:

```python
if "instrument_ids" in vals:
    ids = vals["instrument_ids"]
    if not isinstance(ids, (list, tuple)) or not all(isinstance(i, int) for i in ids):
        raise UserError(...)
    vals["instrument_ids"] = [(6, 0, list(ids))]
```

Tupla de comando crua vinda do cliente é **recusada**: um `(0, 0, {...})`
criaria registro de instrumento novo pela porta da agenda.

A trava de OS em execução vale de graça — `instrument_ids` já está em
`_SCHEDULE_FIELDS`.

### O que não muda

- A carga por dia e por técnico é somada **no cliente**, a partir das visitas que
  `pwa_agenda_fetch` já devolve na janela.
- O roster completo de técnicos já vem de `pwa_tecnico_options`, incluindo quem
  não tem visita nenhuma — que é justamente para onde se quer mover.
- `_PWA_MAX_SPAN_DAYS = 92` e `_PWA_FETCH_LIMIT = 500` continuam válidos; uma
  semana são 7 dias, folgadamente dentro.

## Front

### Modo

`/tecnico/qualificacao/agenda` ganha um botão **Lista ⇄ Semana**. A preferência
persiste no `tecnicoSettings` (zustand), como o "Só minhas". No modo Semana a
janela passa de 14 para 7 dias.

### Três faixas empilhadas

**1. Dias da semana.** Sete colunas estreitas: dia da semana, número, total de
horas do dia, marca quando há conflito. Uma selecionada.

**"Só minhas" fica desabilitado no modo Semana.** A pergunta que este modo
responde é de capacidade da equipe — carga por dia e por técnico só significa
alguma coisa com a equipe inteira à vista. Deixar o filtro ligado mostraria uma
faixa de dias que contradiz o painel logo abaixo. O controle continua visível,
desabilitado, com o motivo em texto; volta a valer ao trocar para Lista. A navegação de janela
anda de 7 em 7, ancorada em `server_today` como já faz a Lista — o front
continua sem chamar `Date.now()`.

**2. Painel de recursos do dia selecionado**, alternando Técnico ⇄ Instrumento:

- *Técnico*: uma linha por técnico do roster, inclusive os sem visita. Barra de
  carga e horas, ou "livre".
- *Instrumento*: uma linha por instrumento — onde está
  (`Q001 · 8–12 · OS26-02/Afonso`), "livre", ou tarja de calibração vencida
  quando `validade < dia selecionado`.

**3. Visitas do dia selecionado.** Reusa `VisitaCard` sem alteração.

### O gesto

Card editável ganha o botão **Ajustar**. Tocado, a visita entra em seleção e as
outras duas faixas viram alvo, cada uma com seu verbo:

| Toque em | Efeito |
|---|---|
| um dia da faixa | move a visita para aquele dia |
| um técnico do painel | passa a visita para ele |
| um instrumento do painel | liga/desliga aquele instrumento na visita |

Cada toque grava uma chamada `pwa_visita_update` com **um** campo. Tocar fora,
ou em "Concluir", encerra a seleção.

O alvo do gesto é a própria informação que embasa a decisão — o painel já está
na tela dizendo quem está livre. Por isso não há um fluxo de "mover" separado.

**Tocar o card continua abrindo a folha**, como na Lista. A seleção só começa
pelo botão explícito, para que o mesmo toque não tenha dois significados em
modos diferentes.

Alvos de toque ≥44px, como no resto do app — o técnico usa luva.

### Onde o erro cai

Sem folha aberta, a mensagem do servidor (data passada, equipamento sobreposto,
OS em execução, instrumento em conflito) vai para uma **tarja abaixo da faixa de
dias**, no mesmo tom do erro da Lista, e a visita volta visualmente para onde
estava. Escrita é online-only, como o resto deste PWA.

### Escala da barra de carga

Proporcional ao técnico-dia mais cheio da **semana visível**, com as horas
escritas ao lado. O modelo não define uma jornada padrão, e inventar 8h aqui
seria número fingido.

## Granularidade: uma honestidade registrada

O painel diz "livre" por **dia**, mas o conflito que o modelo calcula é por
**janela de horário sobreposta** (`_compute_conflicts`,
`_compute_resource_conflicts`). Por isso cada linha ocupada mostra o horário
(`Q001 · 8–12`): o Gestor vê que 13–17 está livre. Marcar "livre" apenas quando
o dia está totalmente vazio esconderia folga real; marcar sem o horário mentiria
em dia com dois turnos.

Os avisos de conflito continuam **não bloqueantes**, como já são no modelo e no
board OWL: gravar é permitido, a tarja de conflito aparece no card depois.

## Fora de escopo

- Grade técnico × dia (não cabe em celular — decisão de produto 1).
- Arrastar-e-soltar, em qualquer forma.
- Dimensão de equipamento no painel.
- Criar ou apagar visita pelo modo Semana (o FAB e a folha da Lista já fazem).
- Guardar os métodos `board_*`, que seguem sem guard contra o grupo Usuário —
  follow-up já registrado na spec anterior.

## Testes

**Backend** — em `tests/test_pwa_agenda.py`:

- `instrument_ids` aparece no payload de `pwa_agenda_fetch` e bate com o
  `instrument_list`.
- `pwa_instrumento_options` devolve `validade` como a maior
  `validate_calibration`; devolve `False` para instrumento sem certificado.
- `pwa_instrumento_options` chamado por usuário **sem** permissão de HR não
  estoura (espelha `test_tecnico_options_sem_permissao_hr_nao_estoura`).
- `pwa_visita_update` com `{"instrument_ids": [1, 2]}` grava.
- `pwa_visita_update` recusa `{"instrument_ids": [(0, 0, {...})]}` e
  `{"instrument_ids": "abc"}` com `UserError`.
- `pwa_visita_update` com `instrument_ids` numa OS em execução é recusado pela
  trava existente.

**Front** — vitest, baseline limpo em `pwa/docs/BASELINE.md`:

- Agregação de carga por dia e por técnico: função pura, testada isolada,
  incluindo técnico do roster sem visita nenhuma ("livre").
- Mapa de ocupação por instrumento: função pura, incluindo o caso de um
  instrumento em duas visitas no mesmo dia.
- Calibração vencida: `validade < dia selecionado` marca, `>=` não marca,
  `False` marca.
- Máquina de seleção: "Ajustar" seleciona; toque no dia/técnico/instrumento
  dispara a mutação certa com o campo certo; "Concluir" encerra.
- Nenhuma leitura de `Date.now()` na navegação de janela (mesmo teste-âncora da
  Lista).
- Card travado não oferece "Ajustar"; painel não vira alvo sem `can_manage`.
- "Só minhas" chega desabilitado no modo Semana e volta habilitado na Lista.
