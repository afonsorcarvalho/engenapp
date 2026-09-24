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


class TestSelectUncertaintyAt(CalibrationCase):

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

    def _virar_multiponto(self):
        """Converte a linha genérica da fixture em 0 s e acrescenta 60 e 120."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        self.unc_line.erro_value = 0.000
        p60 = self._ponto(60.0, erro_value=-0.002, uncertainty=0.035)
        p120 = self._ponto(120.0, erro_value=-0.006, uncertainty=0.045)
        return p60, p120

    def test_linha_generica_serve_qualquer_valor(self):
        """100% do acervo atual cai aqui — não pode regredir."""
        for valor in (0.0, 60.0, 99999.0):
            r = self.certificate._select_uncertainty_at(self.unit_tempo, valor)
            self.assertEqual(r['status'], 'ok')
            self.assertAlmostEqual(r['uncertainty'], 0.035, places=6)
            self.assertEqual(r['source_line_id'], self.unc_line.id)

    def test_ponto_exato(self):
        p60, _ = self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 60.0)
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(r['source_line_id'], p60.id)
        self.assertAlmostEqual(r['erro_value'], -0.002, places=6)

    def test_entre_dois_pontos_interpola_erro(self):
        """90 s fica no meio de 60 e 120: erro = -0,002 + 0,5*(-0,006+0,002)"""
        self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertEqual(r['status'], 'ok')
        self.assertAlmostEqual(r['erro_value'], -0.004, places=6)

    def test_entre_dois_pontos_incerteza_pelo_pior(self):
        """U vem do ponto de maior u=U/k, não interpolada."""
        _, p120 = self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertAlmostEqual(r['uncertainty'], 0.045, places=6)
        self.assertEqual(r['source_line_id'], p120.id)

    def test_pior_ponto_usa_u_e_nao_U_nu(self):
        """U=0,050 com k=2,5 dá u=0,020, igual a U=0,040 com k=2,0.
        Escolher pelo U nu pegaria o errado."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.unc_line.uncertainty = 0.040
        self.unc_line.coverage_factor = 2.0
        self._ponto(120.0, uncertainty=0.050, coverage_factor=2.5)
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        # empate em u: resolve pelo menor id, que é a linha da fixture
        self.assertEqual(r['source_line_id'], self.unc_line.id)
        self.assertAlmostEqual(r['coverage_factor'], 2.0, places=6)

    def test_fora_da_faixa_devolve_status_sem_levantar(self):
        self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 2000.0)
        self.assertEqual(r['status'], 'fora_faixa')
        self.assertIn('2000', r['message'])
        self.assertEqual(r['uncertainty'], 0.0)

    def test_abaixo_da_faixa_tambem(self):
        self._virar_multiponto()
        r = self.certificate._select_uncertainty_at(self.unit_tempo, -5.0)
        self.assertEqual(r['status'], 'fora_faixa')

    def test_unidade_ausente_devolve_status_sem_levantar(self):
        outra = self.env['engc.calibration.measurement.unit'].create(
            {'name': 'Bar', 'simbolo': 'bar'})
        r = self.certificate._select_uncertainty_at(outra, 1.0)
        self.assertEqual(r['status'], 'sem_unidade')

    def test_k_zero_nao_estoura(self):
        """Review Focus 1: k=0 cadastrado por engano dividiria por zero
        dentro de um compute store=True."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self._ponto(120.0, coverage_factor=0.0)
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertEqual(r['status'], 'ok')
