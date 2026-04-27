# -*- coding: utf-8 -*-
"""
Arquivos de fita sintéticos (padrão de nome como ``20251001_152420_Ciclo_002509.txt``).

Compatíveis com ``ReaderFitaDigitalAfr13`` (24 linhas de cabeçalho + corpo), exceto onde indicado:

- ``20251001_152420_Ciclo_002509_valid_afr13.txt`` — ciclo mínimo válido.
- ``20251001_152420_Ciclo_002509_sem_chave_data.txt`` — sem campo ``Data:`` (usa ``Fecha:``).
- ``20251001_152420_Ciclo_002509_data_formato_iso.txt`` — data fora de ``%d-%m-%Y``.
- ``20251001_152420_Ciclo_002509_arquivo_truncado.txt`` — arquivo curto (corpo vazio após header).
- ``20251001_152420_Ciclo_002509_corpo_so_fases.txt`` — só fases, sem linhas de medição.
- ``20251001_152420_Ciclo_002509_corpo_primeira_linha_invalida.txt`` — primeira linha do corpo inválida.
- ``20251001_152420_Ciclo_002509_medicao_nao_numerica.txt`` — token não numérico na medição.
- ``20251001_152420_Ciclo_002509_vazio.txt`` — arquivo vazio.
- ``20251001_152420_Ciclo_002509_header_com_null.txt`` — byte NUL corrompendo a data (UTF-8).
- ``20251001_152420_Ciclo_002509_baumer_estilo_amostra.txt`` — amostra estilo Baumer (não é AFR13).

Os testes que consomem estes arquivos estão em ``test_fixture_arquivos.py``.
"""

from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent
