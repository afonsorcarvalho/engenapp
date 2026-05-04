# Correção: Relatório Saindo em Branco

## Problema Identificado

O relatório estava saindo em branco após as mudanças para integrar o wizard com o menu de impressão.

## Causa Raiz REAL

### **Uso incorreto de `data` ao invés de `context`**

**Problema**: 
Estávamos tentando passar os materiais através do parâmetro `data` do `report_action()`, mas o template QWeb não consegue acessar `data` de forma confiável dentro do loop `t-foreach="docs"`.

**Código Problemático**:
```python
# wizard/wizard_print_laudo.py
return self.env.ref(...).report_action(
    self.ciclo_id,
    data={'material_line_ids': self.material_line_ids.ids}  # ❌ ERRADO
)
```

```xml
<!-- Template tentando acessar data -->
<t t-set="material_lines" t-value="data.get('material_line_ids')"/>  <!-- ❌ NÃO FUNCIONA -->
```

**Solução Correta**:
Usar `with_context()` para passar os dados através do contexto do ambiente Odoo:

```python
# wizard/wizard_print_laudo.py - CORRETO
return self.env.ref(...).with_context(
    material_line_ids=self.material_line_ids.ids  # ✅ CORRETO
).report_action(self.ciclo_id)
```

```xml
<!-- Template acessando via contexto -->
<t t-set="material_lines" t-value="o.env.context.get('material_line_ids', [])"/>  <!-- ✅ FUNCIONA -->
```

---

### 2. **Ação Server não retornava corretamente**
**Arquivo**: `reports/supervisorio_ciclo_reports_inherit.xml` (linhas 507-526)

**Problema**: 
A ação server tentava construir a ação inline mas a sintaxe estava complexa.

**Solução**:
```xml
<field name="code">action = records.action_print_laudo_wizard()</field>
```

Simplificado para chamar o método do modelo diretamente.

---

### 3. **Contexto incompleto no wizard**
**Arquivo**: `models/supervisorio_ciclos_extend.py` (método `action_print_laudo_wizard`)

**Problema**:
```python
'context': {
    'default_ciclo_id': self.id,
},
```

O wizard espera `active_id` no contexto (linha 60 do wizard), mas só estava recebendo `default_ciclo_id`.

**Solução**:
```python
'context': {
    'default_ciclo_id': self.id,
    'active_id': self.id,
    'active_model': 'afr.supervisorio.ciclos',
},
```

Agora passa todos os contextos necessários.

---

## Arquivos Modificados

1. ✅ `wizard/wizard_print_laudo.py`
   - Método `action_print_laudo()`: Mudança de `data={}` para `with_context()`
   - Agora passa `material_line_ids` através do contexto ao invés de data

2. ✅ `reports/supervisorio_ciclo_reports_inherit.xml`
   - Linha 8: Acesso via `o.env.context.get()` ao invés de `data.get()`
   - Linha 503: Adicionado `print_report_name` com nome do ciclo
   - Linha 512: Simplificação da ação server

3. ✅ `models/supervisorio_ciclos_extend.py`
   - Linhas 55-58: Adição de `active_id` e `active_model` ao contexto

---

## Testes Recomendados

Após atualizar o módulo, teste os seguintes cenários:

### ✅ Cenário 1: Botão no Header
1. Abra um ciclo com materiais
2. Clique em "Gerar Laudo de Liberação" no header
3. Wizard deve abrir com materiais pré-selecionados
4. Gere o laudo
5. **Esperado**: PDF gerado com conteúdo completo

### ✅ Cenário 2: Menu Imprimir
1. Abra um ciclo com materiais
2. Clique em "Imprimir"
3. Selecione "Laudo de Liberação de Produtos"
4. Wizard deve abrir
5. Gere o laudo
6. **Esperado**: PDF gerado com conteúdo completo

### ✅ Cenário 3: Menu Ação
1. Abra um ciclo com materiais
2. Clique em "Ação"
3. Selecione "Laudo de Liberação de Produtos"
4. Wizard deve abrir
5. Gere o laudo
6. **Esperado**: PDF gerado com conteúdo completo

### ✅ Cenário 4: Seleção Parcial
1. Abra o wizard (qualquer método)
2. Desmarque alguns materiais
3. Gere o laudo
4. **Esperado**: PDF com apenas os materiais selecionados

### ✅ Cenário 5: Todos Selecionados
1. Abra o wizard (qualquer método)
2. Deixe todos selecionados (padrão)
3. Gere o laudo
4. **Esperado**: PDF com todos os materiais do ciclo

---

## Status

✅ **CORRIGIDO** - Versão 1.0.1

Data: 2025-12-05

