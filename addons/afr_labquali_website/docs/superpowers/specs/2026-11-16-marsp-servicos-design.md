# MARSP — página de serviços (`/marsp/servicos`)

## Intenção
Inspirado no bloco "After Sales" da Telstar: mostrar que a MARSP cuida do
equipamento de EtO a vida toda. Serviços apresentados como **da MARSP**
(LabQuali não aparece nesta página). Fala com dois públicos: quem compra
MARSP e quem já tem EtO **de qualquer marca**.

## Objetivos / não-objetivos
- Objetivo: página `/marsp/servicos` com um bloco por serviço + faixa resumo
  na vitrine `/marsp` (entre "Parceria" e "Pedir proposta") linkando a ela.
- CTA de serviço: "Solicitar atendimento técnico" (distinto de "Pedir proposta").
- Não-objetivo: peças de reposição (fica para depois).
- Anti-objetivo: prometer o que a operação não sustenta (sem SLA, prazos,
  estoque, "laboratório de calibração").

## Abordagens
1. Seção de cards só na vitrine — rápida, mas 1 frase por serviço.
2. **Página `/marsp/servicos` + faixa na vitrine — escolhida**: comporta o
   conteúdo por serviço e ajuda busca orgânica.
3. Uma página por serviço — conteúdo hoje ralo demais para 6 páginas.

## Conteúdo (ordem dos blocos)
Formato: o que é / inclui / cliente recebe.

1. **Diagnóstico técnico** — visita de avaliação em EtO de qualquer marca.
   Inclui estanqueidade (leak rate), bomba de vácuo, válvulas de gás,
   umidificação, aquecimento, porta/vedações, histórico de alarmes e tempos
   de ciclo. Recebe relatório com fotos, achados por criticidade e plano de
   ação priorizado. Porta de entrada para os demais serviços.
2. **Manutenção corretiva, preventiva e preditiva** — qualquer marca.
   Corretiva: atendimento a equipamento parado. Preventiva: plano por ciclos/
   meses, troca de vedações e itens de desgaste, verificação de segurança
   (detecção de EtO, intertravamentos). Preditiva: tendência de vácuo e
   estanqueidade. Recebe OS por visita e histórico do equipamento.
3. **Retrofit e modernização** — resumo (CLP/IHM, rastreabilidade, otimização
   de ciclo) + botão para `/retrofit/eto` (página existente).
4. **Qualificação e validação** — QI/QO/QD conforme ISO 11135, mapeamento de
   temperatura e umidade, bioindicadores, requalificação periódica. Recebe
   protocolos e relatórios prontos para VISA/acreditação.
5. **Calibração em campo** — sensores de pressão, temperatura e umidade no
   próprio equipamento, com padrões rastreados à RBC. Recebe certificado com
   incerteza de medição declarada e etiqueta.
6. **Treinamento** — operação (carga, ciclos, IHM, alarmes), segurança com
   EtO (exposição, emergência, EPI), manutenção de 1º nível. Recebe
   certificado de participação e material de apoio.
7. **Suporte remoto** — diagnóstico on-line via IHM/CLP conectado: leitura de
   alarmes, parâmetros e histórico de ciclos à distância, orientação ao
   operador. Sem horário/SLA prometido.
8. **Engenharia de instalação** — apoio na URS (especificação do usuário),
   layout da sala, utilidades, tratamento do gás de exaustão (lavador /
   catalisador) e adequação NR-13 do vaso.

Enriquecimentos técnicos (fonte de inspiração: BOCON, sem copiar texto/números):
- Diagnóstico cita verificação da sequência do ciclo (pré-vácuo, teste de
  estanqueidade, umidificação, injeção, exposição, lavagens de ar, aeração).
- Manutenção cita bomba de vácuo, separador água/gás, intertravamento de
  porta, detecção de vazamento de EtO, componentes à prova de explosão.
- Qualificação: sequência QD → QI → QO → apoio à QP, com análise de risco.
  Inclui validação de software do CLP (confirmado pelo user).
- Card Retrofit linka `/retrofit/eto` mesmo sendo página marca LabQuali
  (aceito pelo user).

Omitidos por ora: peças de reposição, TAF/TAS.

## Restrições
- Seguir o padrão existente: HTML estático em `static/demos/marsp-servicos/`,
  rota via `MARSP` em `controllers/demos.py`, design system MARSP
  (navy `#0A3D62`, laranja `#FF6B35`, Nasalization no wordmark), `page.css`
  da vitrine como referência; mobile-first.
- Bump de versão do manifest (feat → MINOR).
- Texto pt-BR; nada de nomes/textos da Telstar.

## Decisões do builder (deixadas em aberto)
- Ícones dos 6 serviços (SVG inline, estilo das silhuetas da vitrine).
- Destino do CTA "Solicitar atendimento técnico" (reusar o formulário/contato
  de "Pedir proposta" com assunto pré-preenchido é a sugestão).
- Copy final das frases (pode lapidar, sem acrescentar promessas).
