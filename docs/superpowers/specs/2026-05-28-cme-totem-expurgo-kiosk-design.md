# Spec — Piloto Expurgo kiosk (afr_cme_rastreabilidade)

**Data:** 2026-05-28
**Módulo:** `addons/afr_cme/afr_cme_rastreabilidade`
**Cliente OWL:** `static/src/cme_totem/cme_totem.{js,xml,scss}`
**Escopo:** redesenhar a estação **Expurgo** do totem em **modo kiosk** (full-bleed, sem topbar Odoo) como piloto. Após validação com operador real, replicar padrão nas outras estações (preparo, esterilização, entrega, paciente).

---

## 1. Problema

O cliente OWL `cme_totem` atende todas as 5 estações com layout único Bootstrap. Limitações na Expurgo identificadas:

1. **Scroll vertical longo** — setor + dono + método + lista lateral + scan + busca + tabela + botão empilhados numa coluna.
2. **Sem clareza de passos** — setup (setor/método/dono) misturado com operação (scan/linhas).
3. **Feedback de scan fraco** — só notification toast Odoo; sem som, sem flash, sem destaque "+1".
4. **Tipografia/contraste insuficientes para kiosk** — Bootstrap default; valores numéricos pequenos em monitor 22" a 60 cm; cores Odoo (#714b67) não comunicam estados CME.
5. **Sidebar "Pendências" rouba foco** — aside esquerdo permanente ocupa ~1/3 da tela durante operação.
6. **Topbar Odoo presente em kiosk** — operador pode navegar para fora; distração visual.
7. **Sem atalhos teclado** — só Enter no scan; operador experiente quer F-keys.
8. **Erros silenciosos** — "Concluir recebimento" sem confirmação; pode concluir lote vazio ou sem dono em modo `third_party`.

## 2. Não-objetivos do piloto

- Refactor das demais estações (preparo/esterilização/entrega/paciente). Padrão criado é exemplo; replicação fica para depois.
- PWA installable ou rota HTTP standalone (Approach C explorado e descartado). Pode entrar em fase posterior.
- Configuração kiosk por usuário ou por máquina. Piloto usa flag global (ICP).
- Reescrever RPCs `totem_*` ou backend; o piloto é **frontend-only** + 3 ICPs novos.

## 3. Decisões de design

### 3.1 Arquitetura (Approach B híbrido)

Mantém o `ir.actions.client` (`tag="cme_totem"`) e o componente OWL `CmeTotem`. Introduz um **modo kiosk** ativado por:

1. `context.cme_totem_kiosk: True` na ação (menu), **OU**
2. Query param `?kiosk=1` (override em runtime), **OU**
3. ICP `cme.totem.kiosk_default = True` (fallback global).

Quando ativo, o componente root recebe a classe CSS `cme_totem--kiosk`. Essa classe:

- aplica `position: fixed; inset: 0; z-index: 1030` no root, **acima** do `.o_main_navbar`, ocultando-a visualmente;
- aplica o **theme teal cirúrgico** (variáveis CSS substituem `--o-brand-primary` no escopo do componente);
- ativa atalhos de teclado globais, modo idle, modais de confirmação e auto-foco no scan;
- colapsa a sidebar "Pendências" para um drawer slide-out.

Modo inativo: comportamento atual (back-office), zero regressão para usuários que abrem o totem em desktop normal.

**Risco do approach:** ocultar `.o_main_navbar` via empilhamento (z-index + position fixed) é robusto; não depende de `:has()`. Como fallback adicional, ao montar em kiosk o componente seta a classe `cme-totem-kiosk-active` em `document.body` para regras CSS auxiliares.

### 3.2 Layout (landscape split 60/40)

```
┌─ Topbar teal: 🧼 EXPURGO · UTI 3º · Vapor · CME/FLUXO/00023 · 14:32 · ●conex ─┐
│ Stepper: [✓ Setup] [● Scan + materiais] [ Concluir]                            │
├─────────────────────── 60% ────────────────────────┬────── 40% ────────────────┤
│ Hero scan (gigante, foco permanente)                │ Lista materiais (5)        │
│ ┌─────────────────────────────────────────────┐    │ ┌────────────────────────┐ │
│ │ 📷 LEIA A ETIQUETA | Enter confirma         │    │ │ Pinça Kelly      × 2   │ │
│ └─────────────────────────────────────────────┘    │ │ Bisturi          × 1   │ │
│ Busca catálogo (autocomplete)                       │ │ Tesoura          × 1   │ │
│ ┌─────────────────────────────────────────────┐    │ │ ...                   │ │
│ │ Pinça...                                    │    │ └────────────────────────┘ │
│ └─────────────────────────────────────────────┘    │ Total: 5 itens              │
│ Confirmação "+1 Pinça Kelly ✓" (flash 1.5s)         │                             │
├─ Footer teal ──────────────────────────────────────────────────────────────────┤
│ [F1 Ajuda] [F2 Retrabalho] [F3 Pendências] ··················· [F4 Concluir →]  │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Topbar (fixa):** identidade da estação + pill de setup (setor / dono / método) + relógio + indicador de conexão Odoo.
- **Stepper:** três passos `Setup → Scan + materiais → Concluir`. Em kiosk o stepper destaca o passo atual.
- **Split 60/40:** `ScanHero` à esquerda (hero scan + busca catálogo + confirmação), `MaterialsList` à direita (lista sempre visível + total).
- **Footer (fixo):** hint dos atalhos visíveis + botão principal `F4 Concluir`.

Em viewport `< 992px` (tablet/portrait estreito), as duas colunas empilham — `ScanHero` em cima, `MaterialsList` abaixo. Comportamento testado mas não otimizado no piloto (kiosk fixo é o alvo).

### 3.3 Componentes OWL

Refactor do template e do JS para extrair sub-componentes. **Não criamos novos arquivos** ainda — mantemos tudo em `cme_totem.{js,xml,scss}` mas com sub-templates QWeb (`t-name`) e seções claras no JS. Migração para arquivos separados acontece se o piloto for replicado.

| Sub-componente (t-name) | Responsabilidade |
|---|---|
| `cme_totem.KioskTopbar` | título estação, pill de setup, relógio, status de conexão |
| `cme_totem.KioskStepper` | 3 steps (setup/scan/concluir) com estado |
| `cme_totem.ScanHero` | input de scan grande, busca catálogo, slot de "último resultado" |
| `cme_totem.MaterialsList` | lista de linhas + qty inline + total |
| `cme_totem.ActionFooter` | atalhos visíveis + concluir |
| `cme_totem.ConfirmModal` | modal de confirmação de conclusão (resumo + valida) |
| `cme_totem.IdleOverlay` | overlay full-screen "Toque para começar" |
| `cme_totem.SetupPanel` | painel atual (setor/dono/método) — colapsa em pill no header após sessão |

Os sub-componentes recebem callbacks via props; estado central permanece no `CmeTotem` para evitar reescrita do controller.

### 3.4 Paleta — teal cirúrgico

Variáveis CSS no escopo `.cme_totem--kiosk` (não vazam para back-office):

```scss
.cme_totem--kiosk {
  --kiosk-primary: #134e4a;   /* teal-900 — topbar/footer */
  --kiosk-accent:  #0f766e;   /* teal-700 — botões/links */
  --kiosk-hero-bg: #f0fdfa;   /* teal-50 */
  --kiosk-hero-bd: #14b8a6;   /* teal-500 */
  --kiosk-hero-fg: #134e4a;
  --kiosk-ok-bg:   #ecfdf5;   /* emerald-50 */
  --kiosk-ok-bd:   #34d399;   /* emerald-400 */
  --kiosk-ok-fg:   #065f46;   /* emerald-800 */
  --kiosk-err-bg:  #fef2f2;
  --kiosk-err-fg:  #991b1b;

  /* RDC 15 — estados CME */
  --rdc-sujo:     #92400e;
  --rdc-processo: #d97706;
  --rdc-critico:  #dc2626;
  --rdc-seguro:   #0f766e;
  --rdc-usado:    #475569;

  /* tipografia kiosk */
  --kiosk-fs-base: 20px;
  --kiosk-fs-hero: 28px;
  --kiosk-fs-num:  24px;     /* total, qty — tabular-nums */
}
```

### 3.5 Comportamentos

| # | Comportamento | Detalhe técnico |
|---|---|---|
| C1 | Stepper visual sempre topo | `KioskStepper`, 3 estados (`pending/active/done`), derivados de `state.sessionId` + `state.summary.lines.length` |
| C2 | Setup colapsa em pill após sessão criada | `SetupPanel` esconde-se quando `state.sessionId` existe; pill no topbar mostra "UTI 3º · Vapor · próprio"; botão "editar setup" reabre |
| C3 | Feedback scan = som + flash + "+1" | Web Audio (gerado via `OscillatorNode`, sem assets), overlay de flash 200ms (`<div class="cme_totem-flash cme_totem-flash--ok">` removido após timer), painel "+1 Pinça Kelly" no `ScanHero` por 1.5s. Som controlado por ICP `cme.totem.sound_enabled` |
| C4 | Sidebar "Pendências" colapsa em kiosk | `cme_totem-pipeline-aside` recebe classe `cme_totem-drawer`, posicionada `transform: translateX(-100%)`; F3 ou botão "Pendências (n)" no footer faz `translateX(0)` |
| C5 | Atalhos teclado | Listener global no root component (`useExternalListener(window, 'keydown', ...)`): F1=ajuda · F2=retrabalho · F3=pendências · F4=concluir · F5=refresh · Esc=cancel modal; tudo `preventDefault` apenas quando modais/inputs não interceptam |
| C6 | Confirm modal antes "Concluir" | `ConfirmModal` mostra: nº de linhas, setor, dono, método; bloqueia ação se `lines.length == 0` OR (`operating_mode == 'third_party'` AND falta `material_owner_partner_id`) |
| C7 | Auto-foco no scan | `useRef("scanInput")` + `t-on-blur` schedules `setTimeout(() => el.focus(), 50)`; modal fechado dispara refocus; troca de aba (`document.visibilitychange`) restaura |
| C8 | Idle screensaver | Timer no root component reset em qualquer event handler; após `idle_timeout_min` (default 5) sem sessão ativa, monta `IdleOverlay` ("Toque para começar"); qualquer scan/touch fecha |
| C9 | Indicador conexão + relógio | `setInterval` 30s chama `web/webclient/version_info` (lightweight existing endpoint); dot verde/vermelho no topbar; relógio `HH:MM` atualiza a cada 30s também |

### 3.6 Backend (mínimo)

Adicionar três `ir.config_parameter`:

| Chave | Tipo | Default | Função |
|---|---|---|---|
| `cme.totem.kiosk_default` | bool | `False` | Quando `True`, qualquer abertura do totem entra em modo kiosk se context/query não disserem o contrário |
| `cme.totem.sound_enabled` | bool | `True` | Som de scan (sucesso/erro) ligado |
| `cme.totem.idle_timeout_min` | int | `5` | Minutos sem ação antes do idle overlay |

Carregados em `totem_get_app_config` (já existe) e expostos no `state.appConfig` para o cliente.

Os RPCs existentes (`totem_open_session`, `totem_add_expurgo_line`, `totem_set_expurgo_line_qty`, `totem_done`, etc.) **não mudam**.

## 4. Estrutura de arquivos

| Caminho | Mudança |
|---|---|
| `static/src/cme_totem/cme_totem.js` | Adiciona estado kiosk (`isKiosk` computed), listener global de teclado, timer idle, ping conexão, helper Web Audio, refocus scan. Extrai sub-handlers por componente. |
| `static/src/cme_totem/cme_totem.xml` | Reorganiza em sub-templates (`t-name="cme_totem.KioskTopbar"`, etc.). Adiciona overlay de flash, modal de confirmação, idle overlay. Stepper. |
| `static/src/cme_totem/cme_totem.scss` | Bloco `.cme_totem--kiosk` com vars CSS, full-bleed, paleta, tipografia kiosk, drawer da sidebar, flash, modais. Mantém estilos atuais para back-office. |
| `models/cme_dirty_receipt.py` | Estende `totem_get_app_config` (linha 288) para incluir `kiosk_default`, `sound_enabled`, `idle_timeout_min` lidos dos 3 ICPs. |
| `data/cme_totem_kiosk_icps.xml` | Cria os 3 `ir.config_parameter` com defaults documentados (noupdate=1). |
| `__manifest__.py` | Adiciona o XML novo ao `data`. |

## 5. Critérios de aceitação

1. Abrir o totem com `?kiosk=1` em monitor 22" landscape: topbar Odoo invisível, paleta teal, stepper visível, scan hero ≥ 28px font.
2. Pressionar F4 com 0 linhas: confirm modal bloqueia (mensagem clara).
3. Pressionar F4 em modo `third_party` sem dono: confirm modal bloqueia.
4. Pressionar F4 com linhas válidas: confirm modal mostra resumo; "Confirmar" chama `totem_done` existente; sessão fecha; stepper avança para "Concluído"; volta a estado pronto para nova sessão.
5. Scan de etiqueta válida: som agudo curto + flash verde 200ms + "+1 [nome material]" por 1.5s + linha aparece na `MaterialsList` à direita.
6. Scan inválido (catálogo desconhecido): som grave + flash vermelho + toast com erro RPC.
7. Sem ações por `idle_timeout_min` minutos sem sessão: idle overlay aparece; qualquer toque/scan retira.
8. Sidebar "Pendências": drawer colapsado por padrão; F3 ou botão abre; segundo F3/Esc fecha.
9. Abrir o totem sem `?kiosk=1` e sem ICP global ligado: comportamento atual de back-office, sem regressão visual.
10. ICP `cme.totem.kiosk_default = True` sem query param: kiosk ativa.

## 6. Testes

### 6.1 QUnit (OWL) — `static/tests/cme_totem_kiosk_tests.js` (novo)

- `render kiosk vs back-office` — classe `cme_totem--kiosk` aparece com flag, ausente sem flag.
- `F-keys disparam handlers` — F4 chama `onDoneExpurgo`, F2 abre rework modal, Esc fecha modal.
- `confirm modal bloqueia conclusão inválida` — sem linhas, falta dono `third_party`.
- `idle overlay aparece após timeout` — usar `mockTimer`.
- `auto-foco scan restaura após blur` — `el.blur()`, aguarda 50ms, `document.activeElement === scanInput`.

### 6.2 Smoke Python — `tests/test_totem_kiosk_config.py` (novo)

- Após install, os 3 ICPs existem com defaults documentados.
- `totem_get_app_config` retorna `kiosk_default`, `sound_enabled`, `idle_timeout_min` no payload.

### 6.3 Manual — checklist em `docs/cme_totem_kiosk_manual_check.md` (novo)

- Kiosk 22" landscape: layout 60/40 ok, sem topbar, sem scroll horizontal.
- Leitor USB real: scan dispara handler, foco mantido após resposta RPC.
- Queda Odoo durante operação: indicador vira vermelho ≤ 30s; reconnect retoma sem perder sessão.
- F-keys em teclado físico operam atalhos.

## 7. Plano de release

- **Fase A (piloto):** este spec. Implementa kiosk só na Expurgo. Outras estações usam o mesmo `CmeTotem` mas sem layout kiosk (back-office segue como hoje).
- **Fase B:** após validação com operador real, aplicar o mesmo padrão de zonas/atalhos/feedback nas demais estações (preparo, esterilização, entrega, paciente).
- **Fase C:** opcionalmente PWA installable / rota HTTP dedicada se o cenário kiosk se generalizar.

## 8. Pontos abertos

Nenhum bloqueante. Decisões registradas:

- Paleta: **teal cirúrgico** (decidida).
- Layout: **landscape split 60/40** (decidida).
- Approach: **B híbrido** (decidida).
- Sub-componentes inline (sub-templates QWeb) vs arquivos separados: **inline no piloto**.

---

**Referências:**

- Memória `project-afr-cme-rastreabilidade` em `~/.claude/projects/-home-afonso-docker-odoo-engenapp/memory/`
- Repo standalone: `github.com/afonsorcarvalho/afr_cme_rastreabilidade` (submodule em `addons/afr_cme/`)
- TODO entry: `Em curso` em `TODO.md`
