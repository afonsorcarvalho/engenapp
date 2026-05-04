# Changelog - afr_supervisorio_ciclos_extras

## [1.0.2] - 2025-12-05

### 🎯 Simplificação Total do Wizard

**Remoção Completa de Elementos Desnecessários**
- ✅ Removido campo `select_all` do modelo do wizard
- ✅ Removido checkbox "Selecionar Todos" da interface
- ✅ **Removidos botões** "Selecionar Todos" e "Desmarcar Todos"
- ✅ **Removidos métodos** `action_select_all_materials()` e `action_deselect_all_materials()`
- ✅ Wizard agora abre **sem materiais pré-selecionados**
- ✅ Usuário deve **marcar manualmente** cada material usando checkboxes
- 📝 Interface minimalista e clara
- 🎯 Foco total na seleção consciente dos materiais

**Interface Final:**
- Apenas lista de materiais com checkboxes
- Contador de materiais selecionados
- Instruções simples e diretas
- Botões: "Gerar Laudo" e "Cancelar"

**Benefícios:**
- Evita geração acidental de laudos com materiais não desejados
- Deixa claro que o usuário deve escolher ativamente cada material
- Interface minimalista e intuitiva
- Sem distrações ou opções extras

---

## [1.0.1] - 2025-12-05

### ✨ Melhorias de Usabilidade

**Interface Aprimorada**
- ✅ Adicionado botão destacado "Gerar Laudo de Liberação" no header do formulário de ciclo
  - Botão em cor primária (oe_highlight)
  - Visível apenas quando há materiais cadastrados
  - Acesso rápido e intuitivo

**Impressão Sempre via Wizard**
- ✅ Menu "Imprimir" → "Laudo de Liberação de Produtos" agora abre o wizard
- ✅ Menu "Ação" → "Laudo de Liberação de Produtos" agora abre o wizard
- ✅ Todas as formas de acesso garantem seleção de materiais
- ✅ Não há mais impressão direta sem seleção

**Melhorias Técnicas**
- Adicionada ir.actions.server para substituir binding direto do report
- Ação de report agora é interna (usada apenas pelo wizard)
- Documentação atualizada com novos fluxos de acesso

### 🐛 Correções de Bugs

**Relatório Saindo em Branco - CORRIGIDO (v2)**
- ✅ **CAUSA RAIZ**: Mudança de `data={}` para `with_context()` no `report_action()`
  - Wizard agora passa materiais através do contexto: `with_context(material_line_ids=ids)`
  - Template acessa via `o.env.context.get('material_line_ids')` ao invés de `data`
- ✅ Nome do arquivo PDF agora inclui o código do ciclo: `Laudo_Liberacao_Ciclo_[CODIGO]`
- ✅ Simplificada ação server para chamar método do modelo diretamente
- ✅ Corrigido contexto do wizard para incluir `active_id` e `active_model`
- 📝 Documentação detalhada do bugfix em `BUGFIX.md`

---

## [1.0.0] - 2025-12-05

### 🎉 Versão Inicial

Módulo criado para gerenciamento de materiais em ciclos de esterilização.

#### ✨ Funcionalidades Principais

**Cadastro de Materiais**
- Model `afr.supervisorio.materials` para cadastro de materiais
- Campos: descrição, fabricante
- Constraint única: descrição + fabricante
- Menu dedicado no Supervisório

**Registro de Materiais por Ciclo**
- Model `afr.supervisorio.cycle.materials.lines` 
- Relação hierárquica com ciclos
- Campos: material, quantidade, unidade, lote, fabricante, validade
- Unidades: caixa, unidade, pacote, envelope, kit, outro
- Preenchimento automático do fabricante

**Integração com Ciclos**
- Extensão do model `afr.supervisorio.ciclos`
- Aba "Materiais Esterilizados" no formulário do ciclo
- Botão estatístico mostrando quantidade de materiais
- Campo computed para contagem

**Wizard de Seleção de Materiais** 🆕
- Wizard `wizard.print.laudo` para seleção interativa
- Todos os materiais pré-selecionados por padrão
- Seleção individual ou em massa
- Botões de atalho (Selecionar/Desmarcar Todos)
- Contador em tempo real
- Validação de seleção mínima
- Acesso via botão "Gerar Laudo" no ciclo

**Relatório: Laudo de Liberação de Produtos**
- Template completamente novo em formato de laudo oficial
- Página principal: Laudo de Liberação
  - Cabeçalho oficial
  - Identificação do ciclo
  - Tabela de produtos esterilizados (apenas selecionados no wizard)
  - Método de esterilização com referências normativas
  - Dados do indicador biológico
  - Conclusão automática e profissional
  - Rodapé com assinatura
- Anexo: Relatório Técnico
  - Quebra de página automática
  - Estatísticas completas do ciclo
  - Gráfico do ciclo
  - Registro fotográfico
- Integração com wizard para filtrar materiais
- Design profissional com estilos apropriados

**Menus**
- Menu "Materiais" (sequence 60, após Indicadores Biológicos)
- Menu "Materiais dos Ciclos" (sequence 61)

**Documentação**
- README.md: Documentação geral do módulo
- ESTRUTURA.md: Documentação técnica detalhada
- reports/README_RELATORIO.md: Manual do relatório
- wizard/README_WIZARD.md: Manual do wizard
- CHANGELOG.md: Histórico de versões

#### 🔧 Melhorias Técnicas

**Models**
- Nomenclaturas claras e descritivas
- Documentação inline (docstrings)
- Campos relacionados para facilitar buscas
- Constraints de validação
- Métodos name_get customizados

**Views**
- Formulários com widgets apropriados
- Listas editáveis inline
- Filtros e agrupamentos avançados
- Filtros por validade (vencidos/válidos)
- Mensagens de help contextuais
- Wizard modal com interface intuitiva

**Segurança**
- Permissões para todos os usuários (base.group_user)
- Access rights para models e wizard

**Relatórios**
- Template QWeb com estilo profissional
- Suporte a dados dinâmicos (materiais selecionados)
- Quebras de página automáticas
- Tratamento de casos especiais
- Integração com dados do ciclo e indicador biológico

#### 📋 Dependências

- base
- afr_supervisorio_ciclos

#### 🎯 Casos de Uso Suportados

1. **Laudo Completo**: Gerar laudo com todos os materiais do ciclo
2. **Laudo por Cliente**: Selecionar apenas materiais de um cliente específico
3. **Laudo por Categoria**: Agrupar materiais por tipo ou categoria
4. **Múltiplos Laudos**: Gerar vários laudos do mesmo ciclo para diferentes destinatários
5. **Rastreabilidade**: Manter histórico completo de materiais por ciclo

#### 🔜 Próximas Versões

Funcionalidades planejadas:
- [ ] Relatório de rastreabilidade de materiais
- [ ] Dashboard de materiais esterilizados
- [ ] Alertas de validade próxima ao vencimento
- [ ] Integração com estoque
- [ ] Histórico de alterações em materiais
- [ ] Assinatura digital no laudo
- [ ] Código de barras/QR Code no laudo
- [ ] Templates customizáveis de laudo

---

## Formato do Changelog

Este changelog segue o formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
e o projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

### Tipos de Mudanças

- `Added` (Adicionado) para novas funcionalidades
- `Changed` (Modificado) para mudanças em funcionalidades existentes
- `Deprecated` (Obsoleto) para funcionalidades que serão removidas
- `Removed` (Removido) para funcionalidades removidas
- `Fixed` (Corrigido) para correção de bugs
- `Security` (Segurança) para vulnerabilidades

---

**AFR Sistemas** | https://www.afrsistemas.com.br

