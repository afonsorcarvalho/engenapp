# CLAUDE.md — odoo_engenapp

## Estrutura do repositório

Monorepo principal: `https://github.com/afonsorcarvalho/engenapp` (privado).

Contém **6 git submodules** (fonte da verdade: `.gitmodules`):

| Path | Repo | Branch |
|---|---|---|
| `addons/afr_ecm/` | `https://github.com/afonsorcarvalho/afr_ecm.git` | `main` |
| `ecm_desktop/` | `https://github.com/afonsorcarvalho/ecm_desktop.git` | `main` |
| `addons/afr_stock_reports/` | `https://github.com/afonsorcarvalho/afr_stock_reports.git` | `main` |
| `addons/afr_sgq/` | `https://github.com/afonsorcarvalho/afr_sgq.git` | `main` |
| `addons/afr_qualificacao/` | `https://github.com/afonsorcarvalho/afr_qualificacao.git` | `main` |
| `addons/afr_cme/` | `https://github.com/afonsorcarvalho/afr_cme_rastreabilidade.git` | `main` |

Configuração em `.gitmodules` (conversão inicial 2026-05-12; mais submodules
adicionados depois). **Sempre conferir `.gitmodules`** antes de assumir que um
módulo é parte do monorepo — vários `addons/afr_*` são submodules.

⚠️ **Pegadinha:** ao commitar dentro de um submodule, fazer `git push origin
main` **de dentro do submodule** ANTES do bump do pointer no monorepo. Senão o
pointer aponta para um commit que não existe no remote (pointer quebrado).

**Clone:** `git clone --recursive <url>` ou após clone normal `git submodule update --init --recursive`.

**Backup pré-conversão:** tag `pre-submodule-conversion` + branch `backup/pre-submodule-conversion`.

## Regras de Commit

1. **Sempre fazer `git commit` a partir do diretório do arquivo modificado.**
   Se o diretório não contém `.git`, subir ao pai até encontrar o repo correto.
   Nunca assumir que o CWD é o repo correto.

2. **Submodules têm seu próprio `.git`.** Para mudanças em qualquer submodule
   (ver tabela acima / `.gitmodules`), ex. `addons/afr_qualificacao/`:

   ```bash
   cd addons/afr_qualificacao    # dir do submodule
   git add <paths-relativos>
   git commit -m "..."
   git push origin main          # OBRIGATÓRIO antes do bump do pointer
   ```

   Depois, atualizar pointer no monorepo:
   ```bash
   cd /home/afonso/docker/odoo_engenapp
   git add addons/afr_qualificacao
   git commit -m "chore: bump submodule afr_qualificacao"
   git push
   ```

   **Nunca** fazer o bump do pointer sem ter pushado o commit do submodule —
   o pointer ficaria apontando para um commit ausente no remote.

3. **Nunca rodar `git` do monorepo pra mexer dentro dos submodules** —
   o comando vai falhar ou criar commits órfãos.

4. **Agentes commit (`git-commit-push`, `auto_commit_push`):** invocar com
   o `cwd` apontando pro dir do submodule, não do monorepo, quando a
   mudança for dentro de um submodule. Usar paths relativos ao submodule.

5. **Commits sempre via agente especialista (model haiku)** — não usar
   Bash `git commit` direto no main context. Salvo em memória:
   `feedback_commit_via_agent.md`.

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:
1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes

## Convenções do projeto

- Odoo 16.0
- Docker entrypoint custom — porta host 8083, NÃO usar `odoo-bin` direto
- Subagentes ativos: `git-commit-push` (haiku), `auto_commit_push` (haiku),
  `test-runner` (sonnet)
- **Execução de planos via subagentes sempre que possível** — preferir
  `superpowers:subagent-driven-development` (subagent fresh por task + review
  entre tasks) em vez de execução inline; não perguntar, é o padrão.
- **Rodar testes via subagente especialista `test-runner` (model sonnet)** —
  delegar a execução da suíte/test-tags ao agente `test-runner` em vez de rodar
  o comando docker no main loop; acelera os passos de teste e preserva contexto.
  (Dentro de subagent-driven-development, o próprio implementer/reviewer já roda
  seus testes; a regra vale para runs de teste feitos pelo orquestrador.)
