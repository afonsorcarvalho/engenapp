# -*- coding: utf-8 -*-
"""
Testes que usam arquivos sintéticos em ``tests/fixtures/`` (padrão de nome
``YYYYMMDD_HHMMSS_Ciclo_*.txt``).

Os fixtures AFR13 exercitam leitura correta, dados faltantes e formatos corrompidos.
O fixture estilo Baumer (mesmo perfil do arquivo de referência na pasta ``fita_digital/``)
documenta que o ``ReaderFitaDigitalAfr13`` **não** é o leitor desse formato.

Execução::

    PYTHONPATH=. python -m unittest fita_digital.tests.test_fixture_arquivos -v
"""
from __future__ import annotations

import logging
import sys
import unittest
from datetime import datetime
from pathlib import Path

_ADDON_ROOT = Path(__file__).resolve().parents[2]
if str(_ADDON_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADDON_ROOT))

from fita_digital.data_object.dataobject_fita_digital import DataObjectFitaDigital
from fita_digital.reader_fita_digital.reader_fita_digital_afr13 import ReaderFitaDigitalAfr13

# Diretório de fixtures ao lado deste módulo (descoberta unittest não exige pacote fita_digital.tests.*).
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _path(name: str) -> Path:
    return FIXTURES_DIR / name


class TestFixturesAfr13Valido(unittest.TestCase):
    """Fixture ``*_valid_afr13.txt``: fluxo completo e integração com DataObject."""

    def setUp(self):
        self.fp = _path("20251001_152420_Ciclo_002509_valid_afr13.txt")
        self.assertTrue(self.fp.is_file(), f"Fixture ausente: {self.fp}")

    def test_read_header_e_corpo(self):
        r = ReaderFitaDigitalAfr13(str(self.fp))
        h = r.read_header()
        self.assertIsInstance(h["Data:"], datetime)
        b = r.read_body()
        self.assertGreater(len(b["data"]), 0)
        self.assertGreater(len(b["fase"]), 0)
        self.assertEqual(b["header_columns"][0], "Hora")

    def test_get_state_concluido(self):
        r = ReaderFitaDigitalAfr13(str(self.fp))
        r.read_body()
        self.assertEqual(r.get_state(), "concluido")

    def test_dataobject_read_all_fita(self):
        folder = str(self.fp.parent) + "/"
        do = DataObjectFitaDigital(directory_path=folder)
        do.register_reader_fita(ReaderFitaDigitalAfr13(str(self.fp)))
        header, body = do.read_all_fita()
        self.assertIsInstance(header["Data:"], datetime)
        self.assertIsInstance(body["fase"][0][0], datetime)


class TestFixturesAfr13CabecalhoInvalido(unittest.TestCase):
    """Cabeçalho ausente, formato errado, truncado ou com bytes nulos."""

    def test_sem_chave_data_keyerror_ao_converter_data(self):
        fp = _path("20251001_152420_Ciclo_002509_sem_chave_data.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        with self.assertRaises(KeyError):
            r.read_header()

    def test_data_iso_valueerror(self):
        fp = _path("20251001_152420_Ciclo_002509_data_formato_iso.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        with self.assertRaises(ValueError):
            r.read_header()

    def test_header_com_null_na_data_valueerror(self):
        fp = _path("20251001_152420_Ciclo_002509_header_com_null.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        with self.assertRaises(ValueError):
            r.read_header()

    def test_arquivo_vazio_keyerror_ou_falha_cabecalho(self):
        fp = _path("20251001_152420_Ciclo_002509_vazio.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        with self.assertRaises(KeyError):
            r.read_header()


class TestFixturesAfr13CorpoFragil(unittest.TestCase):
    """Corpo mínimo, linhas inválidas ou medições não numéricas."""

    def test_truncado_read_body_retorna_body_antigo_vazio(self):
        """
        Poucas linhas: após size_header não há corpo; o laço de ``read_body`` não
        executa e ``self.body`` pode permanecer ``{}`` (comportamento atual do AFR13).
        """
        fp = _path("20251001_152420_Ciclo_002509_arquivo_truncado.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        h = r.read_header()
        self.assertIsInstance(h["Data:"], datetime)
        b = r.read_body()
        self.assertEqual(b, {})

    def test_somente_fases_sem_medicao_corpo_fica_vazio_no_reader(self):
        """
        Se após o cabeçalho de colunas só existem linhas de fase, o AFR13 nunca
        atribui ``self.body = body_dict`` no laço (só após processar medição).
        Retorno: ``{}`` e ``get_state`` → ``erro``.
        """
        fp = _path("20251001_152420_Ciclo_002509_corpo_so_fases.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        r.read_header()
        b = r.read_body()
        self.assertEqual(b, {})
        logging.disable(logging.CRITICAL)
        try:
            self.assertEqual(r.get_state(), "erro")
        finally:
            logging.disable(logging.NOTSET)

    def test_primeira_linha_corpo_invalida(self):
        """Primeira linha do corpo não é cabeçalho de colunas esperado."""
        fp = _path("20251001_152420_Ciclo_002509_corpo_primeira_linha_invalida.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        r.read_header()
        b = r.read_body()
        self.assertEqual(b["header_columns"][0], "esta")

    def test_medicao_com_texto_nao_numerico_ignora_ou_reduz_linhas(self):
        """Letras no lugar de número: regex ou float falha; segunda linha válida permanece."""
        fp = _path("20251001_152420_Ciclo_002509_medicao_nao_numerica.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        r.read_header()
        b = r.read_body()
        self.assertEqual(len(b["data"]), 1)
        self.assertEqual(b["data"][0][0], "15:24:30")


class TestFixtureBaumerFormatoErradoParaAfr13(unittest.TestCase):
    """
    Amostra no formato Baumer/Steriliza (como ``fita_digital/20251001_152420_Ciclo_002509.txt``).

    O AFR13 espera ``Data:`` (case e layout diferentes de ``DATA:`` em linha Baumer).
    """

    def test_read_header_falha_sem_campo_data_padrao(self):
        fp = _path("20251001_152420_Ciclo_002509_baumer_estilo_amostra.txt")
        r = ReaderFitaDigitalAfr13(str(fp))
        with self.assertRaises(KeyError):
            r.read_header()


if __name__ == "__main__":
    unittest.main()
