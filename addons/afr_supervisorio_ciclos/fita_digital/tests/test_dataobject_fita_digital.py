# -*- coding: utf-8 -*-
"""
Testes unitários standalone para DataObjectFitaDigital.

Cenários: dados faltantes ou fora do padrão esperado pelo processamento da fita.
Não dependem do framework Odoo.

Execução a partir da raiz do addon ``afr_supervisorio_ciclos``::

    PYTHONPATH=. python -m unittest discover -s fita_digital/tests -p "test_*.py"

Pytest costuma carregar ``afr_supervisorio_ciclos/__init__.py`` (Odoo); prefira unittest.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

# Raiz do addon (pai de ``fita_digital``) para importar o pacote sem odoo.addons.
_ADDON_ROOT = Path(__file__).resolve().parents[2]
if str(_ADDON_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADDON_ROOT))

from fita_digital.data_object.dataobject_fita_digital import DataObjectFitaDigital


def _reader_with_header_fields():
    """Mock mínimo de reader com ``header_fields.date_key`` como na interface real."""
    reader = MagicMock()
    hf = MagicMock()
    hf.date_key = "Data:"
    reader.header_fields = hf
    reader.get_state.return_value = "em_andamento"
    return reader


class TestDataObjectFitaDigitalInitAndReader(unittest.TestCase):
    """Construtor e registro de leitor."""

    def test_init_directory_path_vazio_lanca_valueerror(self):
        """directory_path vazio deve gerar ValueError (regra do __init__)."""
        with self.assertRaises(ValueError) as ctx:
            DataObjectFitaDigital(directory_path="")
        self.assertIn("caminho do diretório", str(ctx.exception).lower())

    def test_set_size_header_sem_register_reader_lanca_valueerror(self):
        """set_size_header exige reader registrado previamente."""
        do = DataObjectFitaDigital(directory_path="/tmp")
        with self.assertRaises(ValueError) as ctx:
            do.set_size_header(30)
        self.assertIn("reader_fita", str(ctx.exception).lower())


class TestReadBodyFita(unittest.TestCase):
    """read_body_fita: corpo ausente, formato inválido e cabeçalho incompleto."""

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")
        self.reader = _reader_with_header_fields()
        self.do.register_reader_fita(self.reader)

    def test_read_body_sem_chave_data_retorna_body_apos_valueerror_interno(self):
        """
        read_body() sem 'data' gera ValueError internamente; o método captura
        e retorna self.body_fita (comportamento atual do código-fonte).
        """
        self.reader.read_body.return_value = {}
        self.reader.read_header.return_value = {"Data:": datetime(2024, 1, 1)}
        self.do.header_fita = {"Data:": datetime(2024, 1, 1)}

        result = self.do.read_body_fita()

        self.assertIs(result, self.do.body_fita)
        self.assertNotIn("data", self.do.body_fita or {})

    def test_read_body_horario_fora_padrao_valueerror_e_retorno_sem_converter(self):
        """
        Horário fora de %H:%M:%S gera ValueError em time_to_datetime; read_body_fita
        captura ValueError e retorna self.body_fita (comportamento atual — não relança).
        A coluna de tempo permanece string inválida.
        """
        self.reader.read_body.return_value = {
            "data": [["25-99-99", 0.0]],
            "header_columns": ["Hora", "X"],
        }
        self.reader.read_header.return_value = {"Data:": datetime(2024, 1, 1)}
        self.do.header_fita = {"Data:": datetime(2024, 1, 1)}

        result = self.do.read_body_fita()

        self.assertIs(result, self.do.body_fita)
        self.assertEqual(self.do.body_fita["data"][0][0], "25-99-99")

    def test_read_body_cabecalho_sem_date_key_lanca_excecao(self):
        """Falta da chave configurada em header_fields.date_key no cabeçalho."""
        self.reader.read_body.return_value = {
            "data": [["10:00:00", 1.0]],
            "header_columns": ["Hora", "X"],
        }
        self.reader.read_header.return_value = {}
        self.do.header_fita = {}

        with self.assertRaises(Exception) as ctx:
            self.do.read_body_fita()
        self.assertIn("Erro inesperado ao ler corpo da fita", str(ctx.exception))

    def test_read_body_falha_nao_valueerror_no_reader_propaga_exception(self):
        """Erros que não são ValueError (ex.: falha ao ler corpo) usam except Exception."""
        self.reader.read_body.side_effect = RuntimeError("falha simulada")
        self.do.header_fita = {"Data:": datetime(2024, 1, 1)}

        with self.assertRaises(Exception) as ctx:
            self.do.read_body_fita()
        self.assertIn("Erro inesperado ao ler corpo da fita", str(ctx.exception))
        self.assertIn("falha simulada", str(ctx.exception))


class TestTimeConversion(unittest.TestCase):
    """time_to_datetime e replace_date_in_times com entradas inválidas."""

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")

    def test_time_to_datetime_string_invalida(self):
        """strptime exige HH:MM:SS; string inválida → ValueError."""
        with self.assertRaises(ValueError):
            self.do.time_to_datetime(["não-é-horário"], datetime(2024, 1, 1))

    def test_replace_date_in_times_data_invalida(self):
        """specific_date fora do format_date padrão → ValueError do strptime."""
        t = datetime.strptime("10:00:00", "%H:%M:%S")
        with self.assertRaises(ValueError):
            self.do.replace_date_in_times([t], "31/13/2024")

    def test_replace_date_in_times_backward_pequeno_nao_vira_dia(self):
        """
        Equipamento Baumer Hivac2 emite o timestamp do marcador de fase
        ligeiramente posterior ao snapshot do minuto seguinte (ex.: 16:30:51
        seguido de 16:30:50). Esse backward-jump de 1s NÃO deve disparar
        rollover de dia — todos os pontos permanecem em 2024-01-01.
        """
        times = [
            datetime.strptime(t, "%H:%M:%S")
            for t in ["16:30:51", "16:30:50", "16:31:50", "17:00:00"]
        ]
        out = self.do.replace_date_in_times(times, "2024-01-01")
        for dt in out:
            self.assertEqual(dt.date(), datetime(2024, 1, 1).date())
        self.assertEqual(out[0].strftime("%H:%M:%S"), "16:30:51")
        self.assertEqual(out[1].strftime("%H:%M:%S"), "16:30:50")

    def test_replace_date_in_times_cruzamento_meianoite_vira_dia(self):
        """
        Salto pra trás > 12h é cruzamento real de meia-noite — incrementa
        o dia. 23:55 → 00:05 são pontos consecutivos em dias adjacentes.
        """
        times = [
            datetime.strptime(t, "%H:%M:%S")
            for t in ["23:55:00", "00:05:00", "00:10:00"]
        ]
        out = self.do.replace_date_in_times(times, "2024-01-01")
        self.assertEqual(out[0].date(), datetime(2024, 1, 1).date())
        self.assertEqual(out[1].date(), datetime(2024, 1, 2).date())
        self.assertEqual(out[2].date(), datetime(2024, 1, 2).date())


class TestRolloverMarcadorFita(unittest.TestCase):
    """
    End-to-end: fita AFR13 com padrão de marcador de fase emitindo
    timestamp 1s após o snapshot do minuto seguinte. Antes do fix de
    DAY_ROLLOVER_THRESHOLD, esse padrão fazia o conversor incrementar
    days_elapsed e jogar todos os pontos restantes pro dia seguinte.
    """

    def setUp(self):
        from fita_digital.reader_fita_digital.reader_fita_digital_afr13 import (
            ReaderFitaDigitalAfr13,
        )

        fixture = (
            _ADDON_ROOT
            / "fita_digital"
            / "tests"
            / "fixtures"
            / "20251001_152420_Ciclo_002509_rollover_marcador.txt"
        )
        self.do = DataObjectFitaDigital(directory_path=str(fixture.parent) + "/")
        self.do.register_reader_fita(ReaderFitaDigitalAfr13(str(fixture)))

    def test_todos_os_pontos_permanecem_no_mesmo_dia(self):
        self.do.read_header_fita()
        body = self.do.read_body_fita()

        dia_cabecalho = datetime(2025, 10, 1).date()
        for linha in body["data"]:
            self.assertEqual(
                linha[0].date(),
                dia_cabecalho,
                f"Ponto {linha[0]} não deveria ter virado o dia",
            )

    def test_ordem_temporal_preserva_backward_jump(self):
        """
        Backward jump 16:30:51 → 16:30:50 fica preservado (sem reordenar):
        primeiro o marcador, depois o snapshot 1s antes.
        """
        self.do.read_header_fita()
        body = self.do.read_body_fita()

        horarios = [linha[0].strftime("%H:%M:%S") for linha in body["data"]]
        self.assertIn("15:30:51", horarios)
        self.assertIn("15:30:50", horarios)
        idx_marcador = horarios.index("15:30:51")
        idx_snapshot = horarios.index("15:30:50")
        self.assertLess(idx_marcador, idx_snapshot)


class TestCalcularTempoEntreFases(unittest.TestCase):
    """calcular_tempo_entre_fases: body incompleto e índices inválidos.

    Nota: o método lê ``body_fita['fase']`` antes do ``if 'fase' not in``;
    sem a chave ``fase`` ocorre KeyError, encapsulada em Exception.
    """

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")

    def test_sem_chave_fase_encapsula_keyerror_em_exception(self):
        """Sem 'fase' no body: KeyError antes da validação explícita."""
        self.do.body_fita = {"data": [[datetime(2024, 1, 1, 10, 0, 0), 1.0]]}
        with self.assertRaises(Exception) as ctx:
            self.do.calcular_tempo_entre_fases(0, 1)
        self.assertIn("Erro ao calcular tempo entre fases", str(ctx.exception))

    def test_indices_fora_do_intervalo_lanca_indexerror(self):
        """Índices fora de len(fases) → IndexError explícito."""
        t0 = datetime(2024, 1, 1, 10, 0, 0)
        self.do.body_fita = {
            "data": [[t0, 1.0]],
            "fase": [[t0, "F1"]],
        }
        with self.assertRaises(IndexError):
            self.do.calcular_tempo_entre_fases(0, 2)

    def test_indice_inicial_maior_que_final_lanca_valueerror(self):
        """Regra indice_inicial > indice_final com ambos inteiros válidos."""
        t0 = datetime(2024, 1, 1, 10, 0, 0)
        t1 = t0 + timedelta(minutes=5)
        self.do.body_fita = {
            "data": [[t0, 1.0], [t1, 1.0]],
            "fase": [[t0, "A"], [t1, "B"]],
        }
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_tempo_entre_fases(1, 0)
        self.assertIn("índice inicial", str(ctx.exception).lower())


class TestCalcularTempoTotalCiclo(unittest.TestCase):
    """calcular_tempo_total_ciclo sem dados carregados ou lista vazia."""

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")

    def test_sem_data_no_body_lanca_valueerror(self):
        self.do.body_fita = {}
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_tempo_total_ciclo()
        self.assertIn("não foram carregados", str(ctx.exception).lower())

    def test_data_lista_vazia_lanca_valueerror(self):
        self.do.body_fita = {"data": []}
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_tempo_total_ciclo()
        self.assertIn("medição", str(ctx.exception).lower())


class TestCalcularEstatisticasCiclo(unittest.TestCase):
    """calcular_estatisticas_ciclo: fases obrigatórias e body carregado."""

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")

    def test_fases_none_lanca_valueerror(self):
        self.do.body_fita = {"data": [[datetime.now(), 1.0]], "fase": []}
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_estatisticas_ciclo(fases=None)
        self.assertIn("fases", str(ctx.exception).lower())

    def test_fases_lista_vazia_lanca_valueerror(self):
        self.do.body_fita = {"data": [[datetime.now(), 1.0]], "fase": []}
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_estatisticas_ciclo(fases=[])
        self.assertIn("fases", str(ctx.exception).lower())

    def test_body_sem_dados_lanca_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_estatisticas_ciclo(fases=["X"])
        self.assertIn("não foram carregados", str(ctx.exception).lower())


class TestCalcularEstatisticasCicloEntreFases(unittest.TestCase):
    """calcular_estatisticas_ciclo_entre_fases: fases ausentes no body."""

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")

    def test_com_fases_mas_sem_chave_fase_no_body_lanca_valueerror(self):
        t = datetime(2024, 1, 1, 10, 0, 0)
        self.do.body_fita = {
            "data": [[t, 1.0, 50.0]],
            "header_columns": ["Hora", "PCI(Bar)", "TCI(Celsius)"],
        }
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_estatisticas_ciclo_entre_fases("A", "B")
        self.assertIn("fases não disponíveis", str(ctx.exception).lower())

    def test_fases_nao_encontradas_no_registro_lanca_valueerror(self):
        t0 = datetime(2024, 1, 1, 10, 0, 0)
        t1 = datetime(2024, 1, 1, 11, 0, 0)
        self.do.body_fita = {
            "data": [[t0, 1.0, 50.0], [t1, 1.1, 51.0]],
            "fase": [[t0, "OUTRA"]],
            "header_columns": ["Hora", "PCI(Bar)", "TCI(Celsius)"],
        }
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_estatisticas_ciclo_entre_fases("AUSENTE1", "AUSENTE2")
        self.assertIn("não encontradas", str(ctx.exception).lower())


class TestCalcularMortalidadeIntervalos(unittest.TestCase):
    """calcular_mortalidade_intervalos: dados e fases obrigatórios para o recorte."""

    def setUp(self):
        self.do = DataObjectFitaDigital(directory_path="/tmp")

    def test_sem_body_ou_sem_data_lanca_valueerror(self):
        self.do.body_fita = {}
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_mortalidade_intervalos(N0=1e6)
        self.assertIn("mortalidade", str(ctx.exception).lower())

    def test_fases_inexistentes_lanca_valueerror(self):
        t = datetime(2024, 1, 1, 10, 0, 0)
        self.do.body_fita = {
            "data": [[t, 0.0, 50.0, 0, 0.001]],
            "fase": [[t, "SÓ_UM_MARCADOR"]],
        }
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_mortalidade_intervalos(
                N0=1e6,
                fase_inicial="ESTERILIZACAO",
                fase_final="LAVAGEM",
            )
        self.assertIn("mortalidade", str(ctx.exception).lower())

    def test_janela_sem_pontos_lanca_valueerror(self):
        """Timestamps de fase definem intervalo vazio em relação a 'data'."""
        t_phase = datetime(2024, 1, 1, 12, 0, 0)
        t_data = datetime(2024, 1, 1, 10, 0, 0)
        self.do.body_fita = {
            "data": [[t_data, 0.0, 50.0, 0, 0.001]],
            "fase": [
                [t_phase, "ESTERILIZACAO"],
                [t_phase + timedelta(hours=1), "LAVAGEM"],
            ],
        }
        with self.assertRaises(ValueError) as ctx:
            self.do.calcular_mortalidade_intervalos(N0=1e6)
        self.assertIn("mortalidade", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
