# Relatório: Laudo de Liberação de Produtos

## Descrição

Relatório de liberação de produtos esterilizados, seguindo padrões regulatórios (RDC 291/2019, ISO 11135:2018, ISO 11138-2:2016). Gerado via wizard de seleção de materiais.

## Estrutura do Documento

### Cabeçalho

- Título: "LAUDO DE LIBERAÇÃO DE PRODUTOS ESTERILIZADOS"
- QR Code de autenticidade (canto superior direito, quando disponível)

### Dados do Ciclo

- Ciclo / Lote Ciclo
- Equipamento / Duração
- Data início / Data fim
- Status / Ciclo selecionado
- Gás utilizado no processo: Óxido de Etileno

### MATERIAIS ESTERILIZADOS

Tabela com os materiais selecionados no wizard:

| Coluna | Descrição |
|--------|-----------|
| Item | Numeração sequencial |
| Produto | Descrição do material |
| Fabricante | Nome do fabricante |
| Lote | Número do lote |
| Qtd | Quantidade |
| Unidade | Caixa / Unidade / Pacote / Envelope / Kit / Outro |
| Validade | Data de validade ou "Vide Fabricante" se não informado |

> Quando nenhum material é selecionado, exibe alerta: "Nenhum material foi selecionado para este laudo."

### Tipo de Análise e Método

- **Tipo de Análise:** Análise microbiológica para eficácia do processo por óxido de etileno
- **Método:** Indicadores biológicos em incubadora, conforme RDC 291/2019, ISO 11135:2018 e ISO 11138-2:2016

### INDICADOR BIOLÓGICO

Exibido apenas quando o ciclo tem dados de IB (`ib_lote` preenchido):

- Lote IB / Marca
- Modelo / **Resultado** (verde = Negativo, vermelho = Positivo)
- Início / Fim da Incubação
- Composição: *Bacillus atrophaeus* ATCC 9372, concentração de 10⁶ UFC/unidade

### CONCLUSÃO

Texto normativo de liberação para comercialização.

### Datas de Liberação e Emissão

- **Data de liberação:** Preenchida no wizard (default: data da assinatura do responsável pelo ciclo)
- **Data de emissão:** Preenchida no wizard (default: data de hoje)

### Observações

Exibidas apenas antes da assinatura (campo `notes` do ciclo), se preenchidas.

### Assinatura

- Ciclo assinado digitalmente: exibe imagem da assinatura, nome, conselho e data da assinatura eletrônica
- Ciclo não assinado: usa dados do wizard (imagem, nome, cargo, data)

### Registro Fotográfico

Cada foto (`fotos_ids`) em página separada, com título, legenda e data.

---

## Como Gerar

1. No formulário do ciclo, clique em **"Gerar Laudo de Liberação"** (botão no header) ou "Imprimir" → "Laudo de Liberação de Produtos"
2. No wizard: selecione materiais, confirme datas
3. Clique em **"Gerar Laudo"**

**Nome do arquivo:** `Laudo_Liberacao_[NUMERO_DO_CICLO].pdf`

---

## Requisitos para Laudo Completo

- Materiais cadastrados e vinculados ao ciclo (com lote, validade)
- Dados do indicador biológico preenchidos
- Ciclo assinado (ou assinatura configurada na empresa)

---

## Conformidade Regulatória

- **RDC 291/2019 ANVISA** — Regulamento técnico para esterilização
- **ISO 11135:2018** — Esterilização por óxido de etileno
- **ISO 11138-2:2016** — Indicadores biológicos

---

## Suporte

**AFR Sistemas** — https://www.afrsistemas.com.br
