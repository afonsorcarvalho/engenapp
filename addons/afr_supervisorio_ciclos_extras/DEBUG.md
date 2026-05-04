# Guia de Debug - Material Lines no Relatório

## 🔍 Problema
O relatório está mostrando 3 materiais mesmo quando apenas 2 são selecionados no wizard.

## 📋 Como Debugar

### Método 1: Debug Visual no PDF

1. **Ative o debug no template:**
   
   Edite o arquivo: `reports/supervisorio_ciclo_reports_inherit.xml`
   
   Encontre as linhas comentadas (por volta da linha 11-16):
   
   ```xml
   <!-- DEBUG: Descomente as linhas abaixo para ver os IDs no PDF -->
   <!-- <div style="background: yellow; padding: 10px; margin: 10px;">
       <strong>DEBUG - IDs do Contexto:</strong> <t t-esc="selected_material_ids"/><br/>
       <strong>DEBUG - Total de materiais:</strong> <t t-esc="len(material_lines)"/><br/>
       <strong>DEBUG - Contexto completo:</strong> <t t-esc="o.env.context"/>
   </div> -->
   ```
   
   **Descomente** removendo `<!--` e `-->`:
   
   ```xml
   <!-- DEBUG: Descomente as linhas abaixo para ver os IDs no PDF -->
   <div style="background: yellow; padding: 10px; margin: 10px;">
       <strong>DEBUG - IDs do Contexto:</strong> <t t-esc="selected_material_ids"/><br/>
       <strong>DEBUG - Total de materiais:</strong> <t t-esc="len(material_lines)"/><br/>
       <strong>DEBUG - Contexto completo:</strong> <t t-esc="o.env.context"/>
   </div>
   ```

2. **Atualize o módulo:**
   ```
   Odoo → Apps → afr_supervisorio_ciclos_extras → Atualizar
   ```

3. **Gere o laudo:**
   - Abra o wizard
   - Marque apenas 2 materiais
   - Gere o PDF
   
4. **Veja o resultado:**
   - O PDF terá uma caixa amarela no topo mostrando:
     - `DEBUG - IDs do Contexto: [12, 15]` ← IDs que vieram do wizard
     - `DEBUG - Total de materiais: 2` ← Quantos foram carregados
     - `DEBUG - Contexto completo: {...}` ← Todo o contexto

5. **Após resolver, comente novamente** para remover o debug do PDF

---

### Método 2: Debug no Log do Odoo

Adicione logs no wizard para ver o que está sendo passado:

**Edite:** `wizard/wizard_print_laudo.py`

```python
def action_print_laudo(self):
    """Imprime o laudo com os materiais selecionados"""
    self.ensure_one()
    
    # Validação: pelo menos um material deve ser selecionado
    if not self.material_line_ids:
        raise UserError(
            'Selecione pelo menos um material para gerar o laudo!'
        )
    
    # DEBUG: Log dos materiais selecionados
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("="*50)
    _logger.info("DEBUG WIZARD - Materiais selecionados:")
    _logger.info(f"IDs: {self.material_line_ids.ids}")
    _logger.info(f"Total: {len(self.material_line_ids)}")
    for mat in self.material_line_ids:
        _logger.info(f"  - ID {mat.id}: {mat.material_descricao}")
    _logger.info("="*50)
    
    # Salva os IDs dos materiais selecionados no ciclo temporariamente via contexto
    return self.env.ref(
        'afr_supervisorio_ciclos_extras.report_laudo_liberacao_produtos_action'
    ).with_context(
        material_line_ids=self.material_line_ids.ids
    ).report_action(self.ciclo_id)
```

**Para ver os logs:**
```bash
# No terminal do Odoo (ou docker logs se usar Docker)
tail -f /var/log/odoo/odoo-server.log | grep "DEBUG WIZARD"
```

---

### Método 3: Debug Interativo no Shell do Odoo

```bash
# Entre no shell do Odoo
odoo shell -c /etc/odoo/odoo.conf -d seu_banco

# No shell Python:
>>> ciclo = env['afr.supervisorio.ciclos'].browse(123)  # ID do seu ciclo
>>> ciclo.material_lines_ids
afr.supervisorio.cycle.materials.lines(10, 11, 12)  # Todos os materiais do ciclo

>>> # Simule o que o wizard faz:
>>> selected_ids = [11, 12]  # Apenas 2 IDs
>>> material_lines = env['afr.supervisorio.cycle.materials.lines'].browse(selected_ids)
>>> len(material_lines)
2  # Deve ser 2!

>>> for mat in material_lines:
...     print(f"ID {mat.id}: {mat.material_descricao}")
```

---

## 🎯 O que Verificar

### 1. No Wizard (interface)
- [ ] Quantos materiais você marcou? (deve ser 2)
- [ ] O contador mostra "Materiais Selecionados: 2"?

### 2. No Banco de Dados
Verifique se não há cache de seleção anterior:

```sql
-- Se tiver acesso ao PostgreSQL
SELECT id, name, ciclo_id, material_id 
FROM afr_supervisorio_cycle_materials_lines 
WHERE ciclo_id = SEU_CICLO_ID;

-- Deve listar todos os materiais do ciclo
-- Mas o wizard deve passar apenas os IDs dos marcados
```

### 3. No Código do Wizard
Verifique se `self.material_line_ids` realmente contém apenas os selecionados:

**Adicione print temporário:**
```python
# No método action_print_laudo
print(f"\n{'='*50}")
print(f"MATERIAIS SELECIONADOS: {self.material_line_ids.ids}")
print(f"TOTAL: {len(self.material_line_ids)}")
print(f"{'='*50}\n")
```

---

## 🐛 Possíveis Causas

### Causa 1: Cache do Navegador
**Solução:** Limpe o cache (Ctrl+Shift+R) ou teste em aba anônima

### Causa 2: Módulo não atualizado
**Solução:** 
```bash
# Via CLI
odoo -u afr_supervisorio_ciclos_extras -d seu_banco --stop-after-init

# Via interface
Apps → afr_supervisorio_ciclos_extras → Atualizar
```

### Causa 3: Contexto não está sendo passado
**Teste:** Adicione debug no template (Método 1 acima)
- Se `selected_material_ids` estiver vazio `[]`, o problema é no wizard
- Se tiver 3 IDs, o problema é na seleção do wizard

### Causa 4: Template está usando fallback
**Verificação:** Com debug ativado, veja se `selected_material_ids` é `False` ou `[]`
- Se for `False`, o contexto não está chegando
- Se for `[]` vazio, nenhum material foi selecionado
- Se tiver IDs errados, o wizard está passando os IDs errados

---

## ✅ Teste Definitivo

1. **Crie um novo ciclo de teste**
2. **Adicione exatamente 3 materiais diferentes**
3. **No wizard, marque apenas o 2º e 3º material**
4. **Com debug ativado, gere o PDF**
5. **Verifique:**
   - Box amarelo deve mostrar 2 IDs
   - Tabela deve mostrar 2 materiais
   - Devem ser os IDs corretos (2º e 3º)

Se aparecerem os 3 materiais mesmo assim, o problema está em outro lugar!

---

## 📝 Checklist de Verificação

- [ ] Módulo atualizado no Odoo
- [ ] Cache do navegador limpo
- [ ] Debug ativado no template
- [ ] PDF gerado com apenas 2 materiais marcados
- [ ] Box amarelo de debug aparece no PDF
- [ ] IDs no box amarelo estão corretos
- [ ] Total de materiais no box é 2
- [ ] Tabela mostra apenas 2 materiais
- [ ] Os materiais na tabela são os corretos

Se todos os checks estiverem ✅ mas ainda aparecerem 3 materiais, **compartilhe o conteúdo do box amarelo de debug**!

