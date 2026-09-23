from math import sqrt

from .common import CalibrationCase


class TestCalibrationCharacterization(CalibrationCase):
    """Fixa a matemática ATUAL de _compute_statistics.

    ATENÇÃO: várias destas asserções fixam fórmulas que o relatório
    2026-09-23-analise-calibracao-incerteza-precisao.md aponta como
    incorretas (seção 5). É intencional. Elas são a rede de segurança das
    Fases 0 e 1, que não podem mudar número nenhum. Quem executar a Fase 3
    deve alterar cada asserção DE PROPÓSITO, registrando o delta na mensagem
    de commit.
    """

    def test_padrao_preenchido_pelo_onchange(self):
        m = self.make_measurement()
        self.assertAlmostEqual(m.uncertainty_instrument, 0.035, places=6)
        self.assertAlmostEqual(m.coverage_factor_instrument, 2.0, places=6)
        self.assertAlmostEqual(m.erro_value_instrument, 0.01, places=6)
        self.assertAlmostEqual(m.resolution_instrument, 0.01, places=6)

    def test_media_e_erro(self):
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertAlmostEqual(line.measurement_quantity_value_mean, 60.054, places=6)
        self.assertAlmostEqual(line.erro_value, 0.054, places=6)

    def test_incerteza_expandida_valor_atual(self):
        """Valor conferido à mão a partir da fórmula vigente.

        uc = sqrt((s/2)^2 + (0.035/2)^2 + (0.01/sqrt(3))^2 + (0.01/sqrt(12))^2)
        U  = k * uc, com k = 2,0
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertAlmostEqual(line.uncertainty, 0.037318, places=5)

    def test_veff_atual_usa_constante_3(self):
        """Fórmula vigente: 3*(uc/(s/2))**4 — não é Welch-Satterthwaite."""
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertGreater(line.veff, 100.0)

    def test_tipo_a_usa_divisor_2_e_nao_raiz_de_n(self):
        """Pino explícito do divisor errado, para a Fase 3 ter o que virar.

        Se o termo Tipo A usasse s/sqrt(3), U seria maior. Este teste falha
        no instante em que alguém corrigir a fórmula — que é exatamente o
        sinal desejado.
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        s = 0.001
        esperado_atual = 2.0 * sqrt(
            (s / 2) ** 2
            + (0.035 / 2.0) ** 2
            + (0.01 / sqrt(3)) ** 2
            + (0.01 / sqrt(12)) ** 2
        )
        # places=5 de propósito, NÃO 6: a Task 5 passa a gravar com
        # digits='Calibration' (6 casas), e o valor gravado (0.037318) fica a
        # 4,49e-7 do calculado — dentro da tolerância de places=6 por apenas
        # 5e-8. Margem de 10% é armadilha de teste intermitente.
        self.assertAlmostEqual(line.uncertainty, esperado_atual, places=5)

    def test_leitura_faltando_entra_como_zero(self):
        """Documenta o defeito da seção 5.6: só duas leituras preenchidas
        envenenam a média. Não é comportamento desejado — é o atual.

        mean([60.053, 60.055, 0.0]) = 40.036. O 40 não é erro de digitação:
        é a terceira leitura vazia entrando como zero.

        NA FASE 3 este teste deve virar: com duas leituras preenchidas a
        média tem que ser 60.054 (média das duas de verdade), e o n usado
        no termo Tipo A passa a ser 2.
        """
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 0.0)
        self.assertAlmostEqual(line.measurement_quantity_value_mean, 40.036, places=3)
