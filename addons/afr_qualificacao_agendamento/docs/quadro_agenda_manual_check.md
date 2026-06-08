# Quadro de Agenda — Checklist de Teste Manual

> **Resultado execução automatizada (agent-browser) — 2026-06-08, db `qualif_test_f811`:**
> Secções 1–8 testadas e PASS, salvo 1 achado. Conflitos (sec. 8) validados via setup de dados
> (visitas 557–561 + OS959 Azure/Fremont) — os 4 tipos aparecem no board com ⚠ + borda vermelha:
> técnico sobreposto, instrumento em 2 OS, calibração vencida (PP01 sem cert), deslocamento Fremont→SP.
>
> **ACHADO CORRIGIDO (2026-06-08):** diálogo "Add: Equipamentos"/Instrumentos mostrava botão
> **NEW**. Fix: `<tree create="false" edit="false">` + `options no_create/no_quick_create/no_create_edit`
> em ambos os campos (os_visita_views.xml). Reteste: diálogo agora só **Select/Close**, sem NEW. ✓
>
> Notas cosméticas: input de hora-fim mostra `--:--` quando fim > 24h (28:00 inválido p/ `type=time`);
> display de hora usa relógio 12h do browser (00:00→12:00 AM, 20:00→08:00 PM) — valor real 24h OK.

**Ambiente:** db `qualif_test_f811`, módulo atualizado (`-u afr_qualificacao_agendamento`).
**Acesso:** menu **Qualificações → Quadro de Agenda** (ou Agenda de Visitas).
**Dica:** após cada `-u`, recarregar o browser com **Ctrl+Shift+R** (limpa cache de assets).

---

## 0. Pré-requisitos / dados
- [ ] Existe ≥1 OS de qualificação ativa (estado ≠ done/cancelada) com equipamentos.
- [ ] ≥2 empregados marcados **Técnico de Qualificação** (`is_tecnico`) — RH → Empregado → ligar o checkbox.
- [ ] Equipamento(s) com **apelido** e/ou **tag** preenchidos (para testar o rótulo).

---

## 1. Navegação (toolbar)
- [ ] Setas **‹ ›** (FontAwesome chevrons) mudam o intervalo (semana anterior/seguinte).
- [ ] Botão **Hoje** volta à semana atual.
- [ ] Coluna do **dia de hoje** aparece destacada (fundo azul claro, header forte).
- [ ] Os dois date pickers (de / até) mudam o intervalo manualmente.

## 2. Adicionar técnico
- [ ] Botão **＋ Técnico** (rodapé) abre dropdown.
- [ ] Dropdown lista **só** empregados `is_tecnico=True`.
- [ ] Técnico já presente no quadro **não** aparece na lista (só os que faltam).
- [ ] Selecionar um técnico → nova linha aparece no quadro (mesmo sem visitas).
- [ ] Clicar fora fecha o dropdown.

## 3. Adicionar visita (no dia)
- [ ] Passar o rato sobre uma célula técnico×dia → botão **+** (FA) aparece.
- [ ] Clicar **+** → dropdown de OS.
- [ ] Campo de **filtro** no topo do dropdown.
- [ ] Filtrar por **número da QOS** (ex: `QOS00012`) → lista reduz.
- [ ] Filtrar por **nome do cliente** → lista reduz.
- [ ] Selecionar uma OS → nova visita criada na célula.
- [ ] OS done/cancelada **não** aparece na lista.

## 4. Card da visita — conteúdo
- [ ] **Nº QOS** + (se done) ícone **✓** (fa-check).
- [ ] **Badge de horas** (ex `8h`) — 1 casa decimal (sem `2.1999...`).
- [ ] **Lixeira vermelha** (fa-trash-o) no topo direito.
- [ ] **Horário início–fim** (dois inputs time 24h).
- [ ] **Cliente** (partner).
- [ ] **Equipamento** com ícone 🔧 (fa-wrench) — mostra **apelido**; se não houver, **tag**; se não, **nome**.
- [ ] **Instrumento** com ícone (fa-tachometer) **amarelo**.
- [ ] **Conflito** (se houver) — ícone ⚠ (fa-exclamation-triangle) + mensagem; borda esquerda vermelha.

## 5. Card — interações
- [ ] **Clicar no card** (fora dos inputs/botões) → abre o form da visita (modal).
  - [ ] Ao gravar/fechar o form, o card **reflete** as mudanças (refetch).
- [ ] **Arrastar** o card para outra célula (técnico/dia) → reagenda; visita `done` **não** arrasta.
- [ ] **Lixeira** → abre **modal Odoo** ("Tem certeza que deseja apagar esta visita?", Apagar/Cancelar).
  - [ ] Cancelar → nada acontece.
  - [ ] Apagar → visita some do quadro.
- [ ] **Horário editável**: clicar num input time e mudar → grava; **horas previstas** recalculam (= fim − início); badge de horas atualiza.

## 6. Faixa de divisão (passa do dia)
- [ ] Editar uma visita para **hora início + horas previstas > 24h** (ex início `20:00`, horas `8` → 28h).
- [ ] **Faixa "+" vertical** aparece na **borda direita** do card, **altura toda**.
- [ ] Clicar na faixa → cria **visita-continuação** no **dia seguinte**:
  - [ ] mesmo **horário de início** da origem.
  - [ ] **resto** das horas previstas.
  - [ ] mesmos técnico / OS / equipamentos / instrumentos.
  - [ ] visita original fica com o que cabe até 24h.
- [ ] Se a continuação **ainda** passa do dia → a faixa "+" **reaparece** nela (pode dividir de novo).

## 7. Form da visita (abrir pelo card ou menu)
- [ ] **Técnico** — dropdown só `is_tecnico=True`.
- [x] Aba **Equipamentos** — só equipamentos **elencados na OS** (`os_id`) ✓; grid **não-editável** (só selecionar/remover) ✓; **sem criar novo** ✓ (corrigido — diálogo só Select/Close).
- [ ] Aba **Instrumentos** — grid **não-editável** mostrando **tag / nº identificação / nome**; botão **Puxar do plano F10**.
- [ ] **Hora fim** = hora início + horas previstas (automático ao mudar).
- [ ] Alongar **hora fim** → aumenta horas previstas + aviso.
- [ ] Se passar de 24h → alerta + botão **Dividir em 2 dias** (cria continuação e abre).

## 8. Conflitos (avisos não-bloqueantes)
- [x] Mesmo técnico, 2 visitas sobrepostas → barra com conflito de técnico. ✓ (557/558)
- [x] Instrumento em 2 OS no mesmo período → conflito de instrumento. ✓ (557/558, inst 145)
- [x] Instrumento sem certificado válido na data → conflito de calibração. ✓ (561, inst 147 PP01)
- [x] Deslocamento entre cidades sem buffer suficiente → conflito de deslocamento. ✓ (560, Fremont→SP, buffer 4h)
