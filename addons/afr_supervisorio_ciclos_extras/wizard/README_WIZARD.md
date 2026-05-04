# Wizard de Impressão do Laudo de Liberação

## Descrição

O Wizard de Impressão permite selecionar quais materiais serão incluídos no Laudo de Liberação de Produtos. Útil quando um ciclo contém diversos materiais e é necessário gerar laudos específicos para diferentes clientes ou situações.

## Como Usar

### 1. Acessar o Wizard

**Opção A: Pelo Botão no Header do Formulário (Recomendado)**
1. Abra o formulário de um ciclo de esterilização
2. Clique em **"Gerar Laudo de Liberação"** no header
   - Só aparece se o ciclo tiver materiais cadastrados

**Opção B: Pelo Menu Imprimir**
1. No formulário do ciclo, clique em "Imprimir"
2. Selecione "Laudo de Liberação de Produtos"

**Opção C: Pelo Menu de Ação**
1. No formulário do ciclo, clique em "Ação"
2. Selecione "Laudo de Liberação de Produtos"

### 2. Interface do Wizard

**Cabeçalho:**
- Nome do ciclo
- Título: "Laudo de Liberação de Produtos"

**Informações:**
- **Materiais Selecionados**: Contador em tempo real
- **Data de liberação**: Default = data em que o responsável assinou o ciclo (editável)
- **Data de emissão do laudo**: Default = data de hoje (editável)

**Tabela de Materiais:**
- Descrição do Material
- Fabricante
- Lote
- Quantidade
- Unidade
- Validade

**Botões:**
- **Gerar Laudo**: Gera o PDF (visível apenas quando há materiais selecionados)
- **Cancelar**: Fecha o wizard

### 3. Selecionar Materiais

- Clique na checkbox ao lado de cada material para marcá-lo/desmarcá-lo
- Por padrão, **nenhum material vem selecionado**
- O botão "Gerar Laudo" fica invisível até selecionar pelo menos um material

### 4. Datas no Wizard

| Campo | Default | Editável |
|-------|---------|----------|
| Data de liberação | Data da assinatura do responsável pelo ciclo (ou hoje se não assinado) | Sim |
| Data de emissão | Hoje | Sim |

### 5. Gerar o Laudo

1. Selecione os materiais desejados
2. Confirme ou ajuste as datas
3. Clique em **"Gerar Laudo"**

## Casos de Uso

### Laudo Completo
Marque todos os materiais → "Gerar Laudo"

### Laudo Parcial para Cliente Específico
Marque apenas os materiais do cliente → "Gerar Laudo"

### Múltiplos Laudos do Mesmo Ciclo
Gere um laudo para Cliente A → Abra o wizard novamente → Selecione materiais do Cliente B → Gere outro laudo

## Validações

- **Nenhum material selecionado**: Botão "Gerar Laudo" fica invisível; mensagem de aviso exibida
- **Wizard vazio**: O wizard deve sempre ser aberto a partir do formulário de um ciclo

## Estrutura Técnica

### Model: `wizard.print.laudo`

**Campos:**
- `ciclo_id`: Referência ao ciclo (readonly)
- `material_line_ids`: Many2many com materiais selecionados
- `material_count`: Contador computed
- `signature_type`: Tipo de assinatura (automática / upload / desenho)
- `signature_image`: Imagem da assinatura (binary)
- `signer_name`: Nome do responsável
- `signer_title`: Cargo/função (default: "Garantia de qualidade")
- `data_liberacao`: Data de liberação impressa no laudo (default: `ciclo.signature_date` ou hoje)
- `data_emissao`: Data de emissão impressa no laudo (default: hoje)

**Métodos:**
- `default_get()`: Preenche ciclo e datas por defeito
- `_get_signature_data_for_report()`: Monta dados de assinatura para o relatório
- `action_print_laudo()`: Gera o laudo com materiais e dados selecionados

### Arquivos
- **Model**: `wizard/wizard_print_laudo.py`
- **View**: `wizard/wizard_print_laudo_views.xml`
- **Security**: `security/ir.model.access.csv`

## Suporte

**AFR Sistemas** — https://www.afrsistemas.com.br
