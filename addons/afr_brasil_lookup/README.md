# AFR Brasil Lookup

Módulo Odoo 16 que adiciona em `res.partner` dois lookups públicos para o Brasil:

| Lookup | Fonte                                              | Auth | Custo |
|--------|----------------------------------------------------|------|-------|
| CEP    | https://brasilapi.com.br/api/cep/v2/{CEP}          | —    | grátis |
| CNPJ   | https://open.cnpja.com/office/{CNPJ}               | —    | grátis (rate-limit) |

## Como usar

### Botão manual (padrão)
No formulário de qualquer contato/empresa:

1. Digite o **CEP** → clique no botão **Buscar CEP** ao lado.
2. Digite o **CNPJ** (campo `vat`) → clique no botão **Buscar CNPJ** ao lado.

Endereço, razão social, estado, etc. são preenchidos automaticamente.

### Onchange automático (opt-in)
Configurações → Geral → **AFR Brasil Lookup**:

- ☐ Preencher endereço ao digitar CEP
- ☐ Preencher empresa ao digitar CNPJ

Quando ativado, basta sair do campo (TAB) e o lookup roda sozinho. Erros são silenciados em logs (não interrompem o usuário).

## Mapeamento de campos

### CEP → res.partner
| API field        | res.partner   |
|------------------|---------------|
| `street`         | `street`      |
| `neighborhood`   | `street2`     |
| `city`           | `city`        |
| `state` (UF)     | `state_id`    |
| `zip` (formatado)| `zip`         |
| —                | `country_id` = Brasil |

### CNPJ → res.partner
| API path                  | res.partner       |
|---------------------------|-------------------|
| `company.name`            | `name`            |
| `address.street + number` | `street`          |
| `address.details + district` | `street2`      |
| `address.city`            | `city`            |
| `address.state` (UF)      | `state_id`        |
| `address.zip` (formatado) | `zip`             |
| `phones[0]`               | `phone`           |
| `emails[0].address`       | `email`           |
| `taxId` (formatado)       | `vat`             |
| —                         | `is_company=True` |
| —                         | `country_id` = Brasil |

## Tratamento de erros

- **CEP/CNPJ inválido**: `UserError` no botão; ignorado silenciosamente no onchange.
- **404 (não encontrado)**: `UserError` com mensagem clara.
- **429 (rate limit)**: `UserError` pedindo aguardar.
- **Timeout (5s)**: `UserError` rede indisponível.

Sem dep externa: usa `urllib.request` da stdlib.

## Testes

```bash
docker compose exec web odoo -d <db> --test-enable -i afr_brasil_lookup --stop-after-init
```

10 testes cobrem: validação dígitos CNPJ, parsing CEP, mapping fields,
onchange ICP on/off, mock de HTTP errors.

## Limitações

- Sem cache de respostas (toda chamada vai à API). Adicionar `ormcache` se
  alto volume de chamadas.
- Sem retry/backoff. 429 retorna erro direto ao usuário.
- IE (Inscrição Estadual) não é preenchida (sem campo padrão em res.partner;
  módulos l10n_br_base costumam adicionar `inscr_est`). Pode-se inherit + extender.

## Licença

LGPL-3 — AFR Sistemas.
