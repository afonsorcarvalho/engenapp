from datetime import date

from odoo.exceptions import ValidationError

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


class TestUnitDisplayDecimals(CalibrationCase):

    def test_default_de_tres_casas(self):
        unidade = self.env['engc.calibration.measurement.unit'].create({
            'name': 'Pressão', 'simbolo': 'bar',
        })
        self.assertEqual(unidade.display_decimals, 3)

    def test_aceita_zero_casas(self):
        """Review Focus 4: zero é valor legítimo (ex.: contagem de ciclos)."""
        unidade = self.env['engc.calibration.measurement.unit'].create({
            'name': 'Ciclos', 'simbolo': 'un', 'display_decimals': 0,
        })
        self.assertEqual(unidade.display_decimals, 0)

    def test_rejeita_valor_negativo(self):
        with self.assertRaises(ValidationError):
            self.env['engc.calibration.measurement.unit'].create({
                'name': 'Inválida', 'simbolo': 'x', 'display_decimals': -1,
            })

    def test_rejeita_acima_do_armazenado(self):
        with self.assertRaises(ValidationError):
            self.env['engc.calibration.measurement.unit'].create({
                'name': 'Inválida', 'simbolo': 'x', 'display_decimals': 7,
            })

    def test_unidade_tempo_do_fixture_tem_tres_casas(self):
        self.assertEqual(self.unit_tempo.display_decimals, 3)


class TestCertificateDecimalsRendering(CalibrationCase):
    """Guarda de regressão do bug real desta task.

    `TestUnitDisplayDecimals` cobre só o campo Python `display_decimals` —
    nenhum teste ali renderiza o certificado. Sem esta classe, reverter
    `calibration_certificate_template.xml` para o hardcode antigo
    (`t-options='{"widget": "float", "precision": 2}'`) deixaria os demais
    48 testes de engc_os e os 919 do baseline verdes, e o bug que a Fase 1
    inteira existe para corrigir (60,053 s virando 60,05 s no PDF) voltaria
    sem ninguém perceber.

    O report action `engc_os.report_engc_os_calibration_certificate` está
    ligado ao modelo `engc.calibration` (`reports/engc_os_reports.xml`) —
    os docids passados a `_render_qweb_html` são ids de `engc.calibration`,
    não de `engc.os` nem de medição.
    """

    def _build_calibration_with_line(self, true_value, r1, r2, r3):
        vals = self.make_calibration_vals(issue_date=date.today())
        calibration = self.env['engc.calibration'].create(vals)
        # make_measurement() (common.py) não define calibration_id no seu
        # dict default; passar aqui via kw acrescenta o campo sem tocar no
        # helper compartilhado.
        measurement = self.make_measurement(calibration_id=calibration.id)
        self.make_line(measurement, true_value, r1, r2, r3)
        return calibration

    def _render(self, calibration):
        return self.env['ir.actions.report']._render_qweb_html(
            'engc_os.report_engc_os_calibration_certificate', [calibration.id]
        )[0].decode()

    def test_valor_medido_imprime_tres_casas_nao_truncadas(self):
        """Caso real: mean(60.053, 60.055, 60.054) = 60.054. Tem que
        aparecer 60,054 no certificado — não pode voltar a truncar para
        60,05 (o bug original desta task)."""
        calibration = self._build_calibration_with_line(60.0, 60.053, 60.055, 60.054)
        html = self._render(calibration)
        # Fronteira exata via tag de fechamento: "60,05" é PREFIXO de
        # "60,054", então um assertNotIn('60,05') ingênuo sempre casaria
        # dentro de "60,054" e nunca detectaria o revert para precision=2.
        # Ancorar em "<span>...</span>" completo resolve isso.
        self.assertIn('<span>60,054</span>', html)
        self.assertNotIn('<span>60,05</span>', html)

    def test_display_decimals_zero_imprime_sem_casas(self):
        self.unit_tempo.display_decimals = 0
        calibration = self._build_calibration_with_line(60.0, 60.053, 60.055, 60.054)
        html = self._render(calibration)
        self.assertIn('<span>60</span>', html)
        self.assertNotIn('<span>60,00</span>', html)
        self.assertNotIn('<span>60,054</span>', html)

    def test_unidade_vazia_nao_e_confundida_com_zero_casas(self):
        """FIX 3 (revisão final): `l.unit_of_measurement.display_decimals or 0`
        não distingue "sem unidade" (recordset vazio, display_decimals lê como
        False) de "0 casas configurado de propósito" (caso do teste acima) —
        os dois caem em `casas = 0`. Uma linha salva sem unidade não pode
        truncar 60,054 para 60 como se fosse a configuração deliberada."""
        vals = self.make_calibration_vals(issue_date=date.today())
        calibration = self.env['engc.calibration'].create(vals)
        measurement = self.make_measurement(
            calibration_id=calibration.id, unit_of_measurement=False)
        self.make_line(measurement, 60.0, 60.053, 60.055, 60.054)
        html = self._render(calibration)
        self.assertIn('<span>60,054</span>', html)
        self.assertNotIn('<span>60</span>', html)
