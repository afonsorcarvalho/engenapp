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

    def test_campos_dimensionais_expoem_digits_calibration(self):
        """Guarda real da Task 5: os outros testes desta classe passam mesmo com
        `digits='Calibration'` removido de todos os campos, porque o
        armazenamento (double precision) nunca esteve quebrado — o bug só
        aparecia no widget web, que lê fields_get()['digits']."""
        Lines = self.env['engc.calibration.measurement.lines']
        fg = Lines.fields_get([
            'true_quantity_value',
            'measurement_quantity_value_1',
            'measurement_quantity_value_2',
            'measurement_quantity_value_3',
            'measurement_quantity_value_mean',
            'erro_value',
            'uncertainty',
            'resolutino_instrument',
            'coverage_factor',
            'veff',
        ])
        self.assertEqual(tuple(fg['true_quantity_value']['digits']), (16, 6))
        self.assertEqual(tuple(fg['measurement_quantity_value_1']['digits']), (16, 6))
        self.assertEqual(tuple(fg['measurement_quantity_value_2']['digits']), (16, 6))
        self.assertEqual(tuple(fg['measurement_quantity_value_3']['digits']), (16, 6))
        self.assertEqual(tuple(fg['measurement_quantity_value_mean']['digits']), (16, 6))
        self.assertEqual(tuple(fg['erro_value']['digits']), (16, 6))
        self.assertEqual(tuple(fg['uncertainty']['digits']), (16, 6))
        self.assertEqual(tuple(fg['resolutino_instrument']['digits']), (16, 6))
        self.assertFalse(fg['coverage_factor'].get('digits'))  # adimensional, tem de continuar sem digits
        self.assertFalse(fg['veff'].get('digits'))  # adimensional, tem de continuar sem digits

        Unc = self.env['engc.calibration.instruments.uncertainty.lines']
        fg_u = Unc.fields_get(['erro_value', 'uncertainty', 'resolution', 'coverage_factor', 'veff'])
        self.assertEqual(tuple(fg_u['erro_value']['digits']), (16, 6))
        self.assertEqual(tuple(fg_u['uncertainty']['digits']), (16, 6))
        self.assertEqual(tuple(fg_u['resolution']['digits']), (16, 6))
        self.assertFalse(fg_u['coverage_factor'].get('digits'))
        self.assertFalse(fg_u['veff'].get('digits'))

        Meas = self.env['engc.calibration.measurement']
        fg_m = Meas.fields_get([
            'uncertainty_instrument',
            'erro_value_instrument',
            'resolution_instrument',
            'coverage_factor_instrument',
            'veff_instrument',
        ])
        self.assertEqual(tuple(fg_m['uncertainty_instrument']['digits']), (16, 6))
        self.assertEqual(tuple(fg_m['erro_value_instrument']['digits']), (16, 6))
        self.assertEqual(tuple(fg_m['resolution_instrument']['digits']), (16, 6))
        self.assertFalse(fg_m['coverage_factor_instrument'].get('digits'))
        self.assertFalse(fg_m['veff_instrument'].get('digits'))
