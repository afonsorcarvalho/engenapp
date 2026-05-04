# Supervisório Ciclos - Materiais

## Descrição

Módulo complementar ao `afr_supervisorio_ciclos` que adiciona funcionalidade para gerenciar materiais colocados em ciclos de esterilização.

## Funcionalidades

### Cadastro de Materiais

O módulo permite cadastrar materiais que podem ser esterilizados, incluindo:
- **Descrição**: Descrição do material
- **Fabricante**: Relacionamento com parceiros (res.partner) para identificar o fabricante do material

### Linhas de Materiais por Ciclo

Para cada ciclo de esterilização, é possível registrar os materiais que foram processados através do modelo `afr.supervisorio.cycle.materials.lines`, com os seguintes campos:

- **Ciclo**: Relação hierárquica com o ciclo (afr.supervisorio.ciclos)
- **Material**: Material que foi esterilizado
- **Quantidade**: Quantidade do material
- **Unidade**: Unidade de medida (caixa, unidade, pacote, envelope, kit, outro)
- **Lote**: Número do lote do material
- **Fabricante**: Fabricante do material (pode ser diferente do padrão cadastrado)
- **Validade**: Data de validade do material

### Integração com Ciclos

O módulo estende o modelo de ciclos (`afr.supervisorio.ciclos`) para incluir:
- Uma aba "Materiais Esterilizados" no formulário do ciclo
- Um botão estatístico mostrando a quantidade de materiais no ciclo
- Relação One2many com as linhas de materiais

### Relatório de Liberação de Produtos

O módulo cria um **novo relatório completo** chamado "Laudo de Liberação de Produtos" que substitui o relatório padrão de ciclos quando há materiais registrados.

#### Estrutura do Relatório:

**📄 PÁGINA PRINCIPAL - Laudo de Liberação**
- Cabeçalho oficial formatado como laudo técnico
- Identificação completa do ciclo e equipamento
- Tabela detalhada de todos os produtos esterilizados
- Informações do método de esterilização com referências normativas (RDC 291/2019, ISO 11135:2018)
- Dados completos do indicador biológico utilizado
- Conclusão automática sobre a eficácia da esterilização
- Assinatura do responsável técnico
- Referência ao anexo técnico

**📎 ANEXO - Relatório Técnico do Ciclo** (nova página)
- Informações técnicas detalhadas do ciclo
- Tabela de estatísticas por fase
- Gráfico completo do ciclo
- Registro fotográfico (se disponível)

#### Como Usar:

**Sempre abre o Wizard para Seleção de Materiais:**

1. **Pelo Botão no Header do Formulário (Recomendado)**
   - No formulário do ciclo, clique no botão destacado **"Gerar Laudo de Liberação"** no header
   - O wizard abre automaticamente

2. **Pelo Menu Imprimir**
   - No formulário do ciclo, clique em "Imprimir"
   - Selecione **"Laudo de Liberação de Produtos"**
   - O wizard abre automaticamente

3. **Pelo Menu Ação**
   - No formulário do ciclo, clique em "Ação"
   - Selecione **"Laudo de Liberação de Produtos"**
   - O wizard abre automaticamente

4. **No Wizard:**
   - **Marque os materiais** que deseja incluir clicando nas checkboxes
   - Clique em "Gerar Laudo"
   - O PDF será gerado com **apenas os materiais marcados**

### Wizard de Seleção de Materiais

O módulo inclui um wizard inteligente que permite:
- ✅ **Selecionar materiais específicos** para cada laudo
- ✅ **Gerar múltiplos laudos** do mesmo ciclo para diferentes clientes
- ✅ **Seleção manual** através de checkboxes
- ✅ **Contador em tempo real** de materiais selecionados
- ✅ **Interface simples** e direta

**Casos de Uso:**
- Laudo completo: marque todos os materiais e gere o laudo
- Laudo por cliente: marque apenas os materiais de cada cliente
- Laudo por categoria: marque materiais por tipo/categoria

Para mais detalhes sobre o wizard, consulte: `wizard/README_WIZARD.md`
Para mais detalhes sobre o relatório, consulte: `reports/README_RELATORIO.md`

## Modelos

### afr.supervisorio.materials
Modelo para cadastro de materiais que podem ser esterilizados.

### afr.supervisorio.cycle.materials.lines
Modelo para registro de materiais esterilizados em cada ciclo, com relação hierárquica ao ciclo.

## Menus

O módulo adiciona dois novos itens de menu no menu principal do Supervisório:
- **Materiais**: Gerenciar cadastro de materiais
- **Materiais dos Ciclos**: Visualizar todos os materiais registrados nos ciclos

## Instalação

1. Copie o módulo para o diretório de addons do Odoo
2. Atualize a lista de módulos
3. Instale o módulo `afr_supervisorio_ciclos_extras`

## Dependências

- base
- afr_supervisorio_ciclos

## Versão

16.0.1.0.0

## Autor

AFR Sistemas

## Licença

LGPL-3

