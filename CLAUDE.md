# CLAUDE.md — odoo_engenapp

## Estrutura do repositório

Monorepo principal: `https://github.com/afonsorcarvalho/engenapp` (privado).

Contém dois **git submodules** (conversão feita em 2026-05-12):

| Path | Repo | Branch |
|---|---|---|
| `addons/afr_ecm/` | `https://github.com/afonsorcarvalho/afr_ecm.git` | `main` |
| `ecm_desktop/` | `https://github.com/afonsorcarvalho/ecm_desktop.git` | `main` |

Configuração em `.gitmodules`.

**Clone:** `git clone --recursive <url>` ou após clone normal `git submodule update --init --recursive`.

**Backup pré-conversão:** tag `pre-submodule-conversion` + branch `backup/pre-submodule-conversion`.

## Regras de Commit

1. **Sempre fazer `git commit` a partir do diretório do arquivo modificado.**
   Se o diretório não contém `.git`, subir ao pai até encontrar o repo correto.
   Nunca assumir que o CWD é o repo correto.

2. **Submodules têm seu próprio `.git`.** Para mudanças em `addons/afr_ecm/`
   ou `ecm_desktop/`:

   ```bash
   cd addons/afr_ecm        # ou cd ecm_desktop
   git add <paths-relativos>
   git commit -m "..."
   git push origin main
   ```

   Depois, opcionalmente, atualizar pointer no monorepo:
   ```bash
   cd /home/afonso/docker/odoo_engenapp
   git add addons/afr_ecm ecm_desktop
   git commit -m "chore: bump submodules"
   git push
   ```

3. **Nunca rodar `git` do monorepo pra mexer dentro dos submodules** —
   o comando vai falhar ou criar commits órfãos.

4. **Agentes commit (`git-commit-push`, `auto_commit_push`):** invocar com
   o `cwd` apontando pro dir do submodule, não do monorepo, quando a
   mudança for dentro de um submodule. Usar paths relativos ao submodule.

5. **Commits sempre via agente especialista (model haiku)** — não usar
   Bash `git commit` direto no main context. Salvo em memória:
   `feedback_commit_via_agent.md`.

## Convenções do projeto

- Odoo 16.0
- Docker entrypoint custom — porta host 8083, NÃO usar `odoo-bin` direto
- Subagentes ativos: `git-commit-push` (haiku), `auto_commit_push` (haiku)
