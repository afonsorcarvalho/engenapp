from .common import CalibrationCase


class TestCalibrationPrecision(CalibrationCase):

    def test_precisao_decimal_configurada(self):
        precisao = self.env.ref('engc_os.decimal_calibration')
        self.assertEqual(precisao.name, 'Calibration')
        self.assertGreaterEqual(precisao.digits, 6)

    def test_leitura_com_tres_casas_e_preservada(self):
        """O caso da imagem do relatório: 60,053 não pode virar 60,05."""
        m = self.make_measurement()
        line = self.make_line(m, 60.0, 60.053, 60.055, 60.054)
        self.assertAlmostEqual(line.measurement_quantity_value_1, 60.053, places=6)
        self.assertAlmostEqual(line.measurement_quantity_value_2, 60.055, places=6)

    def test_valor_de_mil_segundos_com_tres_casas(self):
        """Ponto de 1200,043 s da imagem — 7 algarismos significativos."""
        m = self.make_measurement()
        line = self.make_line(m, 1200.0, 1200.043, 1200.046, 1200.044)
        self.assertAlmostEqual(line.measurement_quantity_value_mean, 1200.044333, places=5)

    def test_incerteza_do_padrao_com_tres_casas(self):
        """0,035 precisa sobreviver ao round-trip no banco."""
        self.assertAlmostEqual(self.unc_line.uncertainty, 0.035, places=6)
        self.assertAlmostEqual(self.unc_line.resolution, 0.01, places=6)

    def test_erro_pequeno_nao_vira_zero(self):
        """Erros da imagem são da ordem de -0,002 s."""
        m = self.make_measurement()
        line = self.make_line(m, 60.055, 60.053, 60.053, 60.053)
        self.assertAlmostEqual(line.erro_value, -0.002, places=6)
