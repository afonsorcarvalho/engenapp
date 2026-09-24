from odoo.exceptions import ValidationError

from .common import CalibrationCase


class TestUncertaintyLineConstraints(CalibrationCase):
    """A fixture já cria self.unc_line: uma linha em self.unit_tempo,
    com uncertainty=0.035, coverage_factor=2.0, erro_value=0.01,
    resolution=0.01, veff=2.0. Ela nasce genérica (is_generic=True)."""

    def _ponto(self, valor, **kw):
        vals = {
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False,
            'nominal_value': valor,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'erro_value': -0.002,
            'resolution': 0.01,
        }
        vals.update(kw)
        return self.env['engc.calibration.instruments.uncertainty.lines'].create(vals)

    def test_linha_nasce_generica(self):
        self.assertTrue(self.unc_line.is_generic)
        self.assertTrue(self.unc_line.veff_infinito)

    def test_ponto_em_zero_e_valido(self):
        """O certificado do cronômetro tem ponto em 0,000 s. Float no Odoo
        nunca grava NULL, então is_generic é o que desambigua."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        ponto = self._ponto(60.0)
        self.assertFalse(self.unc_line.is_generic)
        self.assertEqual(self.unc_line.nominal_value, 0.0)
        self.assertEqual(ponto.nominal_value, 60.0)

    def test_nao_mistura_generica_com_ponto(self):
        with self.assertRaises(ValidationError):
            self._ponto(60.0)

    def test_nao_repete_valor_nominal(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        with self.assertRaises(ValidationError):
            self._ponto(60.0)

    def test_nao_aceita_duas_genericas(self):
        with self.assertRaises(ValidationError):
            self._ponto(0.0, is_generic=True)

    def test_unidades_diferentes_nao_conflitam(self):
        outra = self.env['engc.calibration.measurement.unit'].create(
            {'name': 'Celsius', 'simbolo': 'C'})
        linha = self._ponto(0.0, is_generic=True, unit_of_measurement=outra.id)
        self.assertTrue(linha.is_generic)
        self.assertTrue(self.unc_line.is_generic)

    def test_seis_pontos_do_cronometro(self):
        """O caso que motivou a fase inteira: cadastrar a tabela do
        certificado sem que nada reclame."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        for valor in (60.0, 120.0, 480.0, 600.0, 1200.0):
            self._ponto(valor)
        linhas = self.certificate.uncertainty_lines
        self.assertEqual(len(linhas), 6)
        self.assertEqual(
            sorted(linhas.mapped('nominal_value')),
            [0.0, 60.0, 120.0, 480.0, 600.0, 1200.0])
