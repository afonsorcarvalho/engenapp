# -*- coding: utf-8 -*-
"""
Testes standalone para ``ReaderFitaDigitalInterface`` e implementações (AFR13, AFR14 MedPlast).

Valida erros com dados faltantes/fora do padrão, coesão da hierarquia e integração mínima
com ``DataObjectFitaDigital`` (registro do leitor e leitura completa).

Execução (raiz do addon)::

    PYTHONPATH=. python -m unittest discover -s fita_digital/tests -p "test_*.py"
"""
from __future__ import annotations

import logging
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

_ADDON_ROOT = Path(__file__).resolve().parents[2]
if str(_ADDON_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADDON_ROOT))

from fita_digital.data_object.dataobject_fita_digital import DataObjectFitaDigital
from fita_digital.reader_fita_digital.reader_fita_digital import ReaderFitaDigitalInterface
from fita_digital.reader_fita_digital.reader_fita_digital_afr13 import ReaderFitaDigitalAfr13
from fita_digital.reader_fita_digital.reader_fita_digital_afr14_medplast import (
    ReaderFitaDigitalAfr14Medplast,
)


def _afr13_minimal_file_lines():
    """
    Conteúdo mínimo coerente com ReaderFitaDigitalAfr13 (size_header=24 linhas).

    Cabeçalho: campos esperados pela leitura genérica; ``Data:`` em ``%d-%m-%Y``.
    Corpo: primeira linha = colunas; depois medições e fases.
    """
    header = []
    header.append("Data: 15-03-2024")
    header.append("Hora: 10:00:00")
    header.append("Equipamento: ETO01")
    header.append("Operador: TESTE")
    header.append("Cod. ciclo: 123")
    header.append("Ciclo Selecionado: CICLO 01")
    while len(header) < 24:
        header.append("")
    body = [
        "Hora PCI(Bar) TCI(Celsius) UR(%)",
        "10:00:01 0.0 25.0 50.0",
        "10:00:02 -0.1 25.5 51.0",
        "10:00:10 LEAK-TEST",
        "10:00:11 0.0 26.0 52.0",
        "10:05:00 CICLO FINALIZADO",
    ]
    return "\n".join(header + body) + "\n"


class TestReaderFitaDigitalInterface(unittest.TestCase):
    """Contrato da interface: classe abstrata não instanciável; caminho vazio na subclasse concreta."""

    def test_full_path_vazio_na_subclasse_concreta_lanca_valueerror(self):
        """A validação de ``full_path_file`` está no ``__init__`` da interface (via super nas filhas)."""
        with self.assertRaises(ValueError) as ctx:
            ReaderFitaDigitalAfr13("")
        self.assertIn("full_path_file", str(ctx.exception).lower())

    def test_interface_nao_instanciavel_sem_subclasse(self):
        """ABC exige implementação dos métodos abstratos."""
        with self.assertRaises(TypeError):
            ReaderFitaDigitalInterface(full_path_file="/tmp/inexistente.txt")


class TestReaderFitaDigitalAfr13ArquivoMinimo(unittest.TestCase):
    """Leitor AFR13 com arquivo temporário: fluxo feliz e estrutura do body."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "ciclo.txt"
        self.path.write_text(_afr13_minimal_file_lines(), encoding="utf-8")
        self.reader = ReaderFitaDigitalAfr13(str(self.path))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_read_header_data_e_datetime(self):
        h = self.reader.read_header()
        self.assertIsInstance(h["Data:"], datetime)
        self.assertEqual(h["Data:"].year, 2024)
        self.assertEqual(h["Data:"].month, 3)
        self.assertEqual(h["Data:"].day, 15)

    def test_read_body_colunas_data_e_fases(self):
        b = self.reader.read_body()
        self.assertIn("header_columns", b)
        self.assertIn("data", b)
        self.assertIn("fase", b)
        self.assertEqual(b["header_columns"][0], "Hora")
        self.assertEqual(len(b["data"]), 3)
        self.assertTrue(all(isinstance(row[0], str) for row in b["data"]))
        self.assertEqual(len(b["fase"]), 2)
        self.assertEqual(b["fase"][0][1], "LEAK-TEST")

    def test_get_state_concluido_quando_consta_finalizado(self):
        self.reader.read_body()
        self.assertEqual(self.reader.get_state(), "concluido")

    def test_get_state_erro_sem_corpo_carregado(self):
        """Sem read_body, ``body`` não tem chave ``fase`` → fluxo documentado retorna 'erro'."""
        fresh = ReaderFitaDigitalAfr13(str(self.path))
        logging.disable(logging.CRITICAL)
        try:
            self.assertEqual(fresh.get_state(), "erro")
        finally:
            logging.disable(logging.NOTSET)


class TestReaderFitaDigitalAfr13DadosInvalidos(unittest.TestCase):
    """Dados fora do padrão esperado pelo AFR13."""

    def test_read_header_data_formato_invalido_lanca_valueerror(self):
        header = ["Data: 2024-03-15"]
        while len(header) < 24:
            header.append("")
        body = ["Hora X", "10:00:00 1.0"]
        content = "\n".join(header + body) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.txt"
            p.write_text(content, encoding="utf-8")
            r = ReaderFitaDigitalAfr13(str(p))
            with self.assertRaises(ValueError):
                r.read_header()

    def test_linha_medicao_nao_correspondente_regex_nao_entra_em_data(self):
        lines = _afr13_minimal_file_lines().splitlines()
        # Insere linha inválida (não bate no regex de medição)
        insert_at = 24 + 1
        lines.insert(insert_at, "texto_sem_horario_valido")
        content = "\n".join(lines) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ciclo.txt"
            p.write_text(content, encoding="utf-8")
            r = ReaderFitaDigitalAfr13(str(p))
            b = r.read_body()
            self.assertEqual(len(b["data"]), 3)


class TestReaderFitaDigitalAfr14Heranca(unittest.TestCase):
    """Coesão: AFR14 MedPlast estende AFR13 sem quebrar leitura."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "ciclo.txt"
        self.path.write_text(_afr13_minimal_file_lines(), encoding="utf-8")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_e_subclasse_de_afr13(self):
        self.assertTrue(issubclass(ReaderFitaDigitalAfr14Medplast, ReaderFitaDigitalAfr13))

    def test_read_header_e_read_body_iguais_ao_afr13(self):
        r13 = ReaderFitaDigitalAfr13(str(self.path))
        r14 = ReaderFitaDigitalAfr14Medplast(str(self.path))
        self.assertEqual(r13.read_header(), r14.read_header())
        b13, b14 = r13.read_body(), r14.read_body()
        self.assertEqual(b13["header_columns"], b14["header_columns"])
        self.assertEqual(b13["data"], b14["data"])
        self.assertEqual(b13["fase"], b14["fase"])


class TestReaderMetodosAuxiliaresBase(unittest.TestCase):
    """Métodos herdados de ``ReaderFitaDigitalInterface`` (coesão body / estatísticas)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "ciclo.txt"
        self.path.write_text(_afr13_minimal_file_lines(), encoding="utf-8")
        self.reader = ReaderFitaDigitalAfr13(str(self.path))
        self.reader.read_body()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_get_fases_filtra_nomes(self):
        nomes = self.reader.get_fases(["LEAK-TEST", "OUTRA"])
        self.assertEqual(nomes, ["LEAK-TEST"])

    def test_get_parametros_exclui_primeira_coluna(self):
        p = self.reader.get_parametros()
        self.assertEqual(p, ["PCI(Bar)", "TCI(Celsius)", "UR(%)"])

    def test_calcular_tempo_entre_fases_com_horarios_string_retorna_prefixo_erro(self):
        """
        ``calcular_tempo_entre_fases`` na interface usa datetime em ``fase[i][0]``.
        Após ``read_body`` do AFR13 os horários de fase ainda são strings → operação inválida.
        """
        out = self.reader.calcular_tempo_entre_fases("LEAK-TEST", "CICLO FINALIZADO")
        self.assertIsInstance(out, str)
        self.assertTrue(out.startswith("Erro:"))

    def test_compute_statistics_sem_body_lanca_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            self.reader.compute_statistics(phases=["A"], header={}, body=None)
        self.assertIn("carregados", str(ctx.exception).lower())

    def test_compute_statistics_sem_fases_lanca_valueerror(self):
        body = {"data": [[datetime.now(), 1.0]], "fase": []}
        with self.assertRaises(ValueError) as ctx:
            self.reader.compute_statistics(phases=None, header={}, body=body)
        self.assertIn("fases", str(ctx.exception).lower())


class TestDataObjectComReaderAfr13(unittest.TestCase):
    """Integração mínima DataObject + ReaderFitaDigitalAfr13 (como no uso real)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmpdir.name)
        self.file_path = self.folder / "ciclo.txt"
        self.file_path.write_text(_afr13_minimal_file_lines(), encoding="utf-8")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_read_all_fita_converte_fase_para_datetime(self):
        do = DataObjectFitaDigital(directory_path=str(self.folder) + "/")
        do.register_reader_fita(ReaderFitaDigitalAfr13(str(self.file_path)))
        header, body = do.read_all_fita()
        self.assertIsInstance(header["Data:"], datetime)
        self.assertTrue(body["fase"])
        self.assertIsInstance(body["fase"][0][0], datetime)

    def test_calcular_tempo_entre_fases_dataobject_apos_read_all(self):
        """Após conversão no DataObject, tempos de fase são datetime e o cálculo é coerente."""
        do = DataObjectFitaDigital(directory_path=str(self.folder) + "/")
        do.register_reader_fita(ReaderFitaDigitalAfr13(str(self.file_path)))
        do.read_all_fita()
        s = do.calcular_tempo_entre_fases(0, 1)
        self.assertRegex(s, r"^\d{2}:\d{2}:\d{2}$")


if __name__ == "__main__":
    unittest.main()
