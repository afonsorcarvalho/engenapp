# Erro "PCDATA invalid Char value 12" – soluções

Se o script `check_xml_invalid_chars.py` **não encontrou** nenhum caractere inválido nos XML do engc_os, o problema provavelmente está na **cópia da view no banco de dados**, não nos arquivos.

## Solução 1: Recarregar as views do XML (recomendado)

Forçar o Odoo a ler de novo os XML e regravar as views no banco:

1. **Pela interface:** Apps → engc_os → botão "Atualizar" (Upgrade).
2. **Pelo terminal (servidor):**
   ```bash
   odoo -d NOME_DA_BASE -c /caminho/odoo.conf -u engc_os --stop-after-init
   ```
   (Ajuste `-d`, `-c` e o nome do módulo conforme seu ambiente.)

Assim as views são recriadas a partir dos arquivos XML (que estão limpos) e qualquer caractere ruim que estivesse só no banco é sobrescrito.

---

## Solução 2: Verificar a view no banco

Confirmar se o caractere 12 (form feed) está no conteúdo da view armazenado em `ir.ui.view`:

1. No servidor, abra o **Odoo shell**:
   ```bash
   odoo shell -d NOME_DA_BASE -c /caminho/odoo.conf
   ```
2. Execute o script que verifica a view no banco (caminho relativo ao diretório de trabalho):
   ```python
   exec(open('engc_os/check_view_in_db.py').read())
   ```
   Ou copie e cole o conteúdo de `check_view_in_db.py` dentro do shell.

Se forem encontrados caracteres inválidos, a correção é **atualizar o módulo** (Solução 1) para recarregar a view a partir do XML.

---

## Resumo

| Onde o script encontrou algo | O que fazer |
|-----------------------------|-------------|
| Nos **arquivos** XML        | Remover o caractere inválido no arquivo indicado (linha/coluna) e fazer deploy. |
| **Nada** nos arquivos       | Usar **Solução 1** (atualizar o módulo) para recarregar as views do XML. Se quiser confirmar, use **Solução 2** para inspecionar a view no banco. |
