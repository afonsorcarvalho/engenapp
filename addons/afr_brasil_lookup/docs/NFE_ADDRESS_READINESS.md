# Prontidão do cadastro de endereço para NF-e (layout 4.00)

Objetivo: garantir que `res.partner` capture os componentes de endereço de
forma **sem perda** (lossless), prontos para um gerador de NF-e próprio (AFR),
sem reprocessamento futuro.

Fontes do layout: Nota Técnica 2018.005 / Manual NF-e 4.00, grupos `enderEmit`
e `enderDest`. Refs no fim.

## 1. Mapa NF-e → campo Odoo

Grupo `enderEmit` / `enderDest`:

| Campo NF-e | Obrig. | Tam. | Tipo | Campo Odoo (hoje) | Status |
|---|---|---|---|---|---|
| `xLgr` (logradouro) | Sim | 2–60 | C | `street` | ⚠️ contaminado c/ número no lookup CNPJ |
| `nro` (número) | Sim | 1–60 | C | — | ❌ não existe (vai p/ `street`) |
| `xCpl` (complemento) | Não | 1–60 | C | `street2` | ⚠️ misturado c/ bairro |
| `xBairro` (bairro) | Sim | 2–60 | C | — | ❌ não existe (vai p/ `street2`) |
| `cMun` (IBGE município) | **Sim** | 7 | N | — | ❌ crítico — `city` é texto livre |
| `xMun` (nome município) | Sim | 2–60 | C | `city` | ✅ |
| `UF` | Sim | 2 | C | `state_id.code` | ✅ |
| `CEP` | Sim | 8 | N | `zip` | ✅ (limpar máscara no gerador) |
| `cPais` (BACEN, 1058=BR) | Não | 4 | N | — | ❌ (mapear no gerador) |
| `xPais` | Não | 6 | C | `country_id.name` | ✅ |
| `fone` | Não | 6–14 | C | `phone` | ⚠️ limpar p/ só dígitos no gerador |

Grupo `emit` / `dest` (identificação):

| Campo NF-e | Obrig. | Campo Odoo | Status |
|---|---|---|---|
| `CNPJ` / `CPF` | Sim | `vat` / `l10n_br_cpf_code` | ✅ (limpar máscara) |
| `xNome` (razão social) | Sim | `name` | ✅ |
| `xFant` (nome fantasia) | Não | — | ❌ (l10n_br nativo não tem) |
| `IE` | Sim* | `l10n_br_ie_code` | ✅ |
| `IM` | Não | `l10n_br_im_code` | ✅ |
| `CNAE` | Não | — | ❌ |
| `CRT` (regime trib. 1/2/3) | Sim (emit) | — | ❌ (é da empresa emitente) |

\* IE obrigatória conforme situação; contribuinte isento usa `indIEDest`/`ISENTO`.

## 2. Localização instalada

Apenas `l10n_br` **nativo** (autor "Akretion, Odoo Brasil") — fornece
`l10n_br_cpf_code`, `l10n_br_ie_code`, `l10n_br_im_code`, `l10n_br_isuf_code`.
**Não** há suíte NF-e (sem OCA `l10n_br_base`/`l10n_br_nfe`, sem `l10n_br_edi`).
Decisão do projeto: **AFR construirá stack NF-e própria** → modelo de campos
abaixo é AFR-owned (sem depender de convenções OCA/Enterprise).

## 3. Modelo de campos AFR proposto (em `res.partner`)

Princípio: **um campo por componente NF-e**, sem concatenação. Prefixo `afr_`
para não colidir com futura instalação de OCA/Enterprise.

| Campo novo | Tipo | NF-e | Origem (lookup) |
|---|---|---|---|
| `afr_street_number` | Char(60) | `nro` | CNPJ API (`number`); CEP não retorna |
| `afr_district` | Char(60) | `xBairro` | CEP API (`neighborhood`) / CNPJ (`district`) |
| `afr_ibge_code` | Char(7) | `cMun` | CNPJ API retorna IBGE; CEP v2 **não** confiável |
| (reuso) `street` | Char | `xLgr` | só logradouro, **sem** número |
| (reuso) `street2` | Char | `xCpl` | só complemento, **sem** bairro |

Notas de design:
- `afr_ibge_code` como Char(7) é o mínimo viável. Evolução recomendada quando a
  stack NF-e chegar: tabela `res.city` (município × UF × IBGE) e m2o `city_id`,
  resolvendo `cMun` por nome+UF para CEPs (a API de CEP não dá IBGE).
- `cPais`/`xPais`: resolver no gerador (Brasil fixo 1058/BRASIL) ou em
  `res.country` via campo de código BACEN — fora do escopo do lookup.
- `CRT`, `CNAE`, `xFant`, IE do emitente: pertencem à **empresa emitente**
  (`res.company`), tratar no módulo gerador, não aqui.
- `fone`/`CEP`/`CNPJ`: armazenar como o usuário digita (com máscara OK);
  o gerador NF-e remove formatação na serialização do XML.

## 4. Correção lossless do lookup (esta entrega)

Antes (lossy) — `res_partner.py`:
- CNPJ: `street = "logradouro, número"`, `street2 = "complemento - bairro"`.
- CEP: `street2 = bairro`.

Depois (lossless):
- `street` = logradouro puro
- `afr_street_number` = número
- `street2` = complemento puro
- `afr_district` = bairro
- `afr_ibge_code` = IBGE (quando a fonte fornecer — CNPJ sim, CEP não)

## Referências

- Layout NF-e 4.00 — campos `enderEmit`/`enderDest`:
  https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=gU6W5KJQ6QM%3D (NT 2018.005)
- Guia de campos (emit/dest/ender): https://flexdocs.net/guia-nfe/emitente/ , https://flexdocs.net/guia-nfe/destinatario/
