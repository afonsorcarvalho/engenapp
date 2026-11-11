# Pesquisa NR-13 — insumo para o demo "Inspeção NR-13" (caldeira)

Data: 2026-11-10. Fonte primária: texto consolidado NR-13 redação Portaria MTP 1.846/2022
(vigor 01/11/2022, retificação DOU 20/10/2022). Subitens citados são dessa redação.
Marcação **[estimado]** = valor típico de mercado, não consta na norma.

## Alertas de copy (não errar no site)

- Termo é **PLH** (Profissional Legalmente Habilitado), não "PH".
- **Não existe teste hidrostático periódico obrigatório** no texto 2022. TH é de fabricação
  (13.4.4.3) ou a critério do PLH.
- Categoria de caldeira é por **pressão de operação**: A ≥ 1.960 kPa; B entre 60 e 1.960 kPa (13.4.1.1).
- Prazo padrão de inspeção periódica cat. A e B: **12 meses** (13.4.4.4). 24 m com SPIE (cat. B),
  30 m com SGC Anexo IV (cat. B).
- Aos **25 anos** de uso: avaliação de integridade abrangente p/ vida remanescente (13.4.4.6). Não é aposentadoria.
- Extraordinária após **6 meses** inativa (caldeira) — vasos é 12 (13.4.4.10).
- Operador: Anexo I, ensino médio, **40 h** treinamento + **60 h** prática supervisionada (cat. B), 80 h (cat. A).
- Casa de caldeiras: afastamento **3 m**, **2 saídas**, ventilação permanente, sensor de gás (13.4.2.3/13.4.2.4).

## Caldeira-modelo do demo [estimado]

Flamotubular horizontal, 3 passes, gás natural, 2.000 kg/h, PMTA 10,5 kgf/cm² (1,03 MPa),
operação 7 kgf/cm², superfície de aquecimento ~55 m², 2 válvulas de segurança ajustadas em
10,0 e 10,5 kgf/cm², ano 2012 → **Categoria B**, inspeção anual, válvula em bancada anual.

## Dispositivos, placa, documentos (13.4.1)

- Obrigatórios (13.4.1.2): válvula de segurança (abertura ≤ PMTA); indicador de pressão;
  controle automático de nível com intertravamento contra falta d'água.
- Placa (13.4.1.3): fabricante, nº ordem, ano, PMTA, capacidade de vapor, superfície de
  aquecimento, código de construção/edição. Categoria + nº ID visíveis (13.4.1.4).
- Documentação (13.4.1.5): prontuário (10 itens), registro de segurança, **projeto de
  instalação** (obrigatório p/ caldeira), projeto de alteração/reparo, relatórios de inspeção,
  certificados dos dispositivos de segurança.
- Registro de Segurança (13.4.1.8): assinatura do PLH **e do operador presente**.

## Inspeção (13.4.4)

- Tipos: inicial (interno + externo + teste de pressão), periódica (interno + externo), extraordinária.
- Válvulas: desmontar/inspecionar/testar com prazo ≤ periódica (13.4.4.7); teste em campo só em
  situações excepcionais justificadas pelo PLH (13.4.4.7.1). Cat. B sem tratamento
  de água: alavanca manual ≥ 1×/mês (13.4.4.8). Anexo IV: teste de abertura a cada 12 meses.
- Relatório mínimo (13.4.4.12): dados da placa; categoria; tipo caldeira; tipo inspeção; datas;
  descrição exames/testes; **fotos do exame interno**; resultados; **relação de itens NR-13 não
  atendidos**; recomendações; parecer conclusivo até próxima inspeção; data da próxima; PLH
  (nome, assinatura, registro) + técnicos; nº certificado da válvula. Prazo 60 dias (13.3.8).
  Anotar condição no Registro de Segurança imediatamente (13.3.8.1).

## Dados para simular — clímax 1: ultrassom de espessura [estimado]

| Região | Nominal | Mínimo cálculo | Pontos |
|---|---|---|---|
| Costado | 12,7 mm | ~10,0 mm | 4 geratrizes × 3 seções + linha d'água |
| Espelhos | 19,0 mm | ~15,0 mm | 8 posições radiais + solda tubo/espelho |
| Fornalha (tubo de chama) | 12,7 mm | ~9,5 mm | 4 geratrizes × 3 seções (frente/meio/fundo) |
| Tubos de fumaça Ø2" | 3,4 mm | ~2,5 mm | amostra 10–20 % nas extremidades |
| Câmara de reversão | 12,7 mm | ~10,0 mm | — |

Leituras simuladas: costado 12,2–12,6; ponto quente fornalha 10,8 mm (alerta).
Taxa de corrosão = (e_ant − e_atual)/Δt; vida remanescente = (e_atual − e_mín)/taxa;
próxima inspeção ≤ metade da vida remanescente (API 510, prática PLH).
Ex.: fornalha 12,7 → 10,8 em 12 anos ⇒ 0,16 mm/ano ⇒ ≈ 8 anos de vida.

## Dados para simular — clímax 2: válvula de segurança [estimado]

Bancada: PMTA 10,5 vs ajuste 10,5/10,0 vs abertura medida em 3 pops; tolerância ±3 % (ASME).
Reassentamento (blowdown) 7–10 % abaixo. Critério NR: abertura ≤ PMTA (13.4.1.2 "a").
Extra: pressostato limite alto ~0,5 kgf/cm² acima do operacional; teste de corte por baixo nível.

## Não conformidades típicas (cat. B hospital/lavanderia) [típico]

Operador sem prática documentada; Registro sem assinatura do operador; alavanca nunca acionada;
projeto de instalação ausente; casa de caldeiras usada como depósito; sem sensor de gás; água sem
tratamento (incrustação); válvula sem certificado; relatório sem lista de itens não atendidos;
religada após > 6 meses sem extraordinária; > 25 anos sem avaliação de integridade.

## Vasos de pressão (autoclave) — referência rápida

Autoclave hospitalar a vapor: fluido classe C, P.V tipicamente < 1 MPa·m³ ⇒ **Categoria V**:
externo 5 anos / interno 10 anos (Tabela 2, 13.5.4.5). Enquadra se P(kPa)·V(m³) > 8 (13.2.1).

## Fontes

- NR-13 consolidada 2022 (espelho SES-SP): https://saude.sp.gov.br/resources/crh/qualidade-de-vida/saude-e-seguranca/normas-regulamentadoras/nr13-caldeiras_vasos_de_pressao_tubulacoes_e_tanques_metalicos_de_armazenamento.pdf
- FAQ oficial MTE 28/04/2023: https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes/perguntas-e-respostas-nr13_2023_04_28.pdf
- Relatório AIR NR-13 (MTE): https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/relatorios-air/relatorio-air-nr-13.pdf
- Retificação Portaria 1.846/2022: https://www.ibp.org.br/personalizado/uploads/2022/11/portaria-mtp-n-1846-retificacao-20102022.pdf
- Nota Técnica EBSERH 1/2019 (autoclaves): https://www.gov.br/hubrasil/pt-br/acesso-a-informacao/institucional/legislacao-e-normas/legislacao-e-normas-de-engenharia-clinica/sei_sede-1739394-nota-tecnica-sei.pdf/@@download/file
- ASME VIII UG-99 (fator TH): https://industrialmonitordirect.com/blogs/knowledgebase/asme-ug-99b-vs-ug-99c-hydrotest-pressure-selection
