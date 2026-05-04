# Estrutura do Módulo afr_supervisorio_ciclos_extras

## Hierarquia de Arquivos

```
afr_supervisorio_ciclos_extras/
├── __init__.py                                 # Inicialização do módulo
├── __manifest__.py                             # Manifesto do módulo com metadados e dependências
├── README.md                                   # Documentação do módulo
├── ESTRUTURA.md                                # Este arquivo - estrutura do módulo
│
├── models/                                     # Modelos do módulo
│   ├── __init__.py                            # Importa todos os modelos
│   ├── materials.py                           # Modelo: afr.supervisorio.materials
│   ├── cycle_materials_lines.py               # Modelo: afr.supervisorio.cycle.materials.lines
│   └── supervisorio_ciclos_extend.py          # Extensão: afr.supervisorio.ciclos
│
├── wizard/                                     # Wizards
│   ├── __init__.py                            # Importa todos os wizards
│   ├── wizard_print_laudo.py                  # Wizard: wizard.print.laudo
│   ├── wizard_print_laudo_views.xml           # Views do wizard
│   └── README_WIZARD.md                       # Documentação do wizard
│
├── views/                                      # Views XML
│   ├── materials_views.xml                    # Views do modelo materials
│   ├── cycle_materials_lines_views.xml        # Views do modelo cycle_materials_lines
│   ├── supervisorio_ciclos_extend_views.xml   # Extensão da view do ciclo
│   └── menu_views.xml                         # Menus do módulo
│
├── reports/                                    # Relatórios
│   └── supervisorio_ciclo_reports_inherit.xml # Extensão do relatório de ciclo
│
└── security/                                   # Segurança e permissões
    └── ir.model.access.csv                    # Regras de acesso aos modelos
```

## Modelos Criados

### 1. afr.supervisorio.materials
**Arquivo**: `models/materials.py`

Cadastro de materiais que podem ser esterilizados.

**Campos**:
- `descricao` (Char): Descrição do material [OBRIGATÓRIO]
- `fabricante_id` (Many2one → res.partner): Fabricante do material
- `fabricante_nome` (Char): Nome do fabricante [Campo relacionado]
- `active` (Boolean): Status ativo/inativo

**Restrições**:
- Descrição deve ser única

### 2. afr.supervisorio.cycle.materials.lines
**Arquivo**: `models/cycle_materials_lines.py`

Linhas de materiais esterilizados por ciclo (relação hierárquica com ciclos).

**Campos**:
- `ciclo_id` (Many2one → afr.supervisorio.ciclos): Ciclo de esterilização [OBRIGATÓRIO]
- `material_id` (Many2one → afr.supervisorio.materials): Material esterilizado [OBRIGATÓRIO]
- `quantidade` (Float): Quantidade do material [OBRIGATÓRIO]
- `unidade` (Selection): Unidade de medida [OBRIGATÓRIO]
  - Opções: caixa, unidade, pacote, envelope, kit, outro
- `lote` (Char): Número do lote
- `fabricante_id` (Many2one → res.partner): Fabricante
- `validade` (Date): Data de validade
- `active` (Boolean): Status ativo/inativo

**Campos Relacionados** (para facilitar buscas):
- `ciclo_nome`: Nome do ciclo
- `material_descricao`: Descrição do material
- `fabricante_nome`: Nome do fabricante

**Lógica de Negócio**:
- Ao selecionar um material, o fabricante é preenchido automaticamente com o fabricante padrão do material

### 3. Extensão: afr.supervisorio.ciclos
**Arquivo**: `models/supervisorio_ciclos_extend.py`

Estende o modelo de ciclos para incluir relação com materiais.

**Novos Campos**:
- `material_lines_ids` (One2many → afr.supervisorio.cycle.materials.lines): Lista de materiais do ciclo
- `material_count` (Integer): Contador de materiais [Campo calculado]

**Novos Métodos**:
- `action_view_materials()`: Abre a visualização dos materiais do ciclo
- `action_print_laudo_wizard()`: Abre o wizard de seleção de materiais para impressão do laudo

## Wizards Criados

### wizard.print.laudo
**Arquivo**: `wizard/wizard_print_laudo.py`

Wizard transiente para seleção de materiais antes da impressão do laudo.

**Campos**:
- `ciclo_id` (Many2one → afr.supervisorio.ciclos): Ciclo de referência [READONLY]
- `material_line_ids` (Many2many → afr.supervisorio.cycle.materials.lines): Materiais selecionados
- `material_count` (Integer): Contador de materiais selecionados [COMPUTED]

**Métodos**:
- `action_print_laudo()`: Gera o laudo PDF com os materiais selecionados via contexto

**Validações**:
- Requer pelo menos um material selecionado para gerar o laudo

**Comportamento Padrão**:
- Ao abrir: **nenhum material vem selecionado**
- Usuário deve marcar manualmente cada material usando checkboxes
- Sem botões de atalho - seleção totalmente manual e consciente

### wizard_print_laudo_views.xml

**Vista de Formulário do Wizard:**
- Cabeçalho com nome do ciclo
- Contador de materiais selecionados (em tempo real)
- Mensagem de instruções para o usuário
- Tabela de materiais com checkboxes para seleção individual
- Botão "Gerar Laudo" (só aparece quando há pelo menos 1 material selecionado)
- Botão "Cancelar"
- Mensagem de aviso quando nenhum material está selecionado

**Ação do Wizard:**
- **ID**: `action_wizard_print_laudo`
- **Tipo**: act_window com target='new' (modal)
- **Uso**: Chamada internamente pelos botões e ações

**Ação Server para Abrir o Wizard:**
- **ID**: `action_open_wizard_laudo`
- **Nome**: "Laudo de Liberação de Produtos"
- **Tipo**: ir.actions.server
- **Binding**: Disponível no menu "Imprimir" e "Ação" do formulário de ciclos
- **Comportamento**: Abre o wizard automaticamente (substitui impressão direta)

## Views Criadas

### materials_views.xml
- Formulário de cadastro de materiais
- Lista em árvore de materiais
- Busca e filtros por fabricante
- Ação de janela para acesso ao modelo

### cycle_materials_lines_views.xml
- Formulário de linha de material
- Lista em árvore editável de linhas de materiais
- Busca avançada com filtros:
  - Materiais vencidos
  - Materiais válidos
  - Agrupamento por ciclo, material, unidade, fabricante, validade
- Ação de janela para acesso ao modelo

### supervisorio_ciclos_extend_views.xml
- Extensão do formulário de ciclo
- **Adiciona botão destacado no header**: "Gerar Laudo de Liberação" (oe_highlight, visível apenas quando há materiais)
- Adiciona botão estatístico mostrando contagem de materiais
- Adiciona aba "Materiais Esterilizados" com lista editável

### menu_views.xml
- Menu "Materiais" no menu principal do Supervisório
- Menu "Materiais dos Ciclos" no menu principal do Supervisório

## Relatórios Criados/Estendidos

### supervisorio_ciclo_reports_inherit.xml

Cria um **NOVO RELATÓRIO COMPLETO**: "Laudo de Liberação de Produtos"

Este relatório reorganiza completamente a estrutura para atender necessidades regulatórias:

#### 📄 ESTRUTURA DO RELATÓRIO

**PÁGINA 1: LAUDO DE LIBERAÇÃO (Documento Principal)**

1. **Cabeçalho Oficial**
   - Título formatado: "LAUDO DE LIBERAÇÃO DOS PRODUTOS DESCARTÁVEIS VIA INDICADOR BIOLÓGICO PARA COMERCIALIZAÇÃO"
   - Procedimento de liberação de câmara

2. **Identificação do Ciclo**
   - Número do Ciclo
   - Código da Carga
   - Equipamento utilizado
   - Data de Liberação
   - Tipo de Esterilização
   - Status

3. **Tabela de Produtos Esterilizados**
   - Item (numeração automática)
   - Produto/Descrição
   - Fabricante
   - Lote
   - Quantidade
   - Unidade (traduzida: Caixa, Unidade, Pacote, Envelope, Kit, Outro)
   - Validade

4. **Método de Esterilização**
   - Tipo de Análise: Teste de esterilidade para produtos estéreis
   - Método: Uso de Indicadores Biológicos
   - Referências: RDC 291/2019 ANVISA, ISO 11135:2018, ISO 11138-2:2016

5. **Indicador Biológico**
   - Lote do Indicador
   - Marca
   - Modelo
   - Resultado
   - Início e Fim da Incubação
   - Composição: Bacillus atrophaeus ATCC 9372

6. **Conclusão**
   - Texto automático e formatado confirmando:
     - Uso de indicadores biológicos Bacillus atrophaeus ATCC 9372
     - Incubação por 48 horas
     - Resultado obtido
     - Declaração de liberação para comercialização

7. **Referência ao Anexo**
   - Box destacado indicando o relatório técnico nas páginas seguintes

8. **Rodapé**
   - Data de Emissão
   - Linha de assinatura para Responsável Técnico
   - Nome do operador (se disponível)
   - Metadados do documento

**PÁGINAS SEGUINTES: ANEXO - RELATÓRIO TÉCNICO**

Nova página com quebra automática contendo:

1. **Cabeçalho do Anexo**
   - Título: "ANEXO - RELATÓRIO TÉCNICO DO CICLO DE ESTERILIZAÇÃO"
   - Referência ao laudo principal

2. **Informações Técnicas**
   - Dados completos do equipamento
   - Duração detalhada
   - Ciclo selecionado
   - Datas e horários

3. **Estatísticas do Ciclo**
   - Tabela completa por fase
   - Métricas (min, max, média)

4. **Gráfico do Ciclo**
   - Visualização completa do ciclo

5. **Observações Técnicas**
   - Campo de observações (se houver)

6. **Registro Fotográfico** (se disponível)
   - Cada foto em página separada
   - Cabeçalho identificando como anexo fotográfico
   - Dados da foto (título, legenda, data)

#### 🎨 FORMATAÇÃO E ESTILO

- **Design profissional** com bordas e fundos apropriados
- **Cores padronizadas**: Cinza para seções (#e9ecef), amarelo para alertas (#fff3cd)
- **Tipografia hierárquica**: 14px títulos, 13px seções, 11px tabelas
- **Espaçamento adequado**: Margens de 15-20px entre seções
- **Quebras de página** automáticas entre laudo e anexo

#### 📋 TRATAMENTO DE CASOS ESPECIAIS

- **Sem materiais**: Exibe alerta destacado
- **Sem indicador biológico**: Exibe aviso na conclusão recomendando verificação
- **Sem estatísticas**: Mensagem informativa
- **Sem gráfico**: Mensagem de ausência

#### 🔧 AÇÕES DO RELATÓRIO

**Ação de Report (Interna):**
- **ID**: `report_laudo_liberacao_produtos_action`
- **Nome**: "Laudo de Liberação - PDF"
- **Tipo**: ir.actions.report (qweb-pdf)
- **Uso**: Chamada internamente pelo wizard
- **Template**: `afr_supervisorio_ciclos_extras.report_laudo_liberacao_produtos_template`
- **Arquivo gerado**: `Laudo_Liberacao_[NUMERO_CICLO].pdf`

**Ação Server (Menu Imprimir/Ação):**
- **ID**: `action_open_wizard_laudo`
- **Nome**: "Laudo de Liberação de Produtos"
- **Tipo**: ir.actions.server
- **Comportamento**: Abre o wizard de seleção ao invés de imprimir direto
- **Disponível em**: Menu "Imprimir" e menu "Ação" do formulário de ciclos

#### 📚 DOCUMENTAÇÃO ADICIONAL

Para informações completas sobre o relatório, consulte:
`addons/afr_supervisorio_ciclos_extras/reports/README_RELATORIO.md`

## Segurança

### ir.model.access.csv
Define permissões de acesso para:
- `afr.supervisorio.materials`: Leitura, escrita, criação e exclusão para usuários
- `afr.supervisorio.cycle.materials.lines`: Leitura, escrita, criação e exclusão para usuários

## Dependências

- **base**: Módulo base do Odoo
- **afr_supervisorio_ciclos**: Módulo principal de ciclos (requerido para a hierarquia)

## Fluxo de Uso

### 1. Cadastrar Materiais
- Acesse Menu → Materiais
- Cadastre os materiais com descrição e fabricante

### 2. Adicionar Materiais ao Ciclo
- **Opção A**: Abra o ciclo e vá para a aba "Materiais Esterilizados"
- **Opção B**: Acesse Menu → Materiais dos Ciclos e crie novo registro

### 3. Visualizar Materiais do Ciclo
- No formulário do ciclo, clique no botão estatístico "Materiais"
- Ou acesse a aba "Materiais Esterilizados"

### 4. Gerar Laudo de Liberação (NOVO)

**Todas as opções abrem o Wizard de Seleção:**

**Opção A: Botão no Header (Recomendado)**
1. Abra o formulário do ciclo
2. Clique no botão destacado **"Gerar Laudo de Liberação"** no header
   - ⚠️ Botão só aparece se houver materiais cadastrados
   - 🎨 Botão destacado em cor primária (oe_highlight)

**Opção B: Menu Imprimir**
1. No formulário do ciclo
2. Menu "Imprimir" → "Laudo de Liberação de Produtos"

**Opção C: Menu Ação**
1. No formulário do ciclo
2. Menu "Ação" → "Laudo de Liberação de Produtos"

**No Wizard (todas as opções levam aqui):**
3. **Marque os materiais** que deseja incluir no laudo
   - Por padrão, nenhum material vem selecionado
   - Marque individualmente cada material desejado usando as checkboxes
   - Sem atalhos - seleção totalmente manual
4. Clique em **"Gerar Laudo"** (botão só aparece quando há seleção)
5. PDF é gerado com **apenas os materiais marcados**

**Casos de Uso do Wizard:**
- 📋 **Laudo completo**: Marque todos os materiais → Gere o laudo
- 👥 **Laudo por cliente**: Marque apenas materiais do Cliente X → Gere o laudo
- 🏷️ **Laudo por categoria**: Marque apenas instrumentos ou descartáveis → Gere o laudo
- 📑 **Múltiplos laudos**: Abra o wizard várias vezes, marcando materiais diferentes a cada vez

### 5. Consultar Histórico
- Use Menu → Materiais dos Ciclos
- Aplique filtros por ciclo, material, validade, etc.

