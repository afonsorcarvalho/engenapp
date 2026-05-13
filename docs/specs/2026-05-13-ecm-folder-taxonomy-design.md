# Brainstorm — Organização de Pastas ECM (Empresa de Reprocessamento/Esterilização)

## Sumário Executivo

**Objetivo:** taxonomia de pastas + classes documentais para CME externa terceira (RDC 15/2012) implementada sobre `afr_ecm` (Odoo + OCA dms), com foco em compliance regulatório e eficiência operacional.

**Eixo de organização:** híbrido funcional + norma. Nível 1 (raiz) = 10 áreas com prefixo numérico CDD. Dentro de cada área: `/Documentos` (controláveis, versionados, vigência única) + `/Registros` (evidências, com retenção).

**Áreas raiz:**
```
00_SGQ · 10_Operacao · 20_Regulatorio · 30_Comercial · 40_RH
50_Financeiro_Fiscal · 60_TI · 70_Engenharia_Manutencao · 80_SST · 90_Diretoria
```

**Convenções transversais:**
- Nomenclatura: `[CODIGO]_[Titulo]_v[VER]_[YYYY-MM-DD].ext` (POP-XX, IT-XX, FORM-XX, REG-XX…)
- Metadados cruzados (`metadata_field` do afr_ecm): `cliente_id`, `equipamento_id`, `norma_referencia`, `processo`, `validade_data`, `versao_vigente`, `obsoleto`
- Retenção alinhada: RDC 15 (5a op), NR-7 (ASO 20a pós-deslig.), CLT (5a) com precaução 30a RH, CTN/CC (fiscal 5–10a), LGPD (currículo 6m–2a, incidentes 10a)
- Confidencialidade default por área: SGQ/Op = Internal; Reg/Com contratos = Restricted; RH/Fin/Diretoria = Confidential
- Grupos `dms.access.group` espelhados em `res.groups`: ECM_Manager, ECM_SGQ, ECM_Operacao, ECM_Regulatorio, ECM_Comercial, ECM_RH, ECM_RH_Funcionario (próprio dossiê), ECM_Financeiro, ECM_TI, ECM_Eng, ECM_SST, ECM_Diretoria, Auditor_Externo (temporário)

**Decisão arquitetural:** registros transacionais (ciclos diários, BI/CI, leitura câmara) ficam em `afr_supervisorio_ciclos` (módulo Odoo dedicado). ECM recebe apenas sumários mensais agregados + eventos críticos (BI+, recall, liberação excepcional).

**Escopo do brainstorm:** taxonomia + convenções + matriz norma×pasta. Doc types, workflows e seeds XML detalhados no plan são **input para writing-plans posterior**, não contrato de implementação.

## Context

Empresa CME externa terceira (RDC 15/2012). ECM atual (`afr_ecm` sobre OCA dms) tem hierarquia genérica e 6 doc types pré-definidos sem foco regulatório do setor. Operacional transacional (ciclos, indicadores BI/CI, liberação carga) fica em `afr_supervisorio_ciclos`. ECM guarda apenas docs estáticos: SGQ, Operação (docs+evidências), Regulatório, Administrativo. Eixo: híbrido funcional+norma com /Documentos e /Registros dentro de cada área.

## Decisões já alinhadas

| Tópico | Decisão |
|---|---|
| Modelo operação | CME externa terceira — RDC 15/2012 + ISO 9001 (rota ISO 13485 quando aplicável) |
| Escopo ECM | SGQ + Operação + Regulatório + Administrativo (RH/Fin/Com) |
| Eixo nível 1 | Híbrido funcional + norma |
| Reg. operacional transacional | Fora ECM (módulo Odoo `afr_supervisorio_ciclos`) |
| Doc vs Registro | Híbrido — separar **dentro** de cada área |

## Normas aplicáveis

- **ANVISA RDC 15/2012** — boas práticas processamento PPS (norma-mãe)
- **ABNT NBR ISO 9001** — SGQ
- **ABNT NBR ISO 13485** — SGQ dispositivos médicos (aplicável quando contrato cliente exigir)
- **ABNT NBR ISO 17665** — esterilização vapor (validação)
- **ABNT NBR ISO 11135** — esterilização ETO
- **ABNT NBR ISO 11140** — indicadores químicos
- **ABNT NBR ISO 11138** — indicadores biológicos
- **ABNT NBR ISO 14937** — req. desenv./valid./controle esterilização
- **ABNT NBR ISO 15883** — lavadora-desinfetadora
- **ABNT NBR ISO 15489** — gestão arquivos/records management
- **NR-32** — segurança em serviços de saúde
- **LGPD** — Lei 13.709/2018 (dados funcionários, pacientes via PPS)

---

## Proposta — Taxonomia raiz

Prefixo numérico (CDD-inspired) para ordenação estável e referência em auditoria:

```
ECM/
├── 00_SGQ/                       Sistema de Gestão da Qualidade
├── 10_Operacao/                  Reprocessamento (processo CME)
├── 20_Regulatorio/               Licenças, AFE/AE, RT, compliance regulatório
├── 30_Comercial/                 Contratos, clientes, propostas
├── 40_RH/                        Pessoas, treinamento, pastas funcionais
├── 50_Financeiro_Fiscal/         Fiscal, contábil, tributário
├── 60_TI/                        Infra, sistemas, segurança da informação
├── 70_Engenharia_Manutencao/     Qualificação equipamentos, manutenção
├── 80_SST/                       Saúde e Segurança do Trabalho (NR-32)
└── 90_Diretoria/                 Estratégia, atas direção, indicadores macro
```

Dentro de cada área: `/Documentos` (controláveis, versionados) + `/Registros` (evidências com retenção).

---

## Detalhamento por área

### 00_SGQ (detalhado)

Coração do sistema. Estrutura espelha cláusulas ISO 9001/13485 mapeadas para CME (RDC 15).

```
00_SGQ/
├── Documentos/
│   ├── 01_Manual_Qualidade/
│   │   ├── Manual_Qualidade_Vigente.pdf
│   │   ├── Versoes_Anteriores/
│   │   └── Apresentacao_Manual_Resumo.pdf
│   ├── 02_Politica_Objetivos/
│   │   ├── Politica_Qualidade.pdf
│   │   ├── Objetivos_Qualidade_AAAA.pdf       (anuais, mensuráveis)
│   │   ├── Missao_Visao_Valores.pdf
│   │   └── Politica_Anti_Falsificacao.pdf     (autenticidade lotes/IB)
│   ├── 03_Mapa_Processos/
│   │   ├── Mapa_Processos_Macro.pdf           (cadeia valor)
│   │   ├── Mapa_Processos_Suporte.pdf
│   │   ├── Tartaruga_Processo_Reprocessamento.pdf
│   │   ├── Tartaruga_Processo_Comercial.pdf
│   │   └── Interacao_Processos.pdf            (matriz E-S entre processos)
│   ├── 04_Contexto_Organizacao/
│   │   ├── Analise_Contexto_SWOT.pdf
│   │   ├── Partes_Interessadas.pdf
│   │   ├── Necessidades_Expectativas.pdf
│   │   └── Escopo_SGQ.pdf
│   ├── 05_Lista_Mestra_Documentos/
│   │   ├── LMD_Vigente.xlsx                   (índice doc controlado: código, título, versão, vigência, distribuição)
│   │   └── Historico_LMD/
│   ├── 06_Procedimentos_Sistemicos/           (POPs do SGQ — exigidos ISO 9001/13485)
│   │   ├── POP-SGQ-001_Controle_Documentos.pdf
│   │   ├── POP-SGQ-002_Controle_Registros.pdf
│   │   ├── POP-SGQ-003_Auditoria_Interna.pdf
│   │   ├── POP-SGQ-004_Tratamento_NC.pdf
│   │   ├── POP-SGQ-005_Acao_Corretiva_Preventiva_CAPA.pdf
│   │   ├── POP-SGQ-006_Analise_Critica_Direcao.pdf
│   │   ├── POP-SGQ-007_Gestao_Mudancas.pdf
│   │   ├── POP-SGQ-008_Gestao_Riscos.pdf
│   │   ├── POP-SGQ-009_Comunicacao_Interna_Externa.pdf
│   │   ├── POP-SGQ-010_Pesquisa_Satisfacao.pdf
│   │   ├── POP-SGQ-011_Tratamento_Reclamacao.pdf
│   │   ├── POP-SGQ-012_Indicadores_KPI.pdf
│   │   ├── POP-SGQ-013_Calibracao_Verificacao.pdf
│   │   ├── POP-SGQ-014_Qualificacao_Fornecedor.pdf
│   │   ├── POP-SGQ-015_Identificacao_Rastreabilidade.pdf
│   │   ├── POP-SGQ-016_Preservacao_Produto.pdf
│   │   ├── POP-SGQ-017_Treinamento_Conscientizacao.pdf
│   │   └── POP-SGQ-018_Lições_Aprendidas.pdf
│   ├── 07_Procedimentos_Especificos_ISO13485/  (se cliente exige 13485)
│   │   ├── POP-13485-001_Arquivo_Mestre_Dispositivo_DMR.pdf
│   │   ├── POP-13485-002_Vigilancia_Pos_Mercado.pdf
│   │   ├── POP-13485-003_UDI_Identificacao_Unica.pdf
│   │   └── POP-13485-004_Limpeza_Particulas.pdf
│   ├── 08_Formularios_Mestres_SGQ/
│   │   ├── FORM-SGQ-001_Solicitacao_Documento.pdf
│   │   ├── FORM-SGQ-002_Solicitacao_Mudanca_RDM.pdf
│   │   ├── FORM-SGQ-003_Registro_NC.pdf
│   │   ├── FORM-SGQ-004_CAPA.pdf
│   │   ├── FORM-SGQ-005_Plano_Auditoria_Interna.pdf
│   │   ├── FORM-SGQ-006_Checklist_Auditoria.pdf
│   │   ├── FORM-SGQ-007_Relatorio_Auditoria.pdf
│   │   ├── FORM-SGQ-008_Pauta_Analise_Critica.pdf
│   │   ├── FORM-SGQ-009_Ata_Analise_Critica.pdf
│   │   ├── FORM-SGQ-010_Pesquisa_Satisfacao.pdf
│   │   └── FORM-SGQ-011_Avaliacao_Fornecedor.pdf
│   ├── 09_Politicas_Especificas/
│   │   ├── Politica_Riscos.pdf
│   │   ├── Politica_Mudanca_Change_Control.pdf
│   │   ├── Politica_Treinamento_Conscientizacao.pdf
│   │   ├── Politica_Comunicacao.pdf
│   │   ├── Politica_Avaliacao_Fornecedores.pdf
│   │   └── Politica_Liberacao_Produto.pdf
│   └── 10_Cronograma_Anual_SGQ/
│       ├── Cronograma_Auditorias_Internas_AAAA.pdf
│       ├── Cronograma_Analise_Critica_AAAA.pdf
│       ├── Cronograma_Treinamentos_SGQ_AAAA.pdf
│       └── Plano_Acao_Anual_SGQ.pdf
└── Registros/
    ├── 01_Analise_Critica_Direcao/AAAA/
    │   └── ACD_AAAAMMDD/
    │       ├── Pauta.pdf
    │       ├── Apresentacoes_Areas/             (input de cada área)
    │       ├── Ata_Reuniao.pdf
    │       ├── Decisoes_Plano_Acao.pdf
    │       └── Follow_Up.pdf
    ├── 02_Auditorias_Internas/AAAA/
    │   └── AI_AAAAMMDD_Escopo/
    │       ├── Plano_Auditoria.pdf
    │       ├── Checklist_Preenchido.pdf
    │       ├── Lista_Documentos_Evidencias.pdf
    │       ├── Relatorio_Final.pdf
    │       ├── NCs_Identificadas/               (links p/ NCs)
    │       └── Encerramento.pdf
    ├── 03_Auditorias_Externas/AAAA/
    │   ├── ISO_9001_AAAA/
    │   │   ├── Pre_Auditoria/
    │   │   ├── Auditoria/
    │   │   ├── NCs_Apontadas/
    │   │   ├── Plano_Acao_Resposta/
    │   │   ├── Certificado/
    │   │   └── Manutencao_Recertificacao/
    │   ├── ISO_13485_AAAA/                      (se aplicável)
    │   ├── ONA_AAAA/                            (se acreditação)
    │   ├── Cliente_AAAA/                        (cópia de 30_Comercial/AuditCli)
    │   └── Outras/
    ├── 04_Inspecoes_VISA/AAAA/                  (cópia de 20_Regulatorio)
    ├── 05_Nao_Conformidades/AAAA/
    │   └── NC_AAAAMMDD_NN/
    │       ├── Registro_NC.pdf
    │       ├── Disposicao_Imediata.pdf          (correção)
    │       ├── Investigacao_Causa_Raiz.pdf      (5 porquês, Ishikawa, Pareto)
    │       ├── Risco_Avaliacao.pdf
    │       ├── CAPA_Vinculada.pdf
    │       ├── Verificacao_Eficacia.pdf
    │       └── Encerramento.pdf
    ├── 06_CAPA/AAAA/                            (Corrective/Preventive Action)
    │   └── CAPA_AAAAMMDD_NN/
    │       ├── Identificacao.pdf
    │       ├── Analise_Risco.pdf
    │       ├── Plano_Acao.pdf
    │       ├── Implementacao/
    │       ├── Verificacao_Eficacia.pdf
    │       └── Encerramento.pdf
    ├── 07_Reclamacoes_Clientes/AAAA/            (cópia/link 30_Comercial)
    │   └── REC_AAAAMMDD_NN/
    │       ├── Registro.pdf
    │       ├── Classificacao_Severidade.pdf
    │       ├── Investigacao.pdf
    │       ├── Resposta_Cliente.pdf
    │       ├── CAPA_Vinculada.pdf
    │       └── Encerramento.pdf
    ├── 08_Solicitacoes_Mudanca_RDM/AAAA/        (Change Control SGQ)
    │   └── RDM_AAAAMMDD_NN/
    │       ├── Solicitacao.pdf
    │       ├── Analise_Impacto.pdf
    │       ├── Analise_Risco.pdf
    │       ├── Aprovacao.pdf
    │       ├── Implementacao.pdf
    │       └── Verificacao_Pos_Implementacao.pdf
    ├── 09_Gestao_Riscos/                        (matriz organizacional + por processo)
    │   ├── Matriz_Riscos_Estrategicos_AAAA/
    │   ├── Matriz_Riscos_Operacionais_AAAA/
    │   ├── FMEA_Processos/                      (links p/ FMEAs das áreas)
    │   └── Revisoes_Periodicas/
    ├── 10_Indicadores_KPI/AAAA/MM/
    │   ├── Indicadores_Estrategicos.pdf         (consolidado mensal)
    │   ├── Indicadores_Operacionais.csv         (link 10_Op)
    │   ├── Indicadores_RH.csv                   (link 40_RH)
    │   ├── Indicadores_SST.csv                  (link 80_SST)
    │   ├── Indicadores_Comerciais.csv           (link 30_Com)
    │   ├── Indicadores_Manutencao.csv           (link 70_Eng)
    │   └── Painel_Bordo_Diretoria.pdf
    ├── 11_Pesquisa_Satisfacao/AAAA/
    │   ├── Pesquisa_Aplicada.pdf
    │   ├── Respostas_Tabuladas.xlsx
    │   ├── Analise_NPS.pdf
    │   └── Plano_Acao_Insatisfacao.pdf
    ├── 12_Treinamentos_SGQ/AAAA/                (link 40_RH; foco SGQ)
    │   ├── Conscientizacao_Politica_Qualidade/
    │   ├── Treinamento_POPs_SGQ/
    │   └── Reciclagem_Anual/
    ├── 13_Lista_Mestra_Distribuicao/            (controle cópias controladas físicas/digitais)
    │   ├── Distribuicao_Vigente.xlsx
    │   └── Devolucao_Obsoletos/
    ├── 14_Comunicacoes_Internas/AAAA/
    │   ├── Comunicados_Diretoria/
    │   ├── Boletim_Qualidade_Mensal/
    │   └── Murais/
    ├── 15_Licoes_Aprendidas/AAAA/
    │   └── LIC_AAAAMMDD_Tema/
    │       ├── Caso.pdf
    │       ├── Analise.pdf
    │       ├── Aprendizado.pdf
    │       └── Disseminacao.pdf
    ├── 16_Qualificacao_Fornecedores/
    │   └── FORNECEDOR_CNPJ_Nome/
    │       ├── Qualificacao_Inicial.pdf
    │       ├── Documentos_Habilitacao/          (CNPJ, alvará, licenças)
    │       ├── Avaliacao_Periodica/AAAA/        (anual: prazo, qualidade, NCs)
    │       ├── Auditoria_Fornecedor/AAAA/       (se exigida — fornecedor crítico)
    │       └── Status_Aprovacao.pdf
    └── 17_Auditorias_Fornecedores/AAAA/         (auditorias enviadas pela CME)
        └── AUDIT_AAAAMMDD_Fornecedor/
            ├── Plano.pdf
            ├── Relatorio.pdf
            ├── NCs.pdf
            └── Plano_Acao_Fornecedor.pdf
```

**Doc types SGQ:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `SGQ_MANUAL` | Manual Qualidade | Internal | indef (vigente) | sim (RT+Diretoria) | versao |
| `SGQ_POL` | Política | Internal | indef | sim (Diretoria) | tipo |
| `SGQ_POP` | POP Sistêmico | Internal | indef | sim (Qualidade) | norma |
| `SGQ_LMD` | Lista Mestra | Internal | indef | não (sistêmica) | — |
| `SGQ_ACD` | Análise Crítica Direção | Restricted | indef | sim (Diretoria) | ano |
| `SGQ_AI` | Auditoria Interna | Internal | 5a | sim (Qualidade) | ano, escopo |
| `SGQ_AE` | Auditoria Externa | Restricted | 10a | sim (Qualidade+Diretoria) | ano, origem |
| `SGQ_NC` | Não-Conformidade | Internal | 5a | sim (Qualidade) | severidade |
| `SGQ_CAPA` | CAPA | Internal | 5a | sim (Qualidade) | nc_id |
| `SGQ_RDM` | Solicitação Mudança | Internal | 5a | sim (RT+Qualidade) | impacto |
| `SGQ_FMEA` | Análise Risco | Internal | indef | sim (RT) | processo |
| `SGQ_PSAT` | Pesquisa Satisfação | Internal | 5a | não | ano |
| `SGQ_FORN_QUAL` | Qualificação Fornecedor | Internal | vigência+5a | sim (Qualidade) | fornecedor_id |
| `SGQ_LIC_APR` | Lição Aprendida | Internal | indef | não | tema |
| `SGQ_KPI` | Indicador KPI | Internal | 5a | não | mes, area |

**Workflow CAPA-NC:**
1. NC identificada (auditoria, reclamação, processo, fornecedor) → `SGQ_NC` rascunho
2. Disposição imediata em 24h (correção)
3. Investigação causa raiz em ≤15d (5 porquês + Ishikawa)
4. Avaliação risco → decisão abrir CAPA ou só correção
5. Se CAPA: `SGQ_CAPA` aberta com plano ação + responsável + prazo
6. Implementação rastreada via activities
7. Verificação eficácia 30/60/90d (configurável por tipo)
8. Encerramento exige aprovação Qualidade

**Workflow auditoria interna:**
- Cronograma anual em `10_Cronograma_Anual_SGQ/Cronograma_Auditorias_Internas_AAAA.pdf`
- Cada auditoria cria `SGQ_AI` com plano, checklist, relatório, NCs vinculadas
- NCs auditoria geram `SGQ_NC` automaticamente (link)
- Recorrência ≥2 auditorias → análise tendência (input ACD)

---

### 20_Regulatorio (detalhado)

```
20_Regulatorio/
├── Documentos/
│   ├── 01_Constituicao_Empresa/
│   │   ├── Contrato_Social_Atual.pdf
│   │   ├── Alteracoes_Contratuais/AAAA/
│   │   ├── CNPJ_Cartao.pdf
│   │   ├── Inscricao_Estadual.pdf
│   │   ├── Inscricao_Municipal_CCM.pdf
│   │   ├── Procuracoes_Vigentes/
│   │   └── Atas_Assembleias/AAAA/
│   ├── 02_Licencas_Sanitarias/
│   │   ├── AFE_Autorizacao_Funcionamento_Empresa/  (ANVISA)
│   │   │   ├── AFE_Vigente.pdf
│   │   │   ├── Numero_Processo.pdf
│   │   │   └── Versoes_Anteriores/
│   │   ├── AE_Autorizacao_Especial/                (se controlados)
│   │   ├── Licenca_Sanitaria_VISA_Municipal/
│   │   │   ├── LS_Vigente.pdf
│   │   │   └── Versoes_Anteriores/
│   │   ├── Licenca_Sanitaria_VISA_Estadual/        (se aplica)
│   │   ├── Alvara_Funcionamento_Prefeitura/
│   │   ├── AVCB_Bombeiros/                         (cópia 70_Eng + cobertura regulatória)
│   │   ├── Licenca_Ambiental/                      (CETESB ou órgão estadual)
│   │   ├── Licenca_Operacao_Caldeira/              (se aplica — NR-13)
│   │   ├── CNES/                                   (CME terceira pode exigir)
│   │   └── Outros_Registros/
│   ├── 03_Responsabilidade_Tecnica/
│   │   ├── RT_Titular/
│   │   │   ├── Termo_Indicacao_RT.pdf
│   │   │   ├── Diploma_Registro_Conselho.pdf      (COREN/CRF/CRBM/CREA conforme caso)
│   │   │   ├── Curriculo_RT.pdf
│   │   │   ├── Comprovante_Vinculo.pdf
│   │   │   └── Comunicacao_ANVISA_VISA.pdf
│   │   ├── RT_Substituto/                          (mesma estrutura)
│   │   ├── ARTs_Anotacoes_Responsabilidade_Tecnica/AAAA/
│   │   └── Historico_RTs/                          (sucessões)
│   ├── 04_Politicas_Compliance/
│   │   ├── Programa_Compliance.pdf
│   │   ├── Codigo_Conduta_Etica.pdf                (cópia 40_RH)
│   │   ├── Politica_Anti_Suborno_Anti_Corrupcao.pdf  (Lei 12.846)
│   │   ├── Politica_Brindes_Hospitalidade.pdf
│   │   ├── Politica_Conflito_Interesse.pdf
│   │   ├── Politica_Concorrencial_CADE.pdf
│   │   └── Canal_Denuncias_Ouvidoria.pdf
│   ├── 05_LGPD/
│   │   ├── Politica_Privacidade.pdf
│   │   ├── Politica_Cookies.pdf                    (se site público)
│   │   ├── Designacao_DPO_Encarregado.pdf
│   │   ├── ROPA_Registro_Atividades_Tratamento.xlsx  (Art. 37 LGPD)
│   │   ├── DPIA_RIPD_Modelo.pdf                    (relatório impacto)
│   │   ├── Politica_Retencao_Dados.pdf
│   │   ├── Politica_Resposta_Incidentes.pdf
│   │   ├── Politica_Direitos_Titulares.pdf
│   │   ├── Termos_LGPD_Funcionarios.pdf
│   │   ├── Termos_LGPD_Clientes.pdf
│   │   ├── Termos_LGPD_Fornecedores.pdf
│   │   └── POPs_LGPD/
│   │       ├── POP-LGPD-001_Atendimento_Titular.pdf
│   │       ├── POP-LGPD-002_Resposta_Incidente.pdf
│   │       └── POP-LGPD-003_Avaliacao_Impacto.pdf
│   ├── 06_Manuais_Tecnicos_Regulatorios/
│   │   ├── Manual_Boas_Praticas_Reprocessamento.pdf  (interno baseado RDC 15)
│   │   ├── RDC_15_2012_Anotado.pdf                 (cópia anotada)
│   │   ├── RDC_222_2018_PGRSS_Anotado.pdf
│   │   ├── RDC_156_2006_SUD_Anotado.pdf            (se aplica)
│   │   ├── NR-32_Anotada.pdf
│   │   ├── Comparativo_Normas_Aplicaveis.xlsx
│   │   └── Mapa_Norma_X_Documento.xlsx             (matriz cobertura)
│   └── 07_Cronograma_Renovacoes/
│       ├── Cronograma_Renovacoes_AAAA.xlsx        (todas licenças com validade)
│       ├── Plano_Acao_Renovacoes.pdf
│       └── Alertas_Configurados/                   (referência cron afr_ecm)
└── Registros/
    ├── 01_Solicitacoes_Peticoes_ANVISA/AAAA/
    │   └── PET_AAAAMMDD_Tipo/
    │       ├── Protocolo_Peticao.pdf
    │       ├── Documentacao_Suporte/
    │       ├── Resposta_Exigencias/
    │       ├── Despacho_Final.pdf
    │       └── Publicacao_DOU.pdf
    ├── 02_Renovacoes_Licencas/AAAA/
    │   └── REN_Tipo_AAAA/                          (AFE, LS, alvará, etc)
    │       ├── Protocolo_Renovacao.pdf
    │       ├── Documentos_Apresentados/
    │       ├── Pagamentos_Taxas.pdf
    │       ├── Vistoria_Realizada/
    │       └── Licenca_Atualizada.pdf
    ├── 03_Inspecoes_Sanitarias_VISA/AAAA/
    │   └── INSP_AAAAMMDD_Origem/                   (VISA municipal/estadual/ANVISA)
    │       ├── Auto_Inspecao.pdf
    │       ├── Termo_Inspecao.pdf
    │       ├── Notificacoes/                       (se aplicáveis)
    │       ├── Plano_Acao_Resposta.pdf
    │       ├── Recursos_Defesas/
    │       └── Encerramento.pdf
    ├── 04_Notificacoes_Multas_Sancoes/AAAA/
    │   └── NOTIF_AAAAMMDD_NN/
    │       ├── Auto_Infracao.pdf
    │       ├── Defesa_Recurso.pdf
    │       ├── Decisao_Final.pdf
    │       └── Pagamento_Cumprimento.pdf
    ├── 05_Tecnovigilancia/AAAA/                    (cópia/link 10_Op/Tecnovigilancia)
    │   └── EVENTO_AAAAMMDD/
    │       ├── Identificacao_Evento.pdf
    │       ├── Notificacao_NOTIVISA.pdf            (Portal ANVISA)
    │       ├── Investigacao/
    │       ├── Acao_Corretiva.pdf
    │       └── Encerramento.pdf
    ├── 06_LGPD_Operacao/
    │   ├── Requisicoes_Titulares/AAAA/
    │   │   └── REQ_AAAAMMDD_TipoSolicitacao/       (acesso, correção, eliminação, portabilidade)
    │   │       ├── Solicitacao.pdf
    │   │       ├── Verificacao_Identidade.pdf
    │   │       ├── Resposta.pdf
    │   │       └── Comprovante_Atendimento.pdf
    │   ├── Incidentes_Vazamento_Dados/AAAA/
    │   │   └── INC_AAAAMMDD_NN/
    │   │       ├── Identificacao.pdf
    │   │       ├── Avaliacao_Risco.pdf
    │   │       ├── Notificacao_ANPD.pdf            (se aplicável)
    │   │       ├── Comunicacao_Titulares.pdf       (se exigida)
    │   │       ├── Investigacao_Causa.pdf
    │   │       └── Plano_Acao_Mitigacao.pdf
    │   ├── DPIAs_Realizadas/                       (Avaliação Impacto p/ tratamentos de risco)
    │   ├── Treinamentos_LGPD/AAAA/                 (cópia/link 40_RH)
    │   └── Auditorias_LGPD/AAAA/
    ├── 07_Denuncias_Canal_Compliance/AAAA/
    │   └── DEN_AAAAMMDD_NN/                        (CONFIDENCIAL — acesso restrito)
    │       ├── Registro_Anonimo.pdf
    │       ├── Investigacao.pdf
    │       ├── Conclusao.pdf
    │       └── Acao_Disciplinar_Encaminhada.pdf    (link 40_RH se aplicável)
    ├── 08_Auditorias_Compliance/AAAA/              (Lei 12.846 due diligence)
    ├── 09_Reunioes_RT_Diretoria/AAAA/              (atas decisões regulatórias críticas)
    ├── 10_Comunicacoes_ANVISA_VISA/AAAA/
    │   ├── Recebidas/
    │   └── Enviadas/
    └── 11_Indicadores_Regulatorio/AAAA/MM/
        ├── Status_Licencas.csv                     (vigência por licença)
        ├── Aderencia_Cronograma_Renovacao.csv
        ├── Notificacoes_Recebidas.csv
        └── Eventos_Tecnovigilancia.csv
```

**Doc types Regulatório:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `REG_AFE` | AFE ANVISA | Restricted | indef + vigência | sim (Diretoria+RT) | validade_data, numero |
| `REG_AE` | AE ANVISA | Restricted | indef + vigência | sim (Diretoria+RT) | validade_data |
| `REG_LS` | Licença Sanitária | Restricted | indef + vigência | sim (RT) | validade_data, esfera |
| `REG_ALVARA` | Alvará Funcionamento | Restricted | vigência+5a | sim | validade_data |
| `REG_RT` | Documentação RT | Restricted | indef | sim (Diretoria) | nome_rt, conselho |
| `REG_ART` | ART | Restricted | 5a pós-encerramento | sim | servico, ano |
| `REG_PET` | Petição ANVISA | Restricted | 10a | sim (RT) | protocolo |
| `REG_INSP_VISA` | Inspeção VISA | Restricted | 10a | sim (RT) | data, origem |
| `REG_NOTIF` | Notificação/Multa | Restricted | 10a | sim (Jurídico+RT) | numero_auto |
| `REG_TEC` | Tecnovigilância | Confidential | 10a | sim (RT) | cliente_id, lote |
| `REG_LGPD_REQ` | Requisição Titular | Confidential | 5a | sim (DPO) | titular, tipo |
| `REG_LGPD_INC` | Incidente LGPD | Confidential | 10a | sim (DPO+Diretoria) | severidade |
| `REG_DPIA` | DPIA/RIPD | Restricted | indef | sim (DPO+RT) | tratamento |
| `REG_DEN` | Denúncia Compliance | Confidential | 10a | sim (Comitê Ética) | severidade |
| `REG_AUDIT_COMP` | Auditoria Compliance | Restricted | 5a | sim (Diretoria) | ano |

**Workflow renovação de licenças (crítico — operação para se vencer):**
1. Doc com `validade_data` preenchida → cron `afr_ecm` calcula `expiration_status`
2. Alerta `warning` em 90/60/30d antes vencimento → activity p/ RT
3. RT abre processo renovação → cria pasta `02_Renovacoes_Licencas/AAAA/REN_*`
4. Protocolo apresentado → atualiza `dms.file` com referência protocolo
5. Licença atualizada → upload substituindo vigente, marca antiga `obsoleto=True`
6. KPI `Status_Licencas.csv` atualizado mensalmente

**Workflow LGPD incidente:**
1. Incidente detectado → `REG_LGPD_INC` rascunho + DPO notificado
2. Avaliação risco em ≤48h
3. Se risco alto → notificação ANPD ≤72h após conhecimento
4. Comunicação titulares se risco material relevante
5. Investigação causa raiz → CAPA via SGQ
6. Encerramento exige aprovação DPO + Diretoria

**Integração tecnovigilância 10_Op ↔ 20_Reg:**
- Evento adverso reportado por cliente → cria `OP_TEC` em 10_Op
- Se exige NOTIVISA → workflow automático cria `REG_TEC` em 20_Reg vinculado
- Notificação portal ANVISA registrada → DOI/protocolo anexado
- Recall associado (se necessário) vinculado via `OP_RECALL`

### 10_Operacao (detalhado)

Estrutura segue fluxo CME conforme RDC 15/2012 (etapas obrigatórias) + req. ISO 17665/11135/15883.

```
10_Operacao/
├── Documentos/
│   ├── 01_Governanca_Processo/
│   │   ├── Plano_Mestre_Validacao_PMV/        (VMP global)
│   │   ├── Politica_Reprocessamento/
│   │   ├── Lista_Produtos_Reprocessaveis/     (matriz PPS × processo aprovado)
│   │   ├── Lista_Produtos_NAO_Reprocessaveis/ (proibidos)
│   │   ├── Politica_Liberacao_Carga/          (paramétrica vs IB)
│   │   ├── Politica_Recall/
│   │   └── Politica_Reprocessamento_SUD/      (se aplicável — RDC 156)
│   ├── 02_POPs_Reprocessamento/
│   │   ├── 01_Recepcao_PPS/
│   │   │   ├── POP-OP-001_Recebimento_Coleta_Cliente.pdf
│   │   │   ├── POP-OP-002_Triagem_Conferencia.pdf
│   │   │   └── POP-OP-003_Rastreabilidade_Entrada.pdf
│   │   ├── 02_Pre_Limpeza/                    (descontaminação inicial)
│   │   ├── 03_Limpeza_Manual/
│   │   │   ├── POP-OP-010_Limpeza_Manual_Geral.pdf
│   │   │   ├── POP-OP-011_Limpeza_Endoscopios/
│   │   │   └── POP-OP-012_Limpeza_Instrumentos_Microcirurgia/
│   │   ├── 04_Limpeza_Automatizada/
│   │   │   ├── POP-OP-020_Operacao_Lavadora_Termodesinfectora.pdf  (ISO 15883)
│   │   │   ├── POP-OP-021_Lavadora_Ultrassonica.pdf
│   │   │   └── POP-OP-022_Lavadora_Endoscopios.pdf
│   │   ├── 05_Secagem/
│   │   ├── 06_Inspecao_Funcional/
│   │   │   ├── POP-OP-030_Inspecao_Visual_Lupas.pdf
│   │   │   ├── POP-OP-031_Teste_Funcional_Instrumentos.pdf
│   │   │   └── POP-OP-032_Lubrificacao.pdf
│   │   ├── 07_Preparo_Montagem/
│   │   │   ├── POP-OP-040_Montagem_Kits_Cirurgicos.pdf
│   │   │   └── POP-OP-041_Identificacao_Itens.pdf
│   │   ├── 08_Embalagem/
│   │   │   ├── POP-OP-050_Embalagem_Grau_Cirurgico.pdf
│   │   │   ├── POP-OP-051_Embalagem_SMS.pdf
│   │   │   ├── POP-OP-052_Embalagem_Container.pdf
│   │   │   └── POP-OP-053_Selagem_Termica.pdf  (validação seladora ISO 11607)
│   │   ├── 09_Esterilizacao/
│   │   │   ├── Vapor_Saturado/                (ISO 17665)
│   │   │   │   ├── POP-OP-060_Operacao_Autoclave.pdf
│   │   │   │   ├── POP-OP-061_Bowie_Dick_Diario.pdf
│   │   │   │   ├── POP-OP-062_Teste_Vacuo_Diario.pdf
│   │   │   │   └── POP-OP-063_Carga_Distribuicao.pdf
│   │   │   ├── Peroxido_Hidrogenio/           (ISO 22441)
│   │   │   ├── ETO_Oxido_Etileno/             (ISO 11135)
│   │   │   ├── Formaldeido/                   (ISO 25424)
│   │   │   └── Ozonio/
│   │   ├── 10_Monitoramento_Carga/
│   │   │   ├── POP-OP-070_Indicadores_Quimicos.pdf  (ISO 11140)
│   │   │   ├── POP-OP-071_Indicadores_Biologicos.pdf (ISO 11138)
│   │   │   ├── POP-OP-072_Indicadores_Fisicos.pdf
│   │   │   └── POP-OP-073_Posicionamento_PCD.pdf    (Process Challenge Device)
│   │   ├── 11_Liberacao_Carga/
│   │   │   ├── POP-OP-080_Liberacao_Parametrica.pdf
│   │   │   ├── POP-OP-081_Liberacao_Com_IB.pdf
│   │   │   ├── POP-OP-082_Quarentena_Aguardo_IB.pdf
│   │   │   └── POP-OP-083_Liberacao_Excepcional.pdf
│   │   ├── 12_Armazenamento_Arsenal/
│   │   │   ├── POP-OP-090_Estocagem_Esteril.pdf
│   │   │   ├── POP-OP-091_Validade_Embalagem.pdf  (eventual vs time-related)
│   │   │   └── POP-OP-092_PEPS_FEFO.pdf
│   │   ├── 13_Transporte_Distribuicao/
│   │   │   ├── POP-OP-100_Caixas_Transporte_Esteril.pdf
│   │   │   ├── POP-OP-101_Coleta_Entrega_Cliente.pdf
│   │   │   └── POP-OP-102_Higienizacao_Veiculos_Caixas.pdf
│   │   ├── 14_Recall_Tecnovigilancia/
│   │   │   ├── POP-OP-110_Recall_Lote.pdf
│   │   │   ├── POP-OP-111_Quarentena_Suspeito.pdf
│   │   │   └── POP-OP-112_Notificacao_Cliente.pdf
│   │   ├── 15_Reprocessamento_SUD/            (se RDC 156 — opcional)
│   │   │   ├── POP-OP-120_Triagem_SUD.pdf
│   │   │   ├── POP-OP-121_Limites_Reprocessamento.pdf
│   │   │   └── POP-OP-122_Identificacao_Ciclos_SUD.pdf
│   │   └── 16_Higienizacao_Areas/
│   │       ├── POP-OP-130_Limpeza_Sala_Suja.pdf
│   │       ├── POP-OP-131_Limpeza_Sala_Limpa.pdf
│   │       ├── POP-OP-132_Limpeza_Area_Esteril.pdf
│   │       └── POP-OP-133_Descarte_Residuos.pdf  (PGRSS)
│   ├── 03_Instrucoes_Trabalho/
│   │   ├── IT-EQ-XX_Operacao_Autoclave_AC01.pdf  (uma IT por equipamento)
│   │   ├── IT-EQ-YY_Operacao_Lavadora_LV02.pdf
│   │   └── ...
│   ├── 04_Formularios_Mestres/
│   │   ├── FORM-OP-001_Checklist_Recebimento.pdf
│   │   ├── FORM-OP-002_Ficha_Carga_Esterilizacao.pdf
│   │   ├── FORM-OP-003_Liberacao_Carga.pdf
│   │   ├── FORM-OP-004_Recall.pdf
│   │   ├── FORM-OP-005_Quarentena.pdf
│   │   └── FORM-OP-006_Liberacao_Excepcional.pdf
│   ├── 05_Fluxogramas/
│   │   ├── Fluxo_Geral_CME.pdf
│   │   ├── Fluxo_Recall.pdf
│   │   ├── Fluxo_NC_Operacional.pdf
│   │   └── Mapa_Areas_Fisicas.pdf            (planta baixa: suja/limpa/estéril)
│   ├── 06_Tabelas_Tecnicas/
│   │   ├── Compatibilidade_Detergentes.pdf
│   │   ├── Parametros_Ciclos_Validados/      (por equipamento + receita)
│   │   ├── Tempo_Validade_Embalagens.pdf
│   │   ├── Lista_Materiais_Embalagem.pdf
│   │   └── Especificacoes_Agua_Reuso.pdf
│   ├── 07_URS_Specs/                          (User Requirement Specs por equipamento)
│   └── 08_Analise_Risco/
│       ├── HACCP_Processo/
│       ├── FMEA_Processo/                    (ISO 14971-style)
│       └── Avaliacao_Risco_Mudanca/          (change control assessments)
└── Registros/
    ├── 01_Validacao_Processo/
    │   └── Equipamento_XX/                   (uma pasta por equipamento crítico)
    │       ├── 01_URS_Aceite_Fornecedor/
    │       ├── 02_DQ_Design_Qualification/
    │       ├── 03_IQ_Instalacao/
    │       │   ├── Protocolo_IQ.pdf
    │       │   ├── Relatorio_IQ.pdf
    │       │   ├── Lista_Componentes.pdf
    │       │   ├── Calibracao_Inicial/
    │       │   └── Aprovacao_RT.pdf
    │       ├── 04_OQ_Operacional/
    │       │   ├── Protocolo_OQ.pdf
    │       │   ├── Relatorio_OQ.pdf
    │       │   ├── Mapeamento_Termico_Camara_Vazia.pdf
    │       │   ├── Testes_Alarmes_Seguranca.pdf
    │       │   └── Aprovacao_RT.pdf
    │       ├── 05_PQ_Performance/
    │       │   ├── Protocolo_PQ.pdf
    │       │   ├── Relatorio_PQ.pdf
    │       │   ├── Mapeamento_Termico_Carga_Referencia.pdf
    │       │   ├── Carga_Pior_Caso_Worst_Case.pdf
    │       │   ├── Half_Cycle_Microbiologico.pdf
    │       │   ├── Bioburden/                (se aplicável)
    │       │   └── Aprovacao_RT.pdf
    │       ├── 06_Requalificacao_Anual/AAAA/
    │       ├── 07_Revalidacao_Mudancas/      (após mudança significativa)
    │       └── 08_Relatorio_Final_Validacao/
    ├── 02_Validacao_Embalagem_Selagem/        (ISO 11607)
    │   └── Seladora_XX/
    │       ├── IQ_OQ_PQ_Seladora/
    │       └── Testes_Integridade_Selagem/AAAA/
    ├── 03_Validacao_Lavagem/                  (ISO 15883)
    │   └── Lavadora_XX/
    │       ├── IQ_OQ_PQ/
    │       ├── Teste_Eficacia_Limpeza/AAAA/  (proteína, ATP, sangue residual)
    │       └── Requalificacao_Anual/AAAA/
    ├── 04_Monitoramentos_Rotineiros/
    │   ├── Bowie_Dick/AAAA/MM/                (PDFs fitas teste)
    │   ├── Teste_Vacuo/AAAA/MM/
    │   ├── Mapeamento_Termico_Periodico/AAAA/
    │   └── Resumos_Ciclos/AAAA/MM/            (consolidado mensal; diário em afr_supervisorio_ciclos)
    ├── 05_Monitoramento_Utilidades/
    │   ├── Agua/
    │   │   ├── Potabilidade/AAAA/MM/
    │   │   ├── Condutividade/AAAA/MM/
    │   │   ├── Dureza/AAAA/MM/
    │   │   ├── pH/AAAA/MM/
    │   │   └── Endotoxina/AAAA/               (água p/ enxágue final crítico)
    │   ├── Vapor/
    │   │   ├── Qualidade_Vapor/AAAA/          (EN 285: não-condensáveis, dryness, superheat)
    │   │   └── Pureza_Quimica/AAAA/
    │   ├── Ar_Comprimido/AAAA/
    │   └── Energia_UPS/                       (relatos quedas energia, log no-break)
    ├── 06_Monitoramento_Ambiente/
    │   ├── Temperatura_Umidade/
    │   │   ├── Sala_Suja/AAAA/MM/
    │   │   ├── Sala_Preparo/AAAA/MM/
    │   │   ├── Sala_Esterilizacao/AAAA/MM/
    │   │   └── Arsenal/AAAA/MM/
    │   ├── Pressao_Diferencial_Salas/AAAA/MM/
    │   ├── Particulas_Viaveis_Nao_Viaveis/   (se sala classificada)
    │   └── Higienizacao_Salas/AAAA/MM/        (checklists assinados)
    ├── 07_Eventos_Criticos/
    │   ├── Lotes_BI_Positivos/AAAA/
    │   │   └── EVENTO_AAAAMMDD_LoteXX/
    │   │       ├── Notificacao.pdf
    │   │       ├── Quarentena.pdf
    │   │       ├── Investigacao_Causa_Raiz.pdf
    │   │       ├── Recall_Cliente.pdf
    │   │       ├── CAPA.pdf
    │   │       └── Encerramento.pdf
    │   ├── Falhas_Ciclo/AAAA/
    │   ├── Desvios_Limpeza/AAAA/
    │   ├── Liberacao_Excepcional/AAAA/        (registros + análise risco)
    │   └── Reprocessos_Internos/AAAA/         (PPS reprocessados por falha)
    ├── 08_Recalls/AAAA/
    │   └── RECALL_AAAAMMDD_LoteXX/
    │       ├── Decisao_Recall.pdf
    │       ├── Lista_Clientes_Afetados.pdf
    │       ├── Comunicacao_Cliente/
    │       ├── Retorno_Materiais.pdf
    │       ├── Disposicao_Final.pdf
    │       └── Notificacao_VISA.pdf          (tecnovigilância se aplicável)
    ├── 09_Tecnovigilancia/AAAA/
    │   └── EVENTO_AAAAMMDD/
    │       ├── Notificacao_NOTIVISA.pdf
    │       ├── Investigacao.pdf
    │       └── Acao_Corretiva.pdf
    ├── 10_Auditorias_Operacionais_Internas/AAAA/
    ├── 11_Reuniao_Operacional/AAAA/MM/        (atas turno, passagem)
    ├── 12_Indicadores_Operacionais/AAAA/MM/
    │   ├── Taxa_NC_Operacional.csv
    │   ├── Taxa_Recall.csv
    │   ├── Lead_Time_Reprocessamento.csv
    │   ├── Taxa_Retrabalho.csv
    │   ├── BI_Positivos_Mensais.csv
    │   └── OEE_Esterilizadores.csv
    └── 13_Mudancas_Operacionais_Change_Control/
        └── CC_AAAAMMDD_NN/
            ├── Solicitacao.pdf
            ├── Analise_Risco.pdf
            ├── Plano_Implementacao.pdf
            ├── Validacao_Pos_Mudanca.pdf
            └── Aprovacao_RT.pdf
```

**Doc types Odoo (afr_ecm) específicos da Operação:**

| `code` | Nome | Confidencialidade | Retenção | Aprovação | Metadata extra |
|---|---|---|---|---|---|
| `OP_POP` | POP Reprocessamento | Internal | indef (até substituir) | sim (RT) | processo, norma |
| `OP_IT_EQ` | IT Equipamento | Internal | indef | sim (Eng+RT) | equipamento_id |
| `OP_FORM` | Formulário Mestre | Internal | indef | sim (Qualidade) | processo |
| `OP_VAL_IQ` | Relatório IQ | Restricted | vida útil+5a | sim (RT) | equipamento_id |
| `OP_VAL_OQ` | Relatório OQ | Restricted | vida útil+5a | sim (RT) | equipamento_id |
| `OP_VAL_PQ` | Relatório PQ | Restricted | vida útil+5a | sim (RT) | equipamento_id |
| `OP_REQUAL` | Requalificação | Restricted | 5a | sim (RT) | equipamento_id, ano |
| `OP_MON_BD` | Bowie-Dick / Vácuo | Internal | 5a | não | equipamento_id, data |
| `OP_MON_AGUA` | Monitoramento Água | Internal | 5a | sim (Qualidade) | mes |
| `OP_MON_AMB` | Monit. Ambiente | Internal | 5a | sim (Qualidade) | sala, mes |
| `OP_BI_POS` | BI Positivo | Restricted | 10a | sim (RT) | lote_id, equipamento_id |
| `OP_RECALL` | Recall | Restricted | 10a | sim (RT+Diretoria) | lote_id, cliente_id |
| `OP_LIB_EXC` | Liberação Excepcional | Restricted | 5a | sim (RT) | lote_id |
| `OP_CC` | Change Control | Restricted | 5a | sim (RT+Diretoria) | — |
| `OP_FMEA` | Análise Risco | Internal | indef | sim (RT) | processo |
| `OP_TEC` | Tecnovigilância | Confidential | 10a | sim (RT) | cliente_id |

**Workflow especial — Lote BI positivo (POP-OP-110 + integração afr_supervisorio_ciclos):**
1. Sistema operacional (afr_supervisorio_ciclos) detecta BI+ → cria registro no ECM (`OP_BI_POS`) automaticamente
2. ECM dispara workflow: quarentena lote → notificação RT+Qualidade+Diretoria → activity
3. Investigação anexada (causa raiz, 5 porquês, Ishikawa)
4. Se confirma esterilização falha: criar `OP_RECALL` automaticamente com `lote_id` e `cliente_ids` afetados
5. CAPA aberta via NC link
6. Notificação VISA se exigida (NOTIVISA) → `OP_TEC`

**Integração com transacional (`afr_supervisorio_ciclos`):**
- Ciclo diário não duplica no ECM
- Sumário mensal (PDF agregado) gerado por cron → arquivado em `Resumos_Ciclos/AAAA/MM/`
- BI positivo, falha ciclo, liberação excepcional: criam doc estático no ECM com link `cycle_id` (m2o)
- Validação (IQ/OQ/PQ) referencia equipamento_id do mesmo cadastro Odoo

### 20_Regulatorio
```
20_Regulatorio/
├── Documentos/
│   ├── AFE_Autorizacao_Funcionamento/
│   ├── AE_Autorizacao_Especial/
│   ├── Licenca_Sanitaria_Municipal/
│   ├── Alvara_Funcionamento/
│   ├── CNES/
│   ├── Responsabilidade_Tecnica/          (RT, ART, substituto)
│   ├── Contrato_Social_CNPJ/
│   ├── Politicas_LGPD_Compliance/
│   └── Manual_Boas_Praticas/              (referência interna)
└── Registros/
    ├── Inspecoes_VISA/AAAA/
    ├── Renovacoes/AAAA/
    ├── Peticoes_ANVISA/AAAA/
    ├── Notificacoes_Eventos_Adversos/AAAA/
    ├── Tecnovigilancia/AAAA/
    └── Auditorias_Recebidas_Cliente/AAAA/
```

### 30_Comercial (detalhado)

```
30_Comercial/
├── Documentos/
│   ├── 01_Politica_Comercial/
│   ├── 02_Modelos_Contratuais/
│   │   ├── Contrato_Prestacao_CME.docx
│   │   ├── Quality_Agreement_QA.docx        (acordo qualidade — req. ISO 13485 cl. 7.4)
│   │   ├── SLA_Modelo.docx
│   │   ├── Aditivo_Modelo.docx
│   │   ├── Termo_Confidencialidade_NDA.docx
│   │   └── Termo_LGPD_DPA.docx              (Data Processing Agreement)
│   ├── 03_Tabela_Servicos_Precos/AAAA/      (versionada por ano)
│   ├── 04_Catalogo_Servicos/
│   │   ├── Servicos_Esterilizacao/
│   │   ├── Servicos_Logistica/
│   │   └── Servicos_Consultoria/
│   ├── 05_Materiais_Vendas/
│   │   ├── Apresentacoes/
│   │   ├── Folders_Brochures/
│   │   └── Cases_Sucesso/
│   ├── 06_Politica_Atendimento_Reclamacoes/
│   └── 07_Procedimentos_Comerciais/
│       ├── POP-COM-001_Onboarding_Cliente.pdf
│       ├── POP-COM-002_Renovacao_Contrato.pdf
│       ├── POP-COM-003_Tratamento_Reclamacao.pdf
│       ├── POP-COM-004_Encerramento_Contrato.pdf
│       └── POP-COM-005_Pesquisa_Satisfacao.pdf
└── Registros/
    ├── 01_Clientes_Ativos/
    │   └── CNPJ_NomeReduzido/                  (ex: 12345678000199_HOSPITAL_X)
    │       ├── 01_Cadastro/
    │       │   ├── Ficha_Cliente.pdf
    │       │   ├── Contrato_Social.pdf
    │       │   ├── Comprovante_Endereco.pdf
    │       │   ├── Cartao_CNPJ.pdf
    │       │   ├── Licenca_Sanitaria_Cliente.pdf
    │       │   └── Responsavel_Tecnico_Cliente.pdf
    │       ├── 02_Contrato_Vigente/
    │       │   ├── Contrato_Original_Assinado.pdf
    │       │   ├── QA_Quality_Agreement_Assinado.pdf
    │       │   ├── SLA_Assinado.pdf
    │       │   ├── DPA_LGPD_Assinado.pdf
    │       │   └── Procuracao.pdf
    │       ├── 03_Aditivos/
    │       │   └── ADITIVO_NN_AAAAMMDD/
    │       ├── 04_Especificacoes_Tecnicas_Cliente/
    │       │   ├── Lista_PPS_Atendidos.pdf     (catálogo materiais cliente)
    │       │   ├── Particularidades_Embalagem/
    │       │   └── Janelas_Coleta_Entrega/
    │       ├── 05_Auditorias_Recebidas/AAAA/
    │       │   └── AUDIT_AAAAMMDD/
    │       │       ├── Plano_Auditoria.pdf
    │       │       ├── Relatorio_Auditoria.pdf
    │       │       ├── NCs_Apontadas.pdf
    │       │       ├── Plano_Acao_Resposta.pdf
    │       │       └── Encerramento.pdf
    │       ├── 06_Comunicacoes_Oficiais/AAAA/
    │       │   ├── Cartas_Recebidas/
    │       │   ├── Cartas_Enviadas/
    │       │   ├── Notificacoes_Recall_Enviadas/  (link 10_Op/Recalls)
    │       │   └── Comunicados_Tecnicos/
    │       ├── 07_Reunioes/AAAA/
    │       │   └── REUNIAO_AAAAMMDD/
    │       │       ├── Pauta.pdf
    │       │       ├── Ata.pdf
    │       │       └── Plano_Acao_Saida.pdf
    │       ├── 08_Reclamacoes/AAAA/
    │       │   └── REC_AAAAMMDD_NN/
    │       │       ├── Registro_Reclamacao.pdf
    │       │       ├── Investigacao.pdf
    │       │       ├── Resposta_Cliente.pdf
    │       │       └── CAPA_Vinculada.pdf
    │       ├── 09_Pesquisa_Satisfacao/AAAA/
    │       ├── 10_Faturamento/AAAA/MM/         (espelho NF/RPS; transacional Odoo)
    │       ├── 11_Indicadores_Cliente/AAAA/MM/ (SLA: lead time, NC, recalls — sumário p/ cliente)
    │       └── 12_LGPD/
    │           ├── Registro_Tratamento_Dados.pdf
    │           └── Incidentes_Privacidade/
    ├── 02_Clientes_Inativos_Encerrados/
    │   └── CNPJ_NomeReduzido_AAAAMMDD_Encerrado/  (mesma estrutura, congelada)
    ├── 03_Pre_Vendas_Leads/AAAA/
    │   └── LEAD_AAAAMMDD_NomeHospital/
    │       ├── Brief_Inicial.pdf
    │       ├── Visita_Tecnica/
    │       ├── Proposta_Comercial_Vnn.pdf
    │       └── Status_Negociacao.pdf
    ├── 04_Propostas_Enviadas/AAAA/
    ├── 05_Licitacoes_Editais/AAAA/             (se atua em setor público)
    │   └── LICITACAO_NN_AAAA/
    │       ├── Edital.pdf
    │       ├── Documentos_Habilitacao/
    │       ├── Proposta_Tecnica.pdf
    │       ├── Proposta_Comercial.pdf
    │       └── Resultado/
    └── 06_Indicadores_Comerciais/AAAA/MM/
        ├── Pipeline.csv
        ├── Taxa_Renovacao.csv
        ├── Churn.csv
        └── Receita_por_Cliente.csv
```

**Doc types comerciais:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `COM_CONTRATO` | Contrato Cliente | Restricted | 5a pós-encerramento | sim (Diretoria+Jurídico) | cliente_id, validade_data |
| `COM_QA` | Quality Agreement | Restricted | 5a pós-encerramento | sim (RT+Diretoria) | cliente_id |
| `COM_SLA` | SLA | Restricted | 5a | sim (Comercial+RT) | cliente_id |
| `COM_DPA` | DPA LGPD | Confidential | 5a | sim (Jurídico) | cliente_id |
| `COM_ADITIVO` | Aditivo Contratual | Restricted | 5a | sim (Diretoria) | cliente_id, contrato_id |
| `COM_AUDIT_REC` | Auditoria Cliente Recebida | Restricted | 5a | não | cliente_id, ano |
| `COM_RECLAMACAO` | Reclamação Cliente | Restricted | 5a | sim (Qualidade) | cliente_id |
| `COM_PROPOSTA` | Proposta Comercial | Internal | 3a | não | lead_id |
| `COM_ATA_CLI` | Ata Reunião Cliente | Internal | 5a | não | cliente_id |
| `COM_LIC_EDITAL` | Edital Licitação | Internal | 5a | não | — |

**Integração:**
- `cliente_id` é m2o pra `res.partner` (mesmo cadastro Odoo)
- Faturamento NF/RPS: link p/ `account.move` (não duplicar PDF — gerar link)
- Reclamação cliente cria registro no `00_SGQ/Registros/Reclamacoes_Clientes` + link aqui

---

### 70_Engenharia_Manutencao (detalhado)

```
70_Engenharia_Manutencao/
├── Documentos/
│   ├── 01_Governanca/
│   │   ├── Politica_Manutencao.pdf
│   │   ├── Plano_Mestre_Manutencao_PMM.pdf      (mensal/anual)
│   │   ├── Politica_Calibracao.pdf              (metrologia + RBC)
│   │   ├── Politica_Spare_Parts.pdf
│   │   └── Plano_Mestre_Calibracao_PMC.pdf
│   ├── 02_Cadastro_Equipamentos/
│   │   ├── Lista_Mestra_Equipamentos.xlsx       (matriz: ID, modelo, criticidade, freq PM)
│   │   ├── Fichas_Tecnicas/                     (uma por equipamento)
│   │   │   ├── EQP-AC01_Autoclave_Baumer/
│   │   │   │   ├── Ficha_Tecnica.pdf
│   │   │   │   ├── Manual_Fabricante.pdf
│   │   │   │   ├── Manual_Pecas.pdf
│   │   │   │   ├── Diagramas_Eletricos.pdf
│   │   │   │   ├── Diagramas_Hidraulicos_Vapor.pdf
│   │   │   │   ├── Certificado_Origem.pdf
│   │   │   │   ├── Nota_Fiscal_Aquisicao.pdf
│   │   │   │   └── Termo_Garantia.pdf
│   │   │   └── EQP-LV02_Lavadora_Steelco/...
│   │   └── Layout_Planta_Equipamentos.pdf
│   ├── 03_POPs_Manutencao/
│   │   ├── POP-EM-001_Manutencao_Preventiva.pdf
│   │   ├── POP-EM-002_Manutencao_Corretiva.pdf
│   │   ├── POP-EM-003_Lockout_Tagout_LOTO.pdf   (segurança NR-12)
│   │   ├── POP-EM-004_Calibracao_Instrumentos.pdf
│   │   ├── POP-EM-005_Gestao_Estoque_Pecas.pdf
│   │   ├── POP-EM-006_Recebimento_Inspecao_Pecas.pdf
│   │   ├── POP-EM-007_Mudanca_Equipamento.pdf   (change control vinculado RT)
│   │   └── POP-EM-008_Comissionamento_Equipamento.pdf
│   ├── 04_Procedimentos_por_Equipamento/
│   │   ├── EQP-AC01/PM_Mensal.pdf
│   │   ├── EQP-AC01/PM_Semestral.pdf
│   │   ├── EQP-AC01/PM_Anual.pdf
│   │   ├── EQP-LV02/PM_*.pdf
│   │   └── ...
│   ├── 05_Utilidades/
│   │   ├── Vapor/
│   │   │   ├── Especificacao_Qualidade_Vapor.pdf  (EN 285)
│   │   │   ├── Plano_Manutencao_Caldeira.pdf
│   │   │   └── Procedimentos_Operacao_Caldeira.pdf
│   │   ├── Agua_Tratamento/
│   │   │   ├── Especificacao_Agua_Reuso.pdf
│   │   │   ├── Plano_Manutencao_ETA_Osmose.pdf
│   │   │   └── POP_Regeneracao_Resinas.pdf
│   │   ├── Ar_Comprimido/
│   │   │   ├── Especificacao_Qualidade_Ar.pdf    (ISO 8573)
│   │   │   └── Plano_Manutencao_Compressor.pdf
│   │   ├── Energia/
│   │   │   ├── Diagrama_Unifilar.pdf
│   │   │   ├── Plano_Manutencao_QGBT.pdf
│   │   │   ├── Plano_Manutencao_Gerador.pdf
│   │   │   └── Plano_Manutencao_UPS_NoBreak.pdf
│   │   └── Climatizacao_HVAC/
│   │       ├── Especificacao_Salas_Classificadas.pdf
│   │       ├── PMOC_Plano_Manutencao_Climatizacao.pdf  (Lei 13.589/2018)
│   │       └── POPs_Manutencao_HVAC.pdf
│   └── 06_Predial/
│       ├── Plantas_Arquitetonicas/
│       ├── AVCB_Auto_Vistoria_Bombeiros/
│       ├── Laudo_SPDA_Para_raios/
│       ├── Laudo_Eletrico_NR10.pdf
│       └── Laudo_Estrutural/
└── Registros/
    ├── 01_Equipamento_XX/                      (espelha cadastro)
    │   └── EQP-AC01_Autoclave_Baumer/
    │       ├── 01_Comissionamento/
    │       │   ├── Recebimento.pdf
    │       │   ├── Instalacao.pdf
    │       │   ├── Testes_Aceitacao_FAT_SAT.pdf
    │       │   └── Entrega_Operacao.pdf
    │       ├── 02_Manutencao_Preventiva/AAAA/
    │       │   └── PM_AAAAMMDD/
    │       │       ├── Ordem_Servico.pdf
    │       │       ├── Checklist_Executado.pdf
    │       │       ├── Pecas_Substituidas.pdf
    │       │       └── Relatorio_Final.pdf
    │       ├── 03_Manutencao_Corretiva/AAAA/
    │       │   └── CM_AAAAMMDD_NN/
    │       │       ├── Solicitacao.pdf
    │       │       ├── Diagnostico.pdf
    │       │       ├── Reparo_Executado.pdf
    │       │       ├── Pecas.pdf
    │       │       ├── Tempo_Parada.pdf
    │       │       └── Revalidacao_Necessaria.pdf   (gatilho re-PQ)
    │       ├── 04_Calibracao/AAAA/
    │       │   └── CAL_AAAAMMDD_Instrumento/
    │       │       ├── Certificado_RBC.pdf            (laboratório acreditado)
    │       │       ├── Etiqueta_Calibracao.pdf
    │       │       └── Aceite_Tecnico.pdf
    │       ├── 05_Historico_Falhas_MTBF/
    │       ├── 06_Modificacoes_Change_Control/        (link 10_Op/13_Mudancas)
    │       └── 07_Backup_Software_Firmware/           (parametrização salva)
    ├── 02_Utilidades_Operacao/
    │   ├── Caldeira_Vapor/
    │   │   ├── Operacao_Diaria/AAAA/MM/
    │   │   ├── NR13_Inspecao_Anual/AAAA/             (vaso pressão)
    │   │   ├── Tratamento_Agua_Caldeira/AAAA/MM/
    │   │   └── Manutencao_Anual/AAAA/
    │   ├── ETA_Osmose/
    │   │   ├── Operacao/AAAA/MM/
    │   │   └── Troca_Membranas_Resinas/AAAA/
    │   ├── Compressor/
    │   │   ├── NR13_Inspecao/AAAA/
    │   │   └── Manutencao/AAAA/
    │   ├── Gerador_Diesel/
    │   │   ├── Testes_Mensais/AAAA/MM/
    │   │   ├── Manutencao/AAAA/
    │   │   └── Abastecimento_Combustivel/
    │   ├── HVAC/
    │   │   ├── PMOC_Execucao/AAAA/MM/
    │   │   ├── Troca_Filtros/AAAA/
    │   │   └── Mapeamento_Termico_Salas/AAAA/
    │   └── Eletrica/
    │       ├── Manutencao_QGBT/AAAA/
    │       └── Termografia/AAAA/
    ├── 03_Predial/
    │   ├── AVCB/AAAA/                                (renovação)
    │   ├── SPDA/AAAA/                                (inspeção anual NBR 5419)
    │   ├── Laudos_NR10/AAAA/
    │   ├── Manutencao_Predial_Geral/AAAA/MM/
    │   └── Reformas_Obras/
    ├── 04_Spare_Parts_Estoque/
    │   ├── Inventario/AAAA/
    │   ├── Entradas_Saidas/AAAA/MM/
    │   └── Pecas_Criticas_Min_Max.xlsx
    ├── 05_Contratos_Prestadores/
    │   └── PRESTADOR_CNPJ_Nome/
    │       ├── Contrato.pdf
    │       ├── Qualificacao_Fornecedor.pdf          (req. ISO 13485 cl. 7.4)
    │       ├── ART_Responsavel_Tecnico.pdf
    │       ├── Apolice_Seguro.pdf
    │       └── Avaliacoes_Periodicas/AAAA/
    ├── 06_Auditorias_Tecnicas/AAAA/                  (audit infraestrutura)
    ├── 07_Acidentes_Quase_Acidentes_Tecnicos/AAAA/   (link 80_SST)
    └── 08_Indicadores_Manutencao/AAAA/MM/
        ├── MTBF.csv                                  (Mean Time Between Failures)
        ├── MTTR.csv                                  (Mean Time To Repair)
        ├── Disponibilidade.csv                       (uptime % por equipamento)
        ├── Aderencia_PMM.csv                         (% PMs no prazo)
        └── Backlog_Manutencao.csv
```

**Doc types Eng/Manutenção:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `EM_FICHA_EQ` | Ficha Técnica Equipamento | Internal | vida útil | sim (Eng) | equipamento_id |
| `EM_PM` | Ordem Serviço PM | Internal | 5a | não | equipamento_id, data |
| `EM_CM` | Ordem Serviço CM | Internal | 5a | sim se reval. | equipamento_id, data |
| `EM_CAL` | Certificado Calibração | Restricted | vida útil instrumento | sim (Qualidade) | instrumento_id, validade |
| `EM_NR13` | Inspeção NR-13 | Restricted | vida útil + 5a | sim (Eng+RT) | vaso_id |
| `EM_PMOC` | Execução PMOC | Internal | 5a | não | mes |
| `EM_AVCB` | AVCB Bombeiros | Restricted | vigência | sim | validade_data |
| `EM_SPDA` | Laudo SPDA | Restricted | 5a | sim | validade_data |
| `EM_CONTR_PREST` | Contrato Prestador | Restricted | 5a pós-encerramento | sim (Diretoria) | fornecedor_id |
| `EM_QUALIF_FORN` | Qualificação Fornecedor | Internal | vigência+5a | sim (Qualidade) | fornecedor_id |

**Integração transacional:**
- Cadastro equipamento: m2o p/ `maintenance.equipment` (módulo Odoo Maintenance) — único cadastro
- Ordens serviço: criadas em `maintenance.request` → PDF anexado/gerado aqui
- Calibração: integra com `afr_ecm` `dms_file.validade_data` → alerta cron renovação
- Mudança equipamento (Change Control) cria simultaneamente: `EM_CM` aqui + `OP_CC` em 10_Op (vinculados)

**Eventos cruzados Eng ↔ Op:**
- Falha equipamento crítico → CM aqui → se afetou ciclo → vincula em `10_Op/07_Eventos_Criticos/Falhas_Ciclo`
- CM significativa (troca componente crítico) → revalidação PQ → registro em `10_Op/01_Validacao_Processo/.../07_Revalidacao_Mudancas`
- Calibração reprovada → quarentena equipamento → notifica Op

### 40_RH (detalhado)

```
40_RH/
├── Documentos/
│   ├── 01_Governanca_RH/
│   │   ├── Politica_RH.pdf
│   │   ├── Regulamento_Interno.pdf
│   │   ├── Codigo_Etica_Conduta.pdf
│   │   ├── Politica_Anti_Assedio_Discriminacao.pdf
│   │   ├── Politica_Anti_Suborno.pdf
│   │   ├── Politica_Diversidade_Inclusao.pdf
│   │   └── Politica_Trabalho_Remoto_Hibrido.pdf
│   ├── 02_Cargos_Salarios/
│   │   ├── Plano_Cargos_Salarios_PCS.pdf
│   │   ├── Descricao_Cargos/
│   │   │   ├── DC-OP-001_Tecnico_CME.pdf
│   │   │   ├── DC-OP-002_Auxiliar_CME.pdf
│   │   │   ├── DC-OP-003_Enfermeiro_CME.pdf       (RT — req. RDC 15)
│   │   │   ├── DC-QA-001_Coordenador_Qualidade.pdf
│   │   │   ├── DC-EM-001_Tecnico_Manutencao.pdf
│   │   │   └── DC-XX-NNN_*.pdf
│   │   ├── Tabela_Salarial.pdf                    (versionada)
│   │   ├── Pesquisa_Salarial_Mercado/AAAA/
│   │   └── Politica_Beneficios.pdf
│   ├── 03_Competencias_Treinamento/
│   │   ├── Matriz_Competencias_Cargo.xlsx         (competências por cargo)
│   │   ├── Matriz_Treinamento_Anual.xlsx          (cargo × treinamento × periodicidade)
│   │   ├── Plano_Anual_Capacitacao_PAC/AAAA/
│   │   ├── POPs_Treinamento/
│   │   │   ├── POP-RH-010_Levantamento_Necessidades.pdf
│   │   │   ├── POP-RH-011_Conducao_Treinamento.pdf
│   │   │   ├── POP-RH-012_Avaliacao_Eficacia.pdf
│   │   │   └── POP-RH-013_Treinamento_Integracao.pdf
│   │   ├── Conteudos_Programaticos/
│   │   │   ├── INT-001_Integracao_Admissional/    (boas-vindas + SGQ + segurança)
│   │   │   ├── OP-001_Reprocessamento_PPS/
│   │   │   ├── OP-002_Esterilizacao_Vapor/
│   │   │   ├── OP-003_Indicadores_Quimicos_Biologicos/
│   │   │   ├── SST-001_NR32/
│   │   │   ├── SST-002_EPI/
│   │   │   ├── SGQ-001_Sistema_Qualidade/
│   │   │   ├── LGPD-001_Lei_Protecao_Dados/
│   │   │   └── BPRC-001_Boas_Praticas_Reprocessamento_RDC15/
│   │   └── Materiais_Didaticos/                   (slides, vídeos, apostilas)
│   ├── 04_POPs_RH/
│   │   ├── POP-RH-001_Recrutamento_Selecao.pdf
│   │   ├── POP-RH-002_Admissao_Integracao.pdf
│   │   ├── POP-RH-003_Avaliacao_Desempenho.pdf
│   │   ├── POP-RH-004_Promocao_Movimentacao.pdf
│   │   ├── POP-RH-005_Acoes_Disciplinares.pdf
│   │   ├── POP-RH-006_Desligamento.pdf
│   │   ├── POP-RH-007_Folha_Pagamento.pdf
│   │   └── POP-RH-008_Ferias_Afastamentos.pdf
│   ├── 05_Modelos_Formularios/
│   │   ├── FORM-RH-001_Requisicao_Pessoal.pdf
│   │   ├── FORM-RH-002_Ficha_Registro.pdf
│   │   ├── FORM-RH-003_Termo_Confidencialidade.pdf
│   │   ├── FORM-RH-004_Termo_LGPD_Funcionario.pdf
│   │   ├── FORM-RH-005_Avaliacao_Experiencia_30_45_60_90.pdf
│   │   ├── FORM-RH-006_Avaliacao_Eficacia_Treinamento.pdf
│   │   ├── FORM-RH-007_Advertencia_Suspensao.pdf
│   │   └── FORM-RH-008_Pedido_Demissao.pdf
│   ├── 06_Acordos_Coletivos_Sindicato/AAAA/
│   │   ├── CCT_Convencao_Coletiva.pdf
│   │   ├── ACT_Acordo_Coletivo.pdf                (se houver)
│   │   └── Pauta_Negociacoes/
│   └── 07_Organograma/
│       ├── Organograma_Atual.pdf
│       └── Versoes_Anteriores/
└── Registros/
    ├── 01_Funcionarios_Ativos/
    │   └── MATRICULA_CPF_NomeFuncionario/
    │       ├── 01_Admissao_Documentacao/
    │       │   ├── Contrato_Trabalho_Assinado.pdf
    │       │   ├── Ficha_Registro.pdf
    │       │   ├── RG_CPF_CTPS.pdf
    │       │   ├── Comprovante_Residencia.pdf
    │       │   ├── Comprovante_Escolaridade.pdf
    │       │   ├── Certificados_Profissionais.pdf
    │       │   ├── Registro_Conselho_Classe.pdf   (COREN, CRF, CRBM se aplica)
    │       │   ├── Foto_3x4.jpg
    │       │   ├── Dependentes/
    │       │   ├── Termo_Sigilo_NDA.pdf
    │       │   ├── Termo_LGPD_Consentimento.pdf
    │       │   ├── Termo_Codigo_Etica.pdf
    │       │   └── Termo_Posse_Equipamentos.pdf   (notebook, EPI, uniforme)
    │       ├── 02_Saude_Ocupacional/              (NR-7 + NR-32)
    │       │   ├── ASO_Admissional.pdf
    │       │   ├── ASO_Periodicos/AAAA/
    │       │   ├── ASO_Mudanca_Funcao/
    │       │   ├── ASO_Retorno_Trabalho/
    │       │   ├── ASO_Demissional.pdf            (se aplica)
    │       │   ├── Exames_Complementares/AAAA/
    │       │   └── Cartao_Vacinacao_NR32/         (Hep B, dT, tríplice viral)
    │       ├── 03_Treinamentos_Realizados/
    │       │   ├── Integracao_Admissional/
    │       │   ├── Treinamentos_Operacionais/
    │       │   ├── Treinamentos_NR/
    │       │   ├── Treinamentos_SGQ/
    │       │   └── Certificados/AAAA/
    │       ├── 04_Avaliacoes/
    │       │   ├── Experiencia_30_45_60_90/
    │       │   ├── Desempenho_Anual/AAAA/
    │       │   ├── Avaliacao_360/AAAA/            (se aplica)
    │       │   └── Plano_Desenvolvimento_PDI/
    │       ├── 05_Movimentacoes/
    │       │   ├── Promocoes/
    │       │   ├── Transferencias/
    │       │   ├── Mudanca_Funcao/
    │       │   └── Reajustes_Salariais/AAAA/
    │       ├── 06_Ferias_Afastamentos/
    │       │   ├── Ferias/AAAA/
    │       │   ├── Atestados_Medicos/AAAA/
    │       │   ├── Licenca_Maternidade_Paternidade/
    │       │   ├── Auxilio_Doenca_INSS/
    │       │   ├── Acidente_Trabalho_CAT/         (link 80_SST)
    │       │   └── Outros_Afastamentos/
    │       ├── 07_Beneficios/
    │       │   ├── Vale_Transporte/
    │       │   ├── Vale_Alimentacao_Refeicao/
    │       │   ├── Plano_Saude_Odonto/
    │       │   ├── Seguro_Vida/
    │       │   └── Outros_Beneficios/
    │       ├── 08_Documentos_Disciplinares/
    │       │   ├── Advertencias/
    │       │   ├── Suspensoes/
    │       │   └── Justificativas_Defesa/
    │       ├── 09_EPI_Uniforme/                   (link 80_SST/Entrega_EPI)
    │       │   ├── Fichas_EPI/AAAA/
    │       │   └── Termo_Responsabilidade_Uniforme.pdf
    │       └── 10_Comunicacoes_Funcionario/
    │           ├── Comunicados_Recebidos/
    │           └── Solicitacoes_Enviadas/
    ├── 02_Funcionarios_Desligados/
    │   └── MATRICULA_CPF_NomeFuncionario_DataRescisao/   (estrutura congelada + rescisão)
    │       ├── [estrutura igual ao ativo]
    │       └── 11_Rescisao/
    │           ├── Aviso_Previo.pdf
    │           ├── Termo_Rescisao_TRCT.pdf
    │           ├── Homologacao_Sindicato.pdf      (se aplicável)
    │           ├── Exame_Demissional_ASO.pdf
    │           ├── Entrevista_Desligamento.pdf
    │           ├── Termo_Devolucao_Equipamentos.pdf
    │           ├── Quitacao_Beneficios.pdf
    │           └── Guia_FGTS_Rescisao.pdf
    ├── 03_Treinamentos_Coletivos/AAAA/
    │   └── TREIN_AAAAMMDD_NOME/
    │       ├── Plano_Treinamento.pdf
    │       ├── Conteudo_Aplicado.pdf
    │       ├── Lista_Presenca_Assinada.pdf
    │       ├── Material_Didatico_Aplicado/
    │       ├── Avaliacao_Aprendizagem_Individual/
    │       ├── Avaliacao_Eficacia_Pos_30_60_90d/  (RDC 15: eficácia)
    │       └── Certificados_Emitidos/
    ├── 04_Recrutamento_Selecao/AAAA/
    │   └── VAGA_AAAAMMDD_Cargo/
    │       ├── Requisicao_Pessoal.pdf
    │       ├── Anuncio_Divulgacao/
    │       ├── Curriculos_Recebidos/              (LGPD: retenção limitada)
    │       ├── Triagem_Entrevistas/
    │       ├── Testes_Tecnicos/
    │       ├── Resultado_Selecao.pdf
    │       └── Termos_LGPD_Candidatos.pdf
    ├── 05_Folha_Pagamento/AAAA/MM/               (espelho/link p/ módulo Payroll Odoo)
    │   ├── Holerites_Massa.pdf
    │   ├── Provisoes.pdf
    │   ├── Guias_INSS_FGTS_IRRF.pdf
    │   └── Relatorios_Gerenciais.csv
    ├── 06_eSocial_Eventos/AAAA/MM/                (S-1010, S-2200, S-2210, S-2299…)
    ├── 07_Auditorias_Trabalhistas/AAAA/
    ├── 08_Acoes_Trabalhistas/                     (separado por processo)
    │   └── PROCESSO_NN_AnoVara/
    │       ├── Inicial.pdf
    │       ├── Contestacao.pdf
    │       ├── Audiencias/
    │       ├── Sentenca.pdf
    │       └── Encerramento.pdf
    ├── 09_Atestados_Coletivos/AAAA/MM/            (relatos absenteísmo)
    └── 10_Indicadores_RH/AAAA/MM/
        ├── Turnover.csv
        ├── Absenteismo.csv
        ├── Aderencia_Matriz_Treinamento.csv
        ├── Tempo_Preenchimento_Vaga.csv
        ├── ROI_Treinamento.csv
        └── Climate_Pesquisa.csv
```

**Doc types RH:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `RH_ADMISSAO` | Doc Admissão | Confidential | 5a (mín. CLT) — recomendado 30a precaução | sim (RH) | funcionario_id |
| `RH_CONTRATO_T` | Contrato Trabalho | Confidential | 5a (mín. CLT) — recomendado 30a precaução | sim (RH+Diretoria) | funcionario_id |
| `RH_ASO` | ASO | Confidential | 20a pós-desligamento (NR-7 item 7.4.4.3) | sim (Med. Trab.) | funcionario_id, data |
| `RH_TREIN_IND` | Treinamento Individual | Internal | 5a | não | funcionario_id, treinamento_id |
| `RH_TREIN_COL` | Treinamento Coletivo | Internal | 5a (RDC 15) | sim (Qualidade) | treinamento_id, ano |
| `RH_AVAL` | Avaliação Desempenho | Confidential | 5a | sim (Gestor) | funcionario_id, periodo |
| `RH_DISCIP` | Ação Disciplinar | Confidential | 5a (CLT) — recomendado 30a precaução | sim (RH+Jurídico) | funcionario_id |
| `RH_RESC` | Rescisão | Confidential | 5a (CLT) — recomendado 30a precaução | sim (RH+Diretoria) | funcionario_id |
| `RH_CURRICULO` | Currículo Candidato | Confidential | 6m–2a (LGPD — base legítimo interesse) | não | candidato_id, vaga_id |
| `RH_FOLHA` | Folha Pagamento | Confidential | 10a (CC livros) — eSocial 5a | não | ano, mes |
| `RH_ESOCIAL` | Evento eSocial | Confidential | 5a | não | tipo_evento, periodo |
| `RH_ACAO_TRAB` | Ação Trabalhista | Confidential | até trânsito julgado + 5a | sim (Jurídico) | processo_numero |

> **Nota retenção RH:** prazos marcados "recomendado 30a precaução" partem do mínimo legal (prescrição CLT 5a) mas mantêm prática conservadora pela coexistência com FGTS, INSS, eSocial e possível reabertura de ações. **Validar política definitiva com consultoria trabalhista.**

---

### 80_SST (detalhado)

```
80_SST/
├── Documentos/
│   ├── 01_Governanca_SST/
│   │   ├── Politica_SST.pdf
│   │   ├── Politica_Acidente_Zero.pdf
│   │   └── Plano_Anual_SST.pdf
│   ├── 02_Programas_Legais/
│   │   ├── PGR_Programa_Gerenciamento_Riscos/    (NR-1 substituiu PPRA)
│   │   │   ├── PGR_Vigente.pdf
│   │   │   ├── Inventario_Riscos.pdf
│   │   │   ├── Plano_Acao_PGR.pdf
│   │   │   └── Versoes_Anteriores/
│   │   ├── PCMSO_Programa_Controle_Medico/        (NR-7)
│   │   │   ├── PCMSO_Vigente.pdf
│   │   │   ├── Cronograma_Exames.pdf
│   │   │   └── Versoes_Anteriores/
│   │   ├── PCMAT_Construcao/                      (se aplica obras)
│   │   ├── LTCAT_Laudo_Tecnico/                   (insalubridade/aposentadoria especial)
│   │   ├── LIP_Laudo_Insalubridade.pdf
│   │   ├── LIP_Laudo_Periculosidade.pdf
│   │   └── PAE_Plano_Atendimento_Emergencia/
│   │       ├── PAE_Vigente.pdf
│   │       ├── Mapa_Evacuacao.pdf
│   │       ├── Rotas_Fuga.pdf
│   │       └── Pontos_Encontro.pdf
│   ├── 03_Procedimentos_SST/
│   │   ├── POP-SST-001_Investigacao_Acidente.pdf
│   │   ├── POP-SST-002_Comunicacao_CAT.pdf
│   │   ├── POP-SST-003_Entrega_Controle_EPI.pdf
│   │   ├── POP-SST-004_Treinamento_Integrac_Seg.pdf
│   │   ├── POP-SST-005_Inspecoes_Seguranca.pdf
│   │   ├── POP-SST-006_Permissao_Trabalho_Quente.pdf
│   │   ├── POP-SST-007_Trabalho_Altura_NR35.pdf
│   │   ├── POP-SST-008_LOTO_Bloqueio_Etiquetagem_NR12.pdf
│   │   ├── POP-SST-009_Atendimento_Acidente_Biologico_NR32.pdf
│   │   └── POP-SST-010_Descarte_Perfurocortantes.pdf
│   ├── 04_Mapas_Riscos/
│   │   ├── Mapa_Risco_Sala_Suja.pdf
│   │   ├── Mapa_Risco_Sala_Preparo.pdf
│   │   ├── Mapa_Risco_Sala_Esterilizacao.pdf
│   │   ├── Mapa_Risco_Arsenal.pdf
│   │   ├── Mapa_Risco_Casa_Maquinas.pdf
│   │   └── Mapa_Risco_Geral.pdf
│   ├── 05_Especificacoes_EPI/
│   │   ├── Matriz_EPI_por_Funcao.xlsx
│   │   ├── Fichas_Tecnicas_EPI/
│   │   │   ├── Luva_Nitrilica_CA.pdf
│   │   │   ├── Mascara_PFF2_CA.pdf
│   │   │   ├── Oculos_Protecao_CA.pdf
│   │   │   ├── Avental_Impermeavel_CA.pdf
│   │   │   ├── Calcado_Seguranca_CA.pdf
│   │   │   ├── Protetor_Auricular_CA.pdf
│   │   │   └── Protetor_Termico_Autoclave_CA.pdf
│   │   └── Especificacoes_Uniforme/
│   ├── 06_NR_Aplicaveis/                          (referência norma + manual interno)
│   │   ├── NR-01_Disposicoes_Gerais_PGR/
│   │   ├── NR-04_SESMT/
│   │   ├── NR-05_CIPA/
│   │   ├── NR-06_EPI/
│   │   ├── NR-07_PCMSO/
│   │   ├── NR-09_Avaliacao_Exposicao_Riscos/
│   │   ├── NR-10_Eletricidade/
│   │   ├── NR-11_Movimentacao_Materiais/
│   │   ├── NR-12_Maquinas_Equipamentos/
│   │   ├── NR-13_Caldeiras_Vasos_Pressao/         (link 70_Eng)
│   │   ├── NR-17_Ergonomia/
│   │   ├── NR-23_Protecao_Incendios/
│   │   ├── NR-24_Higiene_Conforto/
│   │   ├── NR-25_Residuos_Industriais/
│   │   ├── NR-32_Servicos_Saude/                  (★ central para CME)
│   │   └── NR-35_Trabalho_Altura/                 (se aplica manutenção)
│   └── 07_PGRSS_Residuos_Saude/
│       ├── PGRSS_Vigente.pdf                      (RDC 222/2018)
│       ├── Procedimentos_Segregacao.pdf
│       ├── Fluxo_Residuos.pdf
│       └── Contrato_Coleta_Tratamento.pdf
└── Registros/
    ├── 01_CIPA/AAAA/                              (gestão atual)
    │   ├── Edital_Eleicao.pdf
    │   ├── Atas_Eleicao.pdf
    │   ├── Posse_Membros.pdf
    │   ├── Cronograma_Reunioes.pdf
    │   ├── Atas_Reunioes_Mensais/
    │   ├── SIPAT/
    │   │   └── SIPAT_AAAA/
    │   │       ├── Programacao.pdf
    │   │       ├── Material_Atividades/
    │   │       ├── Lista_Presenca/
    │   │       └── Avaliacao.pdf
    │   ├── Plano_Anual_Trabalho.pdf
    │   └── Indicadores_CIPA/
    ├── 02_ASOs/AAAA/                              (cópia agregada — original em 40_RH/funcionário)
    ├── 03_Acidentes_Trabalho/AAAA/
    │   └── ACID_AAAAMMDD_NN/
    │       ├── CAT_Comunicacao_Acidente.pdf
    │       ├── Investigacao_Causa_Raiz.pdf       (5 porquês, Ishikawa)
    │       ├── Testemunhos.pdf
    │       ├── Boletim_Ocorrencia/
    │       ├── Acompanhamento_Funcionario/
    │       ├── Plano_Acao_Prevencao.pdf
    │       └── Encerramento.pdf
    ├── 04_Quase_Acidentes_Incidentes/AAAA/
    ├── 05_Acidente_Biologico_Perfurocortante/AAAA/   (NR-32 — fluxo específico)
    │   └── EVENTO_AAAAMMDD_NN/
    │       ├── Comunicacao_Imediata.pdf
    │       ├── Atendimento_Medico.pdf
    │       ├── Sorologia_Funcionario.pdf
    │       ├── Sorologia_Fonte_Se_Conhecida.pdf
    │       ├── Acompanhamento_30_90_180d/
    │       ├── CAT.pdf
    │       └── Acao_Preventiva.pdf
    ├── 06_Treinamentos_NR/AAAA/
    │   ├── NR-32_Anual/AAAA/
    │   ├── NR-06_EPI/AAAA/
    │   ├── NR-12_Maquinas/AAAA/
    │   ├── NR-35_Altura/AAAA/
    │   ├── Brigada_Incendio/AAAA/
    │   ├── Primeiros_Socorros/AAAA/
    │   └── Treinamento_Integracao_Seguranca/AAAA/
    ├── 07_EPI_Entregas/AAAA/MM/
    │   └── Fichas_Individuais/                    (link p/ pasta funcionário)
    ├── 08_Inspecoes_Seguranca/AAAA/MM/
    │   ├── Checklist_EPI_Uso.pdf
    │   ├── Checklist_Predial.pdf
    │   ├── Checklist_Eletrico.pdf
    │   ├── Checklist_Incendio_Extintores_Hidrantes.pdf
    │   └── Plano_Acao_NCs.pdf
    ├── 09_Simulados_Emergencia/AAAA/
    │   └── SIM_AAAAMMDD_Tipo/                     (incêndio, evacuação, vazamento ETO)
    ├── 10_Vacinacao_NR32/AAAA/                    (Hep B, dT, tríplice viral)
    ├── 11_Atestados_de_Saude_Coletivos/AAAA/
    ├── 12_Auditorias_SST/AAAA/                    (internas + Min. Trab. + clientes)
    ├── 13_eSocial_SST/AAAA/                       (S-2210, S-2220, S-2230, S-2240)
    ├── 14_PGRSS_Execucao/AAAA/MM/                 (manifestos coleta, certificados destinação)
    │   ├── Manifestos_Transporte_Residuos/
    │   ├── Certificados_Destinacao_Final/
    │   └── Pesagens_Mensais/
    └── 15_Indicadores_SST/AAAA/MM/
        ├── Taxa_Frequencia_TF.csv                 (acidentes c/ afastamento × 10⁶ HHT)
        ├── Taxa_Gravidade_TG.csv
        ├── Dias_Perdidos.csv
        ├── Quase_Acidentes_Reportados.csv
        ├── Aderencia_Treinamentos_NR.csv
        └── Uso_EPI.csv
```

**Doc types SST:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `SST_PGR` | PGR Vigente | Internal | indef (vigente) + 20a obsoletos | sim (Eng. Seg+Diretoria) | validade_data |
| `SST_PCMSO` | PCMSO Vigente | Restricted | 20a | sim (Med. Trab+Diretoria) | validade_data |
| `SST_CAT` | CAT Acidente | Confidential | 20a | sim (Eng. Seg) | funcionario_id, data |
| `SST_INV_ACID` | Investigação Acidente | Restricted | 20a | sim (Eng. Seg+CIPA) | acidente_id |
| `SST_TREIN_NR` | Treinamento NR | Internal | 5a | sim (Qualidade) | nr_numero, ano |
| `SST_EPI_FICHA` | Ficha Entrega EPI | Internal | 30a pós-rescisão | não | funcionario_id |
| `SST_INSP` | Inspeção Segurança | Internal | 5a | não | data, area |
| `SST_SIMUL` | Simulado Emergência | Internal | 5a | não | data, tipo |
| `SST_PGRSS_MAN` | Manifesto Resíduos | Internal | 5a | não | data, transportador |
| `SST_AUDIT` | Auditoria SST | Restricted | 5a | sim | ano, origem |
| `SST_BIO_ACID` | Acidente Biológico NR-32 | Confidential | 20a | sim (Med. Trab) | funcionario_id |

**Integração crítica RH ↔ SST:**
- `RH_ASO` (40_RH) ≡ `RH_ASO` filha de `02_Saude_Ocupacional` do funcionário **+** réplica/link em `80_SST/02_ASOs/AAAA/`
  - Solução técnica: 1 arquivo único, 2 referências (`dms.file` + `relation` ao funcionário; índice agregado em SST via search/tag)
  - Evita duplicação física
- CAT cruzado: registro principal em `80_SST/03_Acidentes_Trabalho` **+** referência em pasta funcionário `40_RH/.../06_Ferias_Afastamentos/Acidente_Trabalho_CAT`
- EPI: ficha principal em `80_SST/07_EPI_Entregas` + tag funcionário

**Workflow eventos críticos SST:**
1. Acidente reportado → cria `SST_CAT` (rascunho) + activity p/ Eng. Seg.
2. CAT preenchida em ≤24h → workflow eSocial S-2210 (S-2210 automático via integração `hr.employee`)
3. Investigação obrigatória ≤7d → `SST_INV_ACID`
4. Se afastamento ≥15d → S-2230 automático
5. CAPA aberta no SGQ (NC operacional vinculada se causa for processo)
6. Indicador TF/TG atualizado no mês

### 50_Financeiro_Fiscal (detalhado)

```
50_Financeiro_Fiscal/
├── Documentos/
│   ├── 01_Governanca_Financeira/
│   │   ├── Politica_Financeira.pdf
│   │   ├── Politica_Credito_Cobranca.pdf
│   │   ├── Politica_Caixa_Tesouraria.pdf
│   │   ├── Politica_Investimentos.pdf
│   │   ├── Politica_Despesas_Reembolsos.pdf
│   │   ├── Politica_Cartao_Corporativo.pdf
│   │   ├── Alcadas_Aprovacao.pdf            (matriz alçadas — valor × aprovador)
│   │   └── Codigo_Conduta_Financeiro.pdf    (anti-suborno)
│   ├── 02_Plano_Contas/
│   │   ├── Plano_Contas_Contabil.xlsx
│   │   ├── Plano_Contas_Gerencial.xlsx
│   │   ├── Centros_Custo.xlsx
│   │   └── Mapa_DRE_Gerencial.pdf
│   ├── 03_Procedimentos_Fiscais/
│   │   ├── POP-FIN-001_Emissao_NFse.pdf
│   │   ├── POP-FIN-002_Conciliacao_Bancaria.pdf
│   │   ├── POP-FIN-003_Fechamento_Mensal.pdf
│   │   ├── POP-FIN-004_Pagamentos.pdf
│   │   ├── POP-FIN-005_Recebimentos.pdf
│   │   ├── POP-FIN-006_Provisoes.pdf
│   │   ├── POP-FIN-007_Aprovacao_Despesas.pdf
│   │   ├── POP-FIN-008_Gestao_Fluxo_Caixa.pdf
│   │   ├── POP-FIN-009_Apuracao_Impostos.pdf
│   │   └── POP-FIN-010_Encerramento_Anual.pdf
│   ├── 04_Politicas_Tributarias/
│   │   ├── Regime_Tributario.pdf            (Lucro Real/Presumido/SN)
│   │   ├── Politica_Reten_Impostos.pdf
│   │   ├── Politica_Substituicao_Tributaria.pdf
│   │   └── Pareceres_Tributarios/           (orientações consultoria)
│   ├── 05_Contratos_Financeiros/
│   │   ├── Bancos_Operadoras_Maquininhas/
│   │   ├── Financiamentos_Emprestimos/
│   │   ├── Leasing_Equipamentos/
│   │   ├── Convenios_Cartoes/
│   │   └── Seguros_Empresariais/
│   └── 06_Modelos_Formularios/
│       ├── FORM-FIN-001_Solicitacao_Pagamento.pdf
│       ├── FORM-FIN-002_Reembolso_Despesa.pdf
│       ├── FORM-FIN-003_Adiantamento_Viagem.pdf
│       ├── FORM-FIN-004_Prestacao_Contas.pdf
│       └── FORM-FIN-005_Solicitacao_Compra.pdf
└── Registros/
    ├── 01_Fiscal/AAAA/MM/
    │   ├── NFse_Emitidas/                   (espelho/link `account.move`)
    │   ├── NFe_Recebidas/                   (XML + DANFE; SPED-Fiscal)
    │   ├── CTe_Conhecimentos/
    │   ├── SPED_Fiscal/                     (EFD ICMS/IPI)
    │   ├── SPED_Contribuicoes/              (EFD PIS/COFINS)
    │   ├── SPED_ECF_ECD/                    (anual)
    │   └── Recibos_Servicos_RPS/
    ├── 02_Tributario/AAAA/
    │   ├── Apuracao_ISS_AAAA_MM/
    │   ├── Apuracao_PIS_COFINS_AAAA_MM/
    │   ├── Apuracao_IRPJ_CSLL_AAAA_TT/      (trimestral)
    │   ├── DARFs_Recolhimentos/AAAA/MM/
    │   ├── DCTF_Web/AAAA/MM/
    │   ├── DEFIS_Anual/                     (Simples)
    │   ├── DIRPJ_DIPJ_Anual/
    │   ├── Reinf/AAAA/MM/                   (eSocial-like p/ retenções)
    │   └── Certidoes_Negativas/AAAA/        (CND federal/estadual/municipal/FGTS/trabalhista)
    ├── 03_Contabil/AAAA/
    │   ├── Balancetes_Mensais/AAAA/MM/
    │   ├── Razoes_Contabeis/AAAA/MM/
    │   ├── DRE_Mensal/AAAA/MM/
    │   ├── DRE_Anual/AAAA/
    │   ├── Balanco_Patrimonial_Anual/AAAA/
    │   ├── DFC_Demonstracao_Fluxo_Caixa/AAAA/
    │   ├── DMPL_Mutacoes_PL/AAAA/
    │   ├── Notas_Explicativas/AAAA/
    │   └── Livros_Contabeis/                (Diário, Razão — ECD)
    ├── 04_Tesouraria/
    │   ├── Bancario/AAAA/MM/
    │   │   ├── Extratos/                    (PDF + OFX)
    │   │   ├── Conciliacao.xlsx
    │   │   └── Saldo_Final_Mes.pdf
    │   ├── Fluxo_Caixa_Diario/AAAA/MM/
    │   ├── Aplicacoes_Resgate/AAAA/MM/
    │   ├── Cartoes_Maquininhas/AAAA/MM/     (extratos operadoras)
    │   └── Caixa_Fisico/AAAA/MM/            (se houver)
    ├── 05_Contas_Pagar/AAAA/MM/
    │   ├── Fornecedores/
    │   │   └── FORN_CNPJ_Nome/
    │   │       ├── NFs_Recebidas/
    │   │       ├── Comprovantes_Pagamento/
    │   │       └── Conciliacao/
    │   ├── Folha_Pagamento/                 (link 40_RH/Folha)
    │   └── Impostos_Recolhidos/
    ├── 06_Contas_Receber/AAAA/MM/
    │   ├── Clientes/                        (link 30_Comercial)
    │   ├── Boletos_Emitidos/
    │   ├── Inadimplencia/
    │   │   └── INAD_CNPJ_Cliente/
    │   │       ├── Cobrancas_Realizadas/
    │   │       ├── Acordos_Repactuacao/
    │   │       ├── Protesto/
    │   │       └── Judicial/
    │   └── Recebimentos.csv
    ├── 07_Orcamento_Planejamento/AAAA/
    │   ├── Budget_Anual.xlsx
    │   ├── Revisoes_Forecast/               (trimestral)
    │   ├── Realizado_vs_Orcado/MM/
    │   └── Plano_Investimentos_CAPEX.pdf
    ├── 08_Auditorias_Financeiras/AAAA/
    │   ├── Auditoria_Independente/          (se aplicável)
    │   ├── Auditoria_Fiscal/
    │   └── Relatorio_Auditor.pdf
    ├── 09_Despesas_Reembolsos/AAAA/MM/
    │   ├── Adiantamentos/
    │   ├── Prestacoes_Contas/
    │   └── Reembolsos_Aprovados/
    ├── 10_Acoes_Fiscais_Tributarias/        (processos)
    │   └── PROC_NN_AnoOrgao/
    │       ├── Notificacao.pdf
    │       ├── Defesa_Impugnacao.pdf
    │       ├── Recursos.pdf
    │       └── Decisao_Final.pdf
    └── 11_Indicadores_Financeiros/AAAA/MM/
        ├── Margem_Bruta_Liquida.csv
        ├── EBITDA.csv
        ├── DSO_Dias_Recebimento.csv
        ├── DPO_Dias_Pagamento.csv
        ├── Capital_Giro.csv
        ├── Endividamento.csv
        ├── Liquidez.csv
        └── ROI_ROA_ROE.csv
```

**Doc types Financeiro:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `FIN_POL` | Política Financeira | Internal | indef | sim (CFO+Diretoria) | tipo |
| `FIN_NFSE` | NFse Emitida | Confidential | 5a | não (sistêmico) | cliente_id, mes |
| `FIN_NFE_REC` | NFe Recebida | Confidential | 5a | não | fornecedor_id, mes |
| `FIN_SPED` | Arquivo SPED | Confidential | 5a | sim (Contabilidade) | tipo_sped, mes |
| `FIN_DARF` | DARF/Guia | Confidential | 5a | sim (Fiscal) | tributo, mes |
| `FIN_CND` | Certidão Negativa | Internal | vigência | não | esfera, validade_data |
| `FIN_BAL` | Balanço/DRE | Confidential | 10a | sim (Contador+CFO) | periodo |
| `FIN_EXT_BANC` | Extrato Bancário | Confidential | 5a | não | banco, mes |
| `FIN_CONTR_BAN` | Contrato Bancário | Confidential | vigência+5a | sim (Diretoria) | banco |
| `FIN_AUDIT` | Auditoria Independente | Restricted | 10a | sim (Diretoria) | ano |
| `FIN_PROC_TRIB` | Processo Tributário | Confidential | até trânsito+5a | sim (Jurídico+CFO) | numero |
| `FIN_BUDGET` | Orçamento Anual | Restricted | 5a | sim (Diretoria) | ano |

**Integração:**
- NFse emitida: gerada por `account.move` em Odoo → PDF + XML automaticamente arquivado aqui via cron (não duplicar manualmente)
- Folha pagamento: link p/ `hr.payslip` (não duplicar)
- Faturamento por cliente: aparece também em `30_Comercial/.../Faturamento/` (mesmo arquivo, 2 referências)

---

### 60_TI (detalhado)

```
60_TI/
├── Documentos/
│   ├── 01_Governanca_TI/
│   │   ├── Politica_TI.pdf
│   │   ├── Plano_Diretor_TI.pdf
│   │   ├── Politica_Uso_Aceitavel.pdf       (BYOD, e-mail, internet, redes sociais)
│   │   ├── Politica_Senha.pdf
│   │   ├── Politica_Mesa_Limpa.pdf
│   │   ├── Politica_Trabalho_Remoto.pdf
│   │   └── Politica_Engenharia_Social.pdf
│   ├── 02_Seguranca_Informacao_SI/           (ISO 27001-aligned)
│   │   ├── Politica_SI_PSI.pdf
│   │   ├── Politica_Classificacao_Informacao.pdf
│   │   ├── Politica_Controle_Acesso.pdf
│   │   ├── Politica_Criptografia.pdf
│   │   ├── Politica_Antimalware.pdf
│   │   ├── Politica_Vulnerabilidade.pdf
│   │   ├── Politica_Resposta_Incidentes.pdf
│   │   ├── Politica_Pen_Test.pdf
│   │   ├── Politica_Logs_Auditoria.pdf
│   │   └── Politica_Continuidade_BCP_DR.pdf
│   ├── 03_LGPD_Tecnico/                     (complementa 20_Reg/LGPD)
│   │   ├── Arquitetura_Tratamento_Dados.pdf
│   │   ├── Mapeamento_Fluxo_Dados.pdf       (dataflow diagram)
│   │   ├── Medidas_Tecnicas_Organizacionais.pdf
│   │   └── Anonimizacao_Pseudonimizacao.pdf
│   ├── 04_POPs_TI/
│   │   ├── POP-TI-001_Provisao_Acesso.pdf
│   │   ├── POP-TI-002_Revogacao_Acesso.pdf  (off-boarding crítico)
│   │   ├── POP-TI-003_Backup.pdf
│   │   ├── POP-TI-004_Restore_Teste.pdf
│   │   ├── POP-TI-005_Patch_Management.pdf
│   │   ├── POP-TI-006_Resposta_Incidente.pdf
│   │   ├── POP-TI-007_Mudanca_Sistemas.pdf  (change control TI)
│   │   ├── POP-TI-008_Gestao_Senha.pdf
│   │   ├── POP-TI-009_Acesso_Remoto.pdf
│   │   ├── POP-TI-010_Suporte_Help_Desk.pdf
│   │   ├── POP-TI-011_Aquisicao_Hardware.pdf
│   │   ├── POP-TI-012_Disposicao_Equipamento.pdf  (LGPD: limpeza dados)
│   │   └── POP-TI-013_Monitoramento_Logs.pdf
│   ├── 05_Arquitetura_Mapa_Ativos/
│   │   ├── Topologia_Rede.pdf
│   │   ├── Diagrama_Sistemas.pdf
│   │   ├── Inventario_Servidores.xlsx       (físicos + cloud)
│   │   ├── Inventario_Estacoes.xlsx
│   │   ├── Inventario_Mobile.xlsx
│   │   ├── Inventario_Periféricos.xlsx
│   │   ├── Mapa_Sistemas_Criticos.xlsx      (com criticidade BIA)
│   │   ├── Matriz_Dependencias.xlsx         (sistema × sistema)
│   │   ├── Catalogo_Servicos_TI.pdf
│   │   └── BIA_Business_Impact_Analysis.pdf
│   ├── 06_Validacao_Sistemas_Computadorizados/  (CSV — req. ISO 13485 cl. 4.1.6)
│   │   ├── Politica_CSV.pdf
│   │   ├── URS_Sistemas/                    (especificações sistemas críticos)
│   │   ├── Lista_Sistemas_Validados.xlsx    (Odoo, ECM, supervisório, etc)
│   │   └── POPs_CSV/
│   ├── 07_Contratos_TI/
│   │   ├── SaaS_Cloud/
│   │   ├── Provedor_Internet.pdf
│   │   ├── Datacenter_Hospedagem.pdf
│   │   ├── Backup_Offsite.pdf
│   │   ├── Antivirus_Endpoint.pdf
│   │   ├── Suporte_Software.pdf
│   │   └── Acordos_Confidencialidade_NDA/
│   └── 08_Plano_Continuidade_DR/
│       ├── BCP_Business_Continuity_Plan.pdf
│       ├── DRP_Disaster_Recovery_Plan.pdf
│       ├── RTO_RPO_por_Sistema.xlsx          (objetivos recuperação)
│       ├── Procedimentos_Failover.pdf
│       └── Cenarios_Crise.pdf
└── Registros/
    ├── 01_Validacao_Sistemas_Computadorizados/
    │   └── Sistema_XX/                       (Odoo, afr_ecm, supervisório ciclos)
    │       ├── 01_URS/
    │       ├── 02_FS_Specs_Funcionais/
    │       ├── 03_DS_Design_Specs/
    │       ├── 04_IQ_Instalacao_Sistema/
    │       ├── 05_OQ_Operacional/
    │       ├── 06_PQ_Performance/            (validação dados produção)
    │       ├── 07_Plano_Testes/
    │       ├── 08_Casos_Teste_Execucao/
    │       ├── 09_Trace_Matrix/              (req → teste)
    │       ├── 10_Aprovacao_Go_Live/
    │       └── 11_Revalidacao_Mudanca/AAAA/
    ├── 02_Backups/
    │   ├── Logs_Execucao/AAAA/MM/            (sucesso/falha diários)
    │   ├── Sumarios_Mensais/AAAA/MM/
    │   ├── Verificacao_Integridade/AAAA/
    │   └── Restauracoes_Teste/AAAA/          (mensal/trimestral)
    ├── 03_Incidentes_SI/AAAA/
    │   └── INC_AAAAMMDD_NN/
    │       ├── Identificacao.pdf
    │       ├── Classificacao_Severidade.pdf
    │       ├── Contencao.pdf
    │       ├── Erradicacao_Recuperacao.pdf
    │       ├── Investigacao_Forense.pdf      (se aplicável)
    │       ├── Notificacao_LGPD/             (link 20_Reg se dados pessoais afetados)
    │       ├── Acao_Corretiva.pdf
    │       └── Encerramento_Licoes.pdf
    ├── 04_Vulnerabilidades_Pen_Tests/AAAA/
    │   ├── Scan_Vulnerabilidades/AAAA/MM/
    │   ├── Pen_Test_Anual/AAAA/
    │   └── Plano_Remediacao/
    ├── 05_Gestao_Acessos/
    │   ├── Provisionamentos/AAAA/MM/         (admissões)
    │   ├── Revogacoes/AAAA/MM/               (desligamentos — CRÍTICO LGPD)
    │   ├── Revisoes_Trimestrais/AAAA/TT/     (recertificação acessos)
    │   ├── Matrizes_Acessos/AAAA/            (sistema × usuário × perfil)
    │   └── Excecoes_Aprovadas/
    ├── 06_Mudancas_Change_Control_TI/AAAA/
    │   └── CC_TI_AAAAMMDD_NN/
    │       ├── Solicitacao.pdf
    │       ├── Analise_Risco_Impacto.pdf
    │       ├── Plano_Implementacao.pdf
    │       ├── Plano_Rollback.pdf
    │       ├── Aprovacao_CAB.pdf             (Change Advisory Board)
    │       ├── Execucao.pdf
    │       └── Pos_Implementacao.pdf
    ├── 07_Inventario_Hardware/AAAA/
    │   └── Auditoria_Anual.xlsx
    ├── 08_Licencas_Software/
    │   └── Licenca_NomeProduto/
    │       ├── Nota_Fiscal_Aquisicao.pdf
    │       ├── Termo_Licenca.pdf
    │       ├── Renovacoes/AAAA/
    │       └── Comprovante_Compliance.pdf
    ├── 09_Auditorias_TI_SI/AAAA/             (internas + externas + LGPD técnica)
    ├── 10_Simulados_DR_BCP/AAAA/             (testes plano continuidade)
    │   └── SIM_AAAAMMDD/
    │       ├── Cenario.pdf
    │       ├── Execucao.pdf
    │       ├── Tempo_Recuperacao_Medido.pdf  (RTO/RPO real)
    │       └── Plano_Acao_Gaps.pdf
    ├── 11_Treinamentos_SI_LGPD/AAAA/         (link 40_RH)
    ├── 12_Phishing_Simulacoes/AAAA/          (testes conscientização)
    └── 13_Indicadores_TI/AAAA/MM/
        ├── Uptime_Sistemas.csv
        ├── Tickets_Help_Desk.csv
        ├── Tempo_Atendimento_SLA.csv
        ├── Incidentes_SI.csv
        ├── Backup_Success_Rate.csv
        ├── Patch_Compliance.csv
        └── Phishing_Click_Rate.csv
```

**Doc types TI:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `TI_POL_SI` | Política SI | Internal | indef | sim (TI+Diretoria) | tipo |
| `TI_CSV_VAL` | Validação Sistema CSV | Restricted | vida útil sistema+5a | sim (TI+RT) | sistema_id |
| `TI_BACKUP_LOG` | Log Backup | Internal | 5a | não | data |
| `TI_INC_SI` | Incidente SI | Restricted | 10a | sim (TI+DPO se LGPD) | severidade |
| `TI_PENTEST` | Pen Test | Restricted | 5a | sim (TI+Diretoria) | ano |
| `TI_CHG` | Change TI | Internal | 5a | sim (CAB) | sistema |
| `TI_ACC_PROV` | Provisão Acesso | Confidential | 5a | sim (Gestor+TI) | funcionario_id |
| `TI_ACC_REV` | Revogação Acesso | Confidential | 5a | sim (RH+TI) | funcionario_id |
| `TI_AUDIT_TI` | Auditoria TI | Restricted | 5a | sim | ano |
| `TI_DRP_SIM` | Simulado DR | Internal | 5a | sim (TI) | data |
| `TI_LIC_SW` | Licença Software | Confidential | vigência+5a | sim (TI+Fin) | produto |

**Integração crítica TI ↔ RH:**
- Admissão funcionário → `TI_ACC_PROV` automático (matriz acesso por cargo)
- Rescisão → `TI_ACC_REV` em ≤4h (gatilho `hr.employee.write` com `active=False`)
- Mudança função → revisão matriz acessos
- Revisão trimestral acessos: TI gera relatório, gestores revisam, NCs vão p/ SGQ

**Workflow CSV (Validação Sistemas Computadorizados):**
- Cada sistema crítico do SGQ deve ter validação documentada (ISO 13485 cl. 4.1.6)
- Sistemas validados típicos: Odoo ERP, afr_ecm (próprio), afr_supervisorio_ciclos, ecm_desktop, sistema laudo
- Revalidação após mudança significativa (`TI_CHG` major) ou ≥3 anos
- Documentação V&V vinculada via `sistema_id` (m2o)

---

### 90_Diretoria (detalhado)

```
90_Diretoria/
├── Documentos/
│   ├── 01_Governanca_Corporativa/
│   │   ├── Codigo_Governanca.pdf
│   │   ├── Estatuto_Politicas_Diretoria.pdf
│   │   ├── Estrutura_Decisional.pdf
│   │   ├── Composicao_Diretoria_Conselho.pdf
│   │   ├── Regimento_Interno_Diretoria.pdf
│   │   └── Regimento_Interno_Conselho.pdf
│   ├── 02_Planejamento_Estrategico/
│   │   ├── Plano_Estrategico_5anos.pdf
│   │   ├── Mapa_Estrategico_BSC.pdf         (Balanced Scorecard)
│   │   ├── SWOT_Atualizado_AAAA.pdf
│   │   ├── Plano_Negocios.pdf
│   │   └── Cenarios_Prospectivos.pdf
│   ├── 03_Organograma_RACI/
│   │   ├── Organograma_Vigente.pdf
│   │   ├── Matriz_RACI_Processos.xlsx       (Responsible/Accountable/Consulted/Informed)
│   │   ├── Linha_Sucessao.pdf               (sucessores-chave)
│   │   └── Descricao_Funcoes_Lideranca/
│   ├── 04_Politicas_Macro/
│   │   ├── Codigo_Etica_Conduta.pdf         (cópia transversal)
│   │   ├── Politica_Sustentabilidade_ESG.pdf
│   │   ├── Politica_Responsabilidade_Social.pdf
│   │   ├── Politica_Comunicacao_Stakeholders.pdf
│   │   ├── Politica_Crise_Reputacao.pdf
│   │   └── Politica_M&A_Aquisicoes.pdf
│   └── 05_Politica_Gestao_Riscos_Corp/
│       ├── Framework_Riscos_Corporativos.pdf  (alinhado COSO/ISO 31000)
│       ├── Apetite_Risco.pdf
│       └── Matriz_Riscos_Diretoria.xlsx
└── Registros/
    ├── 01_Atas_Diretoria/AAAA/
    │   └── ATA_AAAAMMDD/
    │       ├── Pauta.pdf
    │       ├── Apresentacoes/
    │       ├── Ata_Final.pdf                (assinada)
    │       └── Plano_Acao_Decisoes.pdf
    ├── 02_Atas_Conselho/AAAA/                (se houver conselho)
    ├── 03_Atas_Assembleias_Socios/AAAA/
    │   └── ASS_AAAAMMDD_Tipo/                (ordinária, extraordinária)
    │       ├── Convocacao.pdf
    │       ├── Edital.pdf
    │       ├── Documentos_Apresentados/
    │       ├── Ata_Lavrada.pdf
    │       └── Registro_Junta_Comercial.pdf
    ├── 04_Decisoes_Estrategicas/AAAA/
    │   └── DEC_AAAAMMDD_NN/
    │       ├── Contexto.pdf
    │       ├── Analise_Opcoes.pdf
    │       ├── Decisao.pdf
    │       ├── Plano_Implementacao.pdf
    │       └── Follow_Up.pdf
    ├── 05_Painel_Bordo_BSC/AAAA/MM/
    │   ├── Perspectiva_Financeira.pdf
    │   ├── Perspectiva_Cliente.pdf
    │   ├── Perspectiva_Processos.pdf
    │   ├── Perspectiva_Aprendizado.pdf
    │   └── Consolidado_Mensal.pdf
    ├── 06_Indicadores_Estrategicos/AAAA/MM/
    │   ├── Crescimento_Receita.csv
    │   ├── Market_Share.csv
    │   ├── NPS_Consolidado.csv
    │   ├── Engajamento_Funcionarios.csv
    │   ├── ESG_Sustentabilidade.csv
    │   └── Inovacao_Pipeline.csv
    ├── 07_Comites/                           (sub-comitês de governança)
    │   ├── Comite_Auditoria/AAAA/
    │   ├── Comite_Etica_Compliance/AAAA/
    │   ├── Comite_Riscos/AAAA/
    │   └── Comite_Sustentabilidade/AAAA/
    ├── 08_Comunicacoes_Acionistas_Socios/AAAA/
    ├── 09_M&A_Operacoes_Societarias/         (se aplica)
    │   └── OPERACAO_AAAAMMDD/
    │       ├── Due_Diligence/
    │       ├── Contratos.pdf
    │       └── Pos_Closing/
    ├── 10_Plano_Acao_ACD_SGQ/AAAA/           (decisões da Análise Crítica Direção)
    ├── 11_Comunicacao_Crise/                 (eventos extraordinários)
    │   └── EVENTO_AAAAMMDD_Tipo/
    │       ├── Identificacao.pdf
    │       ├── Comunicado_Imprensa.pdf
    │       ├── Comunicacao_Stakeholders.pdf
    │       └── Pos_Mortem.pdf
    └── 12_Relatorio_Anual_Sustentabilidade/AAAA/  (se publicar GRI/SASB)
```

**Doc types Diretoria:**

| `code` | Nome | Confid. | Retenção | Aprovação | Metadata |
|---|---|---|---|---|---|
| `DIR_PLAN_EST` | Plano Estratégico | Confidential | indef + 5a obsoleto | sim (Diretoria+Conselho) | periodo |
| `DIR_ATA_DIR` | Ata Diretoria | Confidential | indef | sim (Diretoria) | data |
| `DIR_ATA_ASS` | Ata Assembleia Sócios | Restricted | indef | sim (Sócios) | tipo, data |
| `DIR_DEC_EST` | Decisão Estratégica | Confidential | indef | sim (Diretoria) | tema |
| `DIR_BSC` | Painel BSC | Restricted | 5a | sim (Diretoria) | mes |
| `DIR_COMITE` | Ata Comitê | Confidential | 10a | sim (Comitê) | nome_comite |
| `DIR_MA` | Operação M&A | Confidential | indef | sim (Diretoria+Sócios) | operacao |
| `DIR_CRISE` | Comunicação Crise | Confidential | 10a | sim (Diretoria) | evento |
| `DIR_RACI` | Matriz RACI | Internal | indef | sim (Diretoria) | versao |

**Integração:**
- Análise Crítica Direção (`SGQ_ACD` em 00_SGQ) → decisões saem aqui em `10_Plano_Acao_ACD_SGQ`
- Indicadores estratégicos consolidam KPIs das outras áreas (auto-import via cron + dashboards)
- Atas Diretoria que aprovam mudanças regulatórias (ex: RT) → link p/ `20_Reg`
- Crises críticas (recall, vazamento LGPD, evento sanitário) → linkadas a evento operacional/regulatório

### 70_Engenharia_Manutencao
```
70_Engenharia_Manutencao/
├── Documentos/
│   ├── Plano_Mestre_Manutencao/
│   ├── Cadastro_Equipamentos/             (ficha técnica por equipamento)
│   ├── Manuais_Fabricante/
│   └── Procedimentos_Manutencao/
└── Registros/
    ├── Equipamento_XX/                    (espelha lista equipamentos)
    │   ├── Manutencao_Preventiva/AAAA/
    │   ├── Manutencao_Corretiva/AAAA/
    │   ├── Calibracao/AAAA/               (certificados RBC)
    │   ├── Qualificacao/                  (link p/ 10_Operacao/Validacao)
    │   └── Historico_Falhas/
    ├── Utilidades/                        (vapor, ar comprimido, água, energia)
    │   ├── Vapor/Validacao_Qualidade/
    │   ├── Agua_Tratamento/
    │   └── Ar_Comprimido/
    └── Predial/                           (HVAC, climatização salas)
```

### 80_SST
```
80_SST/
├── Documentos/
│   ├── PGR_Programa_Gerenciamento_Riscos/
│   ├── PCMSO/
│   ├── Plano_Emergencia/
│   ├── Mapa_Risco/
│   ├── POPs_EPI/
│   └── Procedimentos_NR32/
└── Registros/
    ├── ASOs/AAAA/                         (cópia; original em pasta funcionário)
    ├── CIPA/AAAA/                         (atas, eleição, SIPAT)
    ├── Acidentes_Trabalho/AAAA/           (CAT, investigação)
    ├── Treinamentos_NR/AAAA/
    ├── Entrega_EPI/AAAA/                  (fichas EPI)
    ├── Inspecoes_Seguranca/AAAA/
    └── Vacinacao_Imunizacao/              (NR-32: Hep B, dT, tríplice viral)
```

### 90_Diretoria
```
90_Diretoria/
├── Documentos/
│   ├── Planejamento_Estrategico/
│   ├── Organograma/
│   ├── Matriz_Responsabilidades_RACI/
│   └── Politica_Governanca/
└── Registros/
    ├── Atas_Diretoria/AAAA/
    ├── Indicadores_Estrategicos/AAAA/
    ├── Reunioes_Conselho/AAAA/
    └── Decisoes_Estrategicas/
```

---

## Convenções transversais

### Nomenclatura de arquivos
Padrão: `[CODIGO]_[Titulo]_v[VERSAO]_[YYYY-MM-DD].[ext]`
- `POP-EST-001_Esterilizacao_Vapor_v03_2026-04-15.pdf`
- `REG-VAL-2026-04_IQ_Autoclave_AC02.pdf`
- `RH-ASO-12345_2026-05-13.pdf`

Códigos por área:
| Prefixo | Significado |
|---|---|
| POP-XX | POP (XX = área) |
| IT-XX | Instrução Trabalho |
| FORM-XX | Formulário mestre |
| REG-XX | Registro |
| MAN-XX | Manual |
| POL-XX | Política |
| PLAN-XX | Plano |

### Metadados cruzados (tags / `metadata_field`)
Aplicar em `dms.file` via afr_ecm metadata system:
- `cliente_id` (m2o res.partner) — quando aplicável
- `equipamento_id` (m2o) — quando vincula a equipamento
- `norma_referencia` (selection: RDC15, ISO9001, ISO13485, ISO17665, NR32, LGPD…)
- `processo` (selection: recepcao, lavagem, preparo, embalagem, esterilizacao, armazenamento, transporte)
- `validade_data` (date) — para docs com expiração (AFE, licenças, certificados, ASO)
- `responsavel_aprovacao` (m2o res.users)
- `versao_vigente` (boolean) — apenas última versão = True
- `obsoleto` (boolean) — versão anterior arquivada

### Retenção mínima (alinhar `document_type.retention_days`)
| Categoria | Retenção mínima | Norma | Obs. |
|---|---|---|---|
| Registros operacionais (ciclos, BI/CI) | 5 anos | RDC 15 art. 100 | |
| Validação processo (IQ/OQ/PQ) | Vida útil equip. + 5 anos | RDC 15 | prática setor |
| Documentos SGQ vigentes | Indefinida (até substituição) | ISO 9001 cl. 7.5 | |
| Versões obsoletas controladas | 5 anos após retirada | ISO 9001 cl. 7.5 | |
| ASO/PCMSO | 20 anos pós-desligamento | NR-7 item 7.4.4.3 | confirmado (texto consolidado 2022) |
| RH — pasta funcionário (contrato, registros) | 5 anos prescrição trabalhista + 2 anos | CLT art. 11 / Lei 8.213 | **Confirmar com Jurídico** — STF RE 522.897 (2014) mudou prescrição FGTS p/ 5 anos; prática de mercado mantém 30a por precaução (eSocial S-2299, INSS, ações trabalhistas, FGTS conta vinculada) |
| FGTS/INSS contribuições | 5 anos (STF 2014) — prática 30a | STF RE 522.897 / IN INSS | precaução 30a recomendada |
| Fiscal/contábil | 5 anos (decadência) / 10a (livros) | CTN art. 173-174 / CC art. 1.194 | |
| Contratos com cliente | 5 anos pós-encerramento | RDC 15 + CC art. 205 | prescrição 10a CC |
| Auditorias internas/externas | 5 anos | ISO 9001 / 13485 | |
| Treinamento (lista presença + eficácia) | 5 anos | RDC 15 / NR-1 | |
| Recall / BI positivo / Tecnovigilância | 10 anos | RDC 15 + RDC 67/2009 | |
| Incidentes LGPD | indef./10a min | LGPD + RGPD analogia | |
| Licenças vigentes (AFE, AE, LS, alvará) | indef + vigência | RDC 16/204/420 ANVISA | renovação cronograma |

> **Avisos de verificação:** células marcadas “Confirmar com Jurídico” devem ser validadas com consultor trabalhista da empresa antes de fechar política de retenção (especialmente RH/FGTS — divergência entre STF 2014 e prática histórica).

### Versionamento (alinhar workflow afr_ecm)
- POPs/ITs: aprovação obrigatória (`requires_approval=True`)
- Versão major (`v01`, `v02`) — revisão de conteúdo significativa
- Versão minor (`v01.1`) — correção menor sem mudar processo
- Lista Mestra de Documentos atualizada a cada release (registro em `00_SGQ/Documentos/04_Lista_Mestra_Documentos`)
- Versão obsoleta movida para subpasta `_obsoletos/` ou marcada via `obsoleto=True` (manter consultável, fora da navegação default)

### Controle de acesso (via `dms.access.group` + grupos Odoo)
| Grupo | Escopo |
|---|---|
| ECM_Manager | Tudo (CRUD em todas áreas) |
| ECM_SGQ | 00_SGQ (CRUD), demais (read) |
| ECM_Operacao | 10_Operacao (CRUD), 00_SGQ (read), 70_Eng (read) |
| ECM_Regulatorio | 20_Regulatorio (CRUD), 00_SGQ (read) |
| ECM_Comercial | 30_Comercial (CRUD), 00_SGQ (read) |
| ECM_RH | 40_RH (CRUD), 80_SST (read) |
| ECM_RH_Funcionario | Apenas própria pasta em 40_RH/Registros/Funcionarios |
| ECM_Financeiro | 50_Financeiro_Fiscal (CRUD) |
| ECM_TI | 60_TI (CRUD) |
| ECM_Eng | 70_Engenharia_Manutencao (CRUD), 10_Operacao (read) |
| ECM_SST | 80_SST (CRUD), 40_RH/ASOs (read) |
| ECM_Diretoria | 90_Diretoria (CRUD), read em todas |
| Auditor_Externo | Read em escopo definido por auditoria, expira ao fim |

### Confidencialidade default
| Área | Default `confidentiality` |
|---|---|
| 00_SGQ/Documentos | Internal |
| 10_Operacao/Documentos | Internal |
| 10_Operacao/Registros/Validacao | Restricted |
| 20_Regulatorio | Restricted |
| 30_Comercial (contratos) | Restricted |
| 40_RH/Funcionarios | Confidential |
| 50_Financeiro | Confidential |
| 80_SST/ASOs | Confidential |
| 90_Diretoria | Confidential |

---

## Arquivos críticos a alinhar no afr_ecm

| Arquivo | Mudança |
|---|---|
| `addons/afr_ecm/data/document_type_data.xml` | Substituir 6 doc types genéricos por taxonomia CME (POP, IT, FORM, REG-VAL, REG-CAL, ASO, CONTRATO-CLI, AFE…) |
| `addons/afr_ecm/data/dms_directory_data.xml` (novo) | Seed das 10 áreas raiz + estrutura Documentos/Registros **com campo `description` populado a partir deste plano** |
| `addons/afr_ecm/data/dms_access_group_data.xml` | Grupos ECM_* conforme tabela acesso |
| `addons/afr_ecm/data/metadata_field_data.xml` (novo) | Campos cruzados (cliente_id, equipamento_id, norma, processo, validade) |
| `addons/afr_ecm/security/security.xml` | Grupos res.groups espelho dos dms.access.group |
| `addons/afr_ecm/views/dms_directory_views.xml` (novo) | Tornar campo `description` proeminente no form view + visível em tooltip da árvore |
| `ecm_desktop/` (Next.js) | Tree navigation respeitar prefix numérico; filtros por norma/cliente/processo; **painel lateral mostrando `description` ao selecionar pasta** |

---

## Feature: Description dos diretórios como "mini-manual" embarcado

### Motivação

Usuário navegando ECM deve entender o que vai em cada pasta sem precisar consultar plano externo. Cada pasta tem auto-documentação que aparece ao selecionar — guia inserção correta de documentos e reduz erros de classificação.

### afr_ecm — backend

**Campo `description` já existe** no OCA `dms.directory` (text/HTML, herdado). Não precisa adicionar campo — apenas garantir uso.

Mudanças:

1. **Seed XML (`dms_directory_data.xml`)** — cada `<record model="dms.directory">` traz `description` populada. Exemplos:

```xml
<record id="dir_10_operacao" model="dms.directory">
    <field name="name">10_Operacao</field>
    <field name="is_root_directory">True</field>
    <field name="description"><![CDATA[
<h3>Área 10 — Operação (Reprocessamento)</h3>
<p><strong>Escopo:</strong> documentos estáticos do processo CME conforme RDC 15/2012.
Registros transacionais de ciclos diários ficam em <code>afr_supervisorio_ciclos</code>.</p>
<p><strong>Norma-base:</strong> ANVISA RDC 15/2012 + ABNT NBR ISO 17665 (vapor) /
11135 (ETO) / 15883 (lavadora) / 11607 (embalagem).</p>
<p><strong>Subpastas:</strong></p>
<ul>
  <li><strong>Documentos/</strong> — POPs, ITs, formulários, fluxogramas, FMEA, URS.</li>
  <li><strong>Registros/</strong> — validações IQ/OQ/PQ, monitoramentos, eventos críticos,
      recalls, indicadores.</li>
</ul>
<p><strong>Onde inserir:</strong></p>
<ul>
  <li>POP novo? → <code>Documentos/02_POPs_Reprocessamento/&lt;etapa&gt;/</code></li>
  <li>Relatório IQ/OQ/PQ? → <code>Registros/01_Validacao_Processo/Equipamento_XX/</code></li>
  <li>BI positivo? → workflow automático em <code>Registros/07_Eventos_Criticos/Lotes_BI_Positivos/</code></li>
</ul>
<p><strong>Confidencialidade default:</strong> Internal (POPs) / Restricted (validações).</p>
]]></field>
</record>

<record id="dir_10_op_documentos" model="dms.directory">
    <field name="name">Documentos</field>
    <field name="parent_id" ref="dir_10_operacao"/>
    <field name="description"><![CDATA[
<h3>Documentos controláveis da Operação</h3>
<p>Apenas documentos <strong>vigentes</strong>, versionados, com aprovação RT/Qualidade.
Versões obsoletas: marcar campo <code>obsoleto=True</code> ou mover para subpasta <code>_obsoletos/</code>.</p>
<p><strong>Nomenclatura:</strong> <code>POP-OP-NNN_Titulo_v[VER]_AAAA-MM-DD.pdf</code></p>
<p><strong>Tipos aceitos:</strong> POP, Instrução de Trabalho (IT), Formulário Mestre (FORM), Fluxograma, Tabela Técnica, FMEA, URS.</p>
]]></field>
</record>
```

Mesma estrutura para as ~150 pastas do seed: cada uma com `description` específica explicando:
- O que vai ali (definição clara)
- Norma de referência (RDC art. X, ISO cl. Y)
- Exemplos de arquivos típicos
- Onde NÃO colocar (evitar erro de classificação)
- Nomenclatura esperada
- Confidencialidade/retenção default

2. **Form view (`views/dms_directory_views.xml`)** — promover `description`:

```xml
<record id="dms_directory_view_form_inherit_afr_ecm" model="ir.ui.view">
    <field name="name">dms.directory.form.afr_ecm</field>
    <field name="model">dms.directory</field>
    <field name="inherit_id" ref="dms.directory_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//notebook" position="inside">
            <page string="Manual da Pasta" name="page_description">
                <field name="description" widget="html"
                       options="{'collaborative': true}"
                       placeholder="Descreva o que vai nesta pasta, norma de referência, exemplos de arquivos, onde NÃO colocar..."/>
            </page>
        </xpath>
    </field>
</record>
```

3. **Tooltip na árvore** (opcional): tree view com `description` truncada em `<title>` ou via JS hover.

4. **Manifest version bump:** `__manifest__.py` → `16.0.X.Y.Z+1`.

### ecm_desktop — frontend

**Mudança:** painel de detalhes ao selecionar pasta exibe `description` renderizada (HTML sanitizado).

Estrutura proposta:

```
┌─────────────────────────────────────────────────────────┐
│  Tree (esq)            │  Detalhes pasta selecionada    │
│                        │  ─────────────────────────────  │
│  ▾ 00_SGQ              │  📁 10_Operacao                 │
│  ▾ 10_Operacao  ◄ sel  │                                 │
│    ▾ Documentos        │  ▼ Manual da Pasta              │
│    ▸ Registros         │  Área 10 — Operação...          │
│  ▸ 20_Regulatorio      │  Norma-base: RDC 15/2012...     │
│  ▸ 30_Comercial        │  Subpastas:                     │
│  ...                   │   • Documentos/ — POPs...       │
│                        │   • Registros/ — validações...  │
│                        │  Onde inserir:                  │
│                        │   • POP novo? → Documentos/...  │
│                        │                                 │
│                        │  ▼ Arquivos (42)                │
│                        │  [lista de files]               │
│                        │  ▼ Subpastas (2)                │
│                        │  [lista subpastas]              │
└─────────────────────────────────────────────────────────┘
```

**Implementação:**

1. **API call:** ampliar fetch existente de `dms.directory` p/ incluir `description` no `fields` do `search_read`:

```ts
// renderer/lib/api/directories.ts
const fields = ['id', 'name', 'parent_id', 'child_directory_ids', 'file_ids',
                'count_directories', 'count_files', 'description'];  // ← add
```

2. **Componente novo** `<DirectoryManualPanel />` no painel de detalhes:

```tsx
// renderer/components/dms/DirectoryManualPanel.tsx
import DOMPurify from 'isomorphic-dompurify';

export function DirectoryManualPanel({ directory }: { directory: Directory }) {
  if (!directory.description) return null;
  const safe = DOMPurify.sanitize(directory.description);
  return (
    <Collapsible defaultOpen>
      <CollapsibleTrigger>📖 Manual da Pasta</CollapsibleTrigger>
      <CollapsibleContent>
        <div className="prose prose-sm dark:prose-invert"
             dangerouslySetInnerHTML={{ __html: safe }} />
      </CollapsibleContent>
    </Collapsible>
  );
}
```

3. **Wizard de upload** (F4.1.1) lê `description` da pasta destino e mostra como hint inline no formulário de classificação ("Você está enviando para 10_Operacao/Documentos/02_POPs_Reprocessamento — esta pasta espera: POPs em formato `POP-OP-NNN_*_v[VER]_AAAA-MM-DD.pdf`").

4. **Search results:** quando usuário busca pasta por nome, mostrar primeira linha de `description` como preview.

### Dependências

- `isomorphic-dompurify` (sanitização HTML no renderer) — adicionar `package.json` ecm_desktop
- Backend: nada a instalar (campo existe nativo OCA dms)

### Benefícios

- Usuário não precisa decorar/consultar manual externo
- Plano vira documentação viva (cada pasta auto-explicativa)
- Reduz erros classificação → menos NC do tipo "documento em pasta errada"
- Onboarding novo colaborador acelerado
- Auditor enxerga critério de organização ao navegar (não precisa entrevistar)

### Manutenção

- Quando plano evolui (nova norma, mudança escopo), atualizar `description` da pasta envolvida via UI Odoo
- Versões podem ser tratadas via `description` mas histórico de mudanças via audit log (mixin já existente)

## Matriz Norma × Pasta (cobertura para auditoria)

Mapeamento das exigências documentais críticas → destino na taxonomia. Permite ao auditor localizar evidência objetivamente.

### RDC 15/2012 (ANVISA — boas práticas processamento PPS)

| Artigo/Cláusula | Exigência | Pasta destino |
|---|---|---|
| Art. 11 | Gerenciamento documentos (controle, registro, retenção) | `00_SGQ/Documentos/06_Procedimentos_Sistemicos/POP-SGQ-001/002` + `00_SGQ/Registros/13_Lista_Mestra_Distribuicao` |
| Art. 11 §1 | POPs por etapa processo | `10_Operacao/Documentos/02_POPs_Reprocessamento/` |
| Art. 12 | Responsabilidade Técnica nomeada | `20_Regulatorio/Documentos/03_Responsabilidade_Tecnica/RT_Titular` |
| Art. 13 | Programa Educação Permanente | `40_RH/Documentos/03_Competencias_Treinamento/Matriz_Treinamento_Anual` + `40_RH/Registros/03_Treinamentos_Coletivos` |
| Art. 14 | Capacitação inicial + reciclagem | `40_RH/Registros/01_Funcionarios_Ativos/.../03_Treinamentos_Realizados` |
| Art. 15 | Saúde ocupacional (PCMSO + imunização Hep B/dT/tríplice) | `80_SST/Documentos/02_Programas_Legais/PCMSO` + `80_SST/Registros/10_Vacinacao_NR32` |
| Cap. III | Estrutura física (áreas suja/limpa/estéril) | `70_Engenharia_Manutencao/Documentos/06_Predial/Plantas_Arquitetonicas` + `10_Operacao/Documentos/05_Fluxogramas/Mapa_Areas_Fisicas` |
| Cap. IV | Equipamentos qualificados (IQ/OQ/PQ) | `10_Operacao/Registros/01_Validacao_Processo/Equipamento_XX/03_IQ_Instalacao` etc. |
| Cap. V Art. 67 | Águas reprocessamento (potabilidade, condutividade) | `10_Operacao/Registros/05_Monitoramento_Utilidades/Agua` |
| Cap. VI Art. 76-87 | Etapas processamento (recepção→limpeza→preparo→esterilização→armazenamento→distribuição) | `10_Operacao/Documentos/02_POPs_Reprocessamento/01–13` |
| Art. 88-90 | Monitoramento esterilização (físico/químico/biológico) | `10_Operacao/Documentos/02_POPs_Reprocessamento/10_Monitoramento_Carga` + `10_Operacao/Registros/04_Monitoramentos_Rotineiros` |
| Art. 91 | Liberação carga | `10_Operacao/Documentos/02_POPs_Reprocessamento/11_Liberacao_Carga` |
| Art. 99-101 | Rastreabilidade (5 anos mín) | `afr_supervisorio_ciclos` (transacional) + sumários em `10_Operacao/Registros/04_Monitoramentos_Rotineiros/Resumos_Ciclos` |
| Art. 102-104 | Validação processo + revalidação anual | `10_Operacao/Registros/01_Validacao_Processo/.../06_Requalificacao_Anual` |
| Art. 105-108 | Recall (procedimento + execução) | `10_Operacao/Documentos/02_POPs_Reprocessamento/14_Recall_Tecnovigilancia` + `10_Operacao/Registros/08_Recalls` |
| Art. 109-110 | Tecnovigilância (NOTIVISA) | `10_Operacao/Registros/09_Tecnovigilancia` + `20_Regulatorio/Registros/05_Tecnovigilancia` |
| Art. 111 | PGRSS | `80_SST/Documentos/07_PGRSS_Residuos_Saude` + `80_SST/Registros/14_PGRSS_Execucao` |

### ABNT NBR ISO 9001:2015

| Cláusula | Exigência | Pasta destino |
|---|---|---|
| 4.1-4.2 | Contexto + partes interessadas | `00_SGQ/Documentos/04_Contexto_Organizacao` |
| 4.3-4.4 | Escopo + processos do SGQ | `00_SGQ/Documentos/04_Contexto_Organizacao/Escopo_SGQ` + `03_Mapa_Processos` |
| 5.1-5.3 | Liderança, política, responsabilidades | `00_SGQ/Documentos/02_Politica_Objetivos` + `90_Diretoria/Documentos/03_Organograma_RACI` |
| 6.1 | Riscos e oportunidades | `00_SGQ/Registros/09_Gestao_Riscos` |
| 6.2 | Objetivos da qualidade | `00_SGQ/Documentos/02_Politica_Objetivos/Objetivos_Qualidade_AAAA` |
| 6.3 | Planejamento de mudanças | `00_SGQ/Registros/08_Solicitacoes_Mudanca_RDM` |
| 7.1 | Recursos (pessoas, infra, ambiente, M&M) | `40_RH` + `70_Eng_Manutencao` + `10_Op/Registros/06_Monitoramento_Ambiente` + `70_Eng/Registros/.../04_Calibracao` |
| 7.2 | Competência | `40_RH/Documentos/03_Competencias_Treinamento/Matriz_Competencias_Cargo` |
| 7.3 | Conscientização | `40_RH/Registros/.../03_Treinamentos_Realizados/Integracao_Admissional` |
| 7.4 | Comunicação | `00_SGQ/Documentos/06_Procedimentos_Sistemicos/POP-SGQ-009` + `00_SGQ/Registros/14_Comunicacoes_Internas` |
| 7.5 | Informação documentada | `00_SGQ/Documentos/05_Lista_Mestra_Documentos` + `00_SGQ/Documentos/06_Procedimentos_Sistemicos/POP-SGQ-001/002` |
| 8.1 | Planejamento e controle operacional | `10_Operacao/Documentos/01_Governanca_Processo` |
| 8.2 | Requisitos cliente | `30_Comercial/Registros/01_Clientes_Ativos/.../04_Especificacoes_Tecnicas_Cliente` |
| 8.4 | Controle processos externos (fornecedores) | `00_SGQ/Registros/16_Qualificacao_Fornecedores` |
| 8.5 | Produção e provisão serviço | `10_Operacao/` (todo) |
| 8.5.2 | Identificação e rastreabilidade | `afr_supervisorio_ciclos` + `10_Op/Documentos/02_POPs_Reprocessamento/01_Recepcao_PPS/POP-OP-003` |
| 8.6 | Liberação produto | `10_Op/Documentos/02_POPs/11_Liberacao_Carga` + `10_Op/Registros/07_Eventos_Criticos/Liberacao_Excepcional` |
| 8.7 | Controle saída não-conforme | `00_SGQ/Registros/05_Nao_Conformidades` + `10_Op/Registros/07_Eventos_Criticos` |
| 9.1 | Monitoramento, medição, análise | `00_SGQ/Registros/10_Indicadores_KPI` |
| 9.1.2 | Satisfação cliente | `30_Comercial/Registros/01_Clientes_Ativos/.../09_Pesquisa_Satisfacao` + `00_SGQ/Registros/11_Pesquisa_Satisfacao` |
| 9.2 | Auditoria interna | `00_SGQ/Registros/02_Auditorias_Internas` |
| 9.3 | Análise crítica direção | `00_SGQ/Registros/01_Analise_Critica_Direcao` |
| 10.2 | Não-conformidade e ação corretiva | `00_SGQ/Registros/05_Nao_Conformidades` + `06_CAPA` |
| 10.3 | Melhoria contínua | `00_SGQ/Registros/15_Licoes_Aprendidas` |

### ABNT NBR ISO 13485:2016 (adicional/complementar)

| Cláusula | Exigência | Pasta destino |
|---|---|---|
| 4.1.6 | Validação software (CSV) | `60_TI/Documentos/06_Validacao_Sistemas_Computadorizados` + `60_TI/Registros/01_Validacao_Sistemas_Computadorizados` |
| 4.2.3 | Arquivo Mestre do Dispositivo (DMR) | `00_SGQ/Documentos/07_Procedimentos_Especificos_ISO13485/POP-13485-001` |
| 7.4 | Controle compras / Qualidade fornecedor | `00_SGQ/Registros/16_Qualificacao_Fornecedores` + `30_Comercial/Documentos/02_Modelos_Contratuais/Quality_Agreement_QA` |
| 7.5.6 | Validação processos especiais (esterilização) | `10_Op/Registros/01_Validacao_Processo` |
| 7.5.7 | Validação esterilização específica | idem + `10_Op/Documentos/02_POPs/09_Esterilizacao` |
| 7.5.8 | Identificação (UDI) | `00_SGQ/Documentos/07_Procedimentos_Especificos_ISO13485/POP-13485-003` |
| 8.2.1 | Feedback (vigilância pós-mercado) | `00_SGQ/Documentos/07_Procedimentos_Especificos_ISO13485/POP-13485-002` + `30_Comercial/Registros/01_Clientes_Ativos/.../08_Reclamacoes` |
| 8.2.2 | Tratamento reclamação | idem + `00_SGQ/Registros/07_Reclamacoes_Clientes` |
| 8.3.3 | Notificações autoridades regulatórias | `20_Regulatorio/Registros/05_Tecnovigilancia` + `10_Op/Registros/09_Tecnovigilancia` |

### ABNT NBR ISO 17665 (validação vapor) / 11135 (ETO) / 15883 (lavadora) / 11607 (embalagem)

| Norma | Exigência | Pasta destino |
|---|---|---|
| ISO 17665 | Validação esterilização vapor (DQ/IQ/OQ/PQ + revalidação anual) | `10_Op/Registros/01_Validacao_Processo/Equipamento_XX_Autoclave` |
| ISO 11135 | Validação ETO (gás, ciclo, residuais) | `10_Op/Registros/01_Validacao_Processo/Equipamento_XX_ETO` |
| ISO 15883 | Validação lavadora-termodesinfectora | `10_Op/Registros/03_Validacao_Lavagem` |
| ISO 11607 | Validação embalagem + seladora | `10_Op/Registros/02_Validacao_Embalagem_Selagem` |
| ISO 11138/11140 | Indicadores biológicos/químicos | `10_Op/Documentos/02_POPs/10_Monitoramento_Carga` + `10_Op/Registros/04_Monitoramentos_Rotineiros` |
| EN 285 | Qualidade vapor (NCG, dryness, superheat) | `70_Eng_Manutencao/Registros/02_Utilidades_Operacao/Caldeira_Vapor` |
| ISO 8573 | Qualidade ar comprimido | `70_Eng_Manutencao/Registros/02_Utilidades_Operacao/Compressor` |

### Normas trabalhistas/SST/Ambiental

| Norma | Exigência | Pasta destino |
|---|---|---|
| NR-1 | PGR + GRO | `80_SST/Documentos/02_Programas_Legais/PGR_Programa_Gerenciamento_Riscos` |
| NR-5 | CIPA + SIPAT | `80_SST/Registros/01_CIPA` |
| NR-6 | EPI (matriz, entrega, treinamento) | `80_SST/Documentos/05_Especificacoes_EPI` + `80_SST/Registros/07_EPI_Entregas` |
| NR-7 | PCMSO + ASO 20a | `80_SST/Documentos/02_Programas_Legais/PCMSO` + `80_SST/Registros/02_ASOs` |
| NR-10 | Eletricidade (laudo, treinamento) | `70_Eng/Documentos/06_Predial/Laudo_Eletrico_NR10` + `80_SST/Registros/06_Treinamentos_NR/NR-10` |
| NR-12 | Máquinas (LOTO, segurança) | `80_SST/Documentos/03_Procedimentos_SST/POP-SST-008_LOTO` |
| NR-13 | Caldeiras + vasos pressão | `70_Eng/Registros/02_Utilidades_Operacao/Caldeira_Vapor/NR13_Inspecao_Anual` |
| NR-23 | Proteção incêndio (AVCB, brigada) | `20_Regulatorio/Documentos/02_Licencas_Sanitarias/AVCB_Bombeiros` + `80_SST/Registros/06_Treinamentos_NR/Brigada_Incendio` |
| **NR-32 (★)** | Saúde/segurança serviços saúde | `80_SST/Documentos/06_NR_Aplicaveis/NR-32_Servicos_Saude` + `80_SST/Registros/05_Acidente_Biologico_Perfurocortante` |
| NR-35 | Trabalho altura | `80_SST/Registros/06_Treinamentos_NR/NR-35_Altura` |
| RDC 222/2018 | PGRSS | `80_SST/Documentos/07_PGRSS_Residuos_Saude` + `80_SST/Registros/14_PGRSS_Execucao` |
| Lei 13.589/2018 | PMOC HVAC | `70_Eng/Documentos/05_Utilidades/Climatizacao_HVAC/PMOC` + `70_Eng/Registros/02_Utilidades_Operacao/HVAC/PMOC_Execucao` |
| NBR 5419 | SPDA | `70_Eng/Documentos/06_Predial/Laudo_SPDA_Para_raios` + `70_Eng/Registros/03_Predial/SPDA` |

### LGPD + Compliance

| Norma | Exigência | Pasta destino |
|---|---|---|
| LGPD Art. 37 | ROPA (Registro Atividades Tratamento) | `20_Regulatorio/Documentos/05_LGPD/ROPA_Registro_Atividades_Tratamento` |
| LGPD Art. 38 | DPIA/RIPD | `20_Regulatorio/Documentos/05_LGPD/DPIA_RIPD_Modelo` + `20_Reg/Registros/06_LGPD_Operacao/DPIAs_Realizadas` |
| LGPD Art. 41 | DPO/Encarregado | `20_Regulatorio/Documentos/05_LGPD/Designacao_DPO_Encarregado` |
| LGPD Art. 48 | Notificação incidente ANPD | `20_Regulatorio/Registros/06_LGPD_Operacao/Incidentes_Vazamento_Dados` |
| Lei 12.846 (Anticorrupção) | Programa compliance | `20_Regulatorio/Documentos/04_Politicas_Compliance` + `20_Reg/Registros/08_Auditorias_Compliance` |
| Lei 13.709 (LGPD) — Atendimento titular | Requisição titular | `20_Reg/Registros/06_LGPD_Operacao/Requisicoes_Titulares` |

> Matriz não exaustiva — adicionar progressivamente conforme contrato exigir norma específica de cliente (ex: PORT 4/2002 INMETRO p/ instrumentos; RDC 67/2009 SUD; outras estaduais).

---

## Verificação

1. **Compliance dryrun:** revisão por especialista de qualidade (RT) contra checklist RDC 15 art. 11–13 (gerenciamento documentos) usando matriz norma×pasta acima
2. **Confirmar retenções:** validar com consultor trabalhista as linhas marcadas "recomendado 30a precaução" (RH) — STF RE 522.897 mudou base legal
3. **Teste navegação:** usuário operacional encontra POP de embalagem em ≤3 cliques (`10_Operacao/Documentos/02_POPs_Reprocessamento/08_Embalagem`)
4. **Teste auditoria:** auditor encontra IQ/OQ/PQ de autoclave em ≤2 cliques (`10_Op/Registros/01_Validacao_Processo/Equipamento_XX_Autoclave`)
5. **Teste retenção:** simular expiração de ASO + AFE + contrato — alerta cron afr_ecm dispara nos prazos definidos por `document_type.retention_days`
6. **Migração:** plano de mapeamento dos 6 doc types atuais (Contrato, Fatura, RH-Admissão, RH-ASO, Ata, Certificado) → nova taxonomia

---

## Estado de implementação (2026-05-13)

**Aplicado via odoo-mcp no profile `odoo-ecm-teste-local` (db: odoo_ecm_test, port 8083):**

### Backend afr_ecm v16.0.1.4.0
- `models/dms_directory.py` — campo `description` (Html, sanitize=True) adicionado ao `dms.directory`
- `views/dms_directory_views.xml` — aba "Manual da Pasta" no form (widget=html)
- `__manifest__.py` — version 16.0.1.3.6 → 16.0.1.4.0
- Módulo upgraded via `ir.module.module.button_immediate_upgrade()`

### Estrutura criada (30 directories)
Filhas da raiz pré-existente "DOCUMENTAÇÃO" (id=11):

| Área | ID | Documentos | Registros |
|---|---|---|---|
| 00_SGQ | 54 | 64 | 74 |
| 10_Operacao | 55 | 65 | 75 |
| 20_Regulatorio | 56 | 66 | 76 |
| 30_Comercial | 57 | 67 | 77 |
| 40_RH | 58 | 68 | 78 |
| 50_Financeiro_Fiscal | 59 | 69 | 79 |
| 60_TI | 60 | 70 | 80 |
| 70_Engenharia_Manutencao | 61 | 71 | 81 |
| 80_SST | 62 | 72 | 82 |
| 90_Diretoria | 63 | 73 | 83 |

Cada diretório com `description` HTML populada como mini-manual (escopo, normas, subpastas, onde inserir, nomenclatura, confidencialidade).

### Legacy preservado (não migrado)
- `Administração/` (id=15) — subpastas: Documentação Empresa (48), RH (45)
- `MANUAIS/` (id=53)
- `POPS/` (id=13) — subpastas: Contratos (9), Produção (14)

Migração para nova taxonomia: pendente decisão user.

### Pendente (fases seguintes)
- Subpastas dentro de cada Documentos/Registros (estrutura granular do spec)
- ecm_desktop: componente DirectoryManualPanel + API fetch description
- Doc types específicos por área (substituir 6 genéricos)
- Grupos ECM_* + dms.access.group
- Workflows críticos (CAPA-NC, recall, NOTIVISA, renovação licenças)
- Migração dados legacy

---

## Próximos passos (escopo futuro — fora deste brainstorm)

Conteúdo abaixo é **input para writing-plans posterior**, não parte do design aprovado neste brainstorm:

1. **Validação humana:** revisão pelo RT da empresa + Jurídico (retenções) + DPO (LGPD)
2. **writing-plans:** detalhar implementação no afr_ecm:
   - Seed XML: `dms_directory_data.xml` (estrutura inicial 10 áreas), `document_type_data.xml` (novos codes), `dms_access_group_data.xml`, `metadata_field_data.xml`, `res_groups_data.xml`
   - Migration script: mapear 6 doc types atuais → novos códigos; mover diretórios existentes
   - Cron jobs: renovação licenças, expiração contratos, expiração ASO, sumarização mensal ciclos
   - Workflows críticos: CAPA-NC, recall, tecnovigilância NOTIVISA, LGPD incidente, revogação acesso pós-rescisão
   - Integrações: `afr_supervisorio_ciclos` (sumários mensais), `maintenance.equipment` (cadastro único), `hr.employee` (matriz acesso automática), `res.partner` (`cliente_id`)
   - UI ecm_desktop: tree respeitando prefix numérico, filtros por norma/cliente/processo
3. **Roll-out faseado:**
   - F1: SGQ + Regulatório (estrutura básica, todas licenças carregadas)
   - F2: Operação (POPs + validações)
   - F3: RH + SST
   - F4: Comercial + Eng + Financeiro
   - F5: TI + Diretoria
4. **Treinamento usuários:** matriz de competência ECM por perfil + curso de uso ecm_desktop + reciclagem anual
