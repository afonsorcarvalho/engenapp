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

    def test_recordset_vazio_devolve_status(self):
        """A garantia de "nunca levanta" tem de valer dentro do método, não
        depender de cada chamador guardar o call site."""
        vazio = self.env['engc.calibration.instruments.certificates']
        r = vazio._select_uncertainty_at(self.unit_tempo, 60.0)
        self.assertEqual(r['status'], 'sem_certificado')
        self.assertEqual(r['uncertainty'], 0.0)

    def test_bracketing_com_varios_pontos(self):
        """Com 4 pontos, medir entre o 2º e o 3º tem de escolher esse par —
        não o primeiro nem o último."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 0.0
        self.unc_line.erro_value = 0.0
        self._ponto(60.0, erro_value=-0.002, uncertainty=0.035)
        self._ponto(120.0, erro_value=-0.006, uncertainty=0.045)
        self._ponto(600.0, erro_value=-0.010, uncertainty=0.055)
        r = self.certificate._select_uncertainty_at(self.unit_tempo, 90.0)
        self.assertAlmostEqual(r['erro_value'], -0.004, places=6)
        self.assertAlmostEqual(r['uncertainty'], 0.045, places=6)


class TestStandardContributionOnLine(CalibrationCase):

    def _calibracao_com_medicao(self):
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id,
            'title': 'Tempo',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        return cal, medicao

    def test_valores_chegam_sem_onchange(self):
        """Review Focus 3: criação por RPC não dispara onchange. Antes desta
        fase os valores do padrão ficavam 0,0 em silêncio."""
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 60.0, 60.053, 60.055, 60.054)
        self.assertEqual(linha.standard_status, 'ok')
        self.assertAlmostEqual(linha.standard_uncertainty, 0.035, places=6)
        self.assertAlmostEqual(linha.standard_resolution, 0.01, places=6)
        self.assertEqual(linha.standard_line_id, self.unc_line)

    def test_cada_linha_pega_o_proprio_ponto(self):
        """O ponto desta fase: duas linhas, dois pontos, dois conjuntos."""
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.unc_line.erro_value = -0.002
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False,
            'nominal_value': 1200.0,
            'erro_value': -0.009,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'resolution': 0.01,
        })
        _, medicao = self._calibracao_com_medicao()
        curta = self.make_line(medicao, 60.0, 60.053, 60.055, 60.054)
        longa = self.make_line(medicao, 1200.0, 1200.043, 1200.046, 1200.044)
        self.assertAlmostEqual(curta.standard_erro, -0.002, places=6)
        self.assertAlmostEqual(longa.standard_erro, -0.009, places=6)

    def test_recalcula_ao_mudar_o_valor_real(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False, 'nominal_value': 120.0,
            'erro_value': -0.006, 'uncertainty': 0.045,
            'coverage_factor': 2.0, 'resolution': 0.01,
        })
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        self.assertAlmostEqual(linha.standard_uncertainty, 0.035, places=6)
        linha.true_quantity_value = 120.0
        self.assertAlmostEqual(linha.standard_uncertainty, 0.045, places=6)

    def test_sem_instrumento_nao_estoura(self):
        """get_certificate_valid() faz ensure_one(); com instrument_id vazio
        isso levantaria dentro de um compute store=True."""
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Sem padrão',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        medicao.instrument_id = False
        self.assertEqual(linha.standard_status, 'sem_certificado')
        self.assertEqual(linha.standard_uncertainty, 0.0)

    def test_certificado_vencido_nao_estoura(self):
        """O teste que protege todo -u futuro: o compute tem de ser total.

        O certificado vence ANTES de a linha existir, de propósito. Os campos
        standard_* são compute store=True e `validate_calibration` NÃO está no
        @api.depends — nem deve estar: pela decisão D5 da spec, editar o
        certificado amanhã não pode mudar retroativamente uma calibração já
        emitida. Vencer o certificado depois de criar a linha só deixaria o
        valor gravado intacto, e o teste não provaria nada.
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta
        self.certificate.validate_calibration = date.today() - relativedelta(days=1)
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        self.assertEqual(linha.standard_status, 'sem_certificado')
        self.assertEqual(linha.standard_uncertainty, 0.0)

    def test_unidade_ausente_no_certificado(self):
        """Review Focus 2."""
        outra = self.env['engc.calibration.measurement.unit'].create(
            {'name': 'Bar', 'simbolo': 'bar'})
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Pressão',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': outra.id,
        })
        linha = self.make_line(medicao, 1.0, 1.0, 1.0, 1.0)
        self.assertEqual(linha.standard_status, 'sem_unidade')

    def test_fora_da_faixa_marca_status(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'is_generic': False, 'nominal_value': 120.0,
            'erro_value': -0.006, 'uncertainty': 0.045,
            'coverage_factor': 2.0, 'resolution': 0.01,
        })
        _, medicao = self._calibracao_com_medicao()
        linha = self.make_line(medicao, 2000.0, 2000.0, 2000.0, 2000.0)
        self.assertEqual(linha.standard_status, 'fora_faixa')
        self.assertIn('2000', linha.standard_message)


class TestBlockingOnDone(CalibrationCase):

    def _cal_com_ponto_unico(self):
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = 60.0
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Tempo',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        return cal, medicao

    def test_done_recusa_linha_fora_da_faixa(self):
        cal, medicao = self._cal_com_ponto_unico()
        self.make_line(medicao, 2000.0, 2000.0, 2000.0, 2000.0)
        with self.assertRaises(ValidationError) as ctx:
            cal.action_done()
        self.assertIn('2000', str(ctx.exception))

    def test_done_aceita_tudo_resolvido(self):
        cal, medicao = self._cal_com_ponto_unico()
        self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        cal.action_done()
        self.assertEqual(cal.state, 'done')

    def test_done_sem_nenhuma_linha_nao_estoura(self):
        """Review Focus 5: a validação percorre linhas; com zero linhas não
        pode estourar nem aprovar em falso."""
        cal, _ = self._cal_com_ponto_unico()
        cal.action_done()
        self.assertEqual(cal.state, 'done')

    def test_onchange_avisa_sem_bloquear(self):
        cal, medicao = self._cal_com_ponto_unico()
        linha = self.make_line(medicao, 60.0, 60.0, 60.0, 60.0)
        linha.true_quantity_value = 2000.0
        aviso = linha.onchange_true_quantity_value()
        self.assertIn('warning', aviso)
        self.assertIn('2000', aviso['warning']['message'])


class TestAceitacaoCronometro(CalibrationCase):
    """O caso que motivou a fase: o certificado R0712/2026 do QPS-001,
    com os pontos e erros da tabela do PDF de exemplo."""

    PONTOS = [
        (0.0, 0.000), (60.0, -0.002), (120.0, -0.003),
        (480.0, -0.003), (600.0, -0.002), (1200.0, -0.002),
    ]

    def setUp(self):
        super().setUp()
        self.unc_line.is_generic = False
        self.unc_line.nominal_value = self.PONTOS[0][0]
        self.unc_line.erro_value = self.PONTOS[0][1]
        Linha = self.env['engc.calibration.instruments.uncertainty.lines']
        for nominal, erro in self.PONTOS[1:]:
            Linha.create({
                'certificate': self.certificate.id,
                'unit_of_measurement': self.unit_tempo.id,
                'is_generic': False,
                'nominal_value': nominal,
                'erro_value': erro,
                'uncertainty': 0.035,
                'coverage_factor': 2.0,
                'resolution': 0.01,
                'veff_infinito': True,
            })
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        self.medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id, 'title': 'Tempo',
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        self.cal = cal

    def test_seis_pontos_cadastrados(self):
        self.assertEqual(len(self.certificate.uncertainty_lines), 6)

    def test_sobre_um_ponto_usa_o_erro_dele(self):
        linha = self.make_line(self.medicao, 1200.0, 1200.043, 1200.046, 1200.044)
        self.assertEqual(linha.standard_status, 'ok')
        self.assertAlmostEqual(linha.standard_erro, -0.002, places=6)
        self.assertAlmostEqual(linha.standard_uncertainty, 0.035, places=6)

    def test_entre_dois_pontos_interpola(self):
        """300 s fica entre 120 (-0,003) e 480 (-0,003): erro constante."""
        linha = self.make_line(self.medicao, 300.0, 300.0, 300.0, 300.0)
        self.assertEqual(linha.standard_status, 'ok')
        self.assertAlmostEqual(linha.standard_erro, -0.003, places=6)

    def test_interpolacao_com_erros_diferentes(self):
        """90 s entre 60 (-0,002) e 120 (-0,003): meio do caminho."""
        linha = self.make_line(self.medicao, 90.0, 90.0, 90.0, 90.0)
        self.assertAlmostEqual(linha.standard_erro, -0.0025, places=6)

    def test_fora_da_faixa_bloqueia_a_conclusao(self):
        self.make_line(self.medicao, 2000.0, 2000.0, 2000.0, 2000.0)
        with self.assertRaises(ValidationError):
            self.cal.action_done()

    def test_pontos_diferentes_na_mesma_medicao(self):
        """A prova de que o escalar por bloco virou valor por linha."""
        curta = self.make_line(self.medicao, 60.0, 60.053, 60.055, 60.054)
        longa = self.make_line(self.medicao, 120.0, 120.043, 120.046, 120.044)
        self.assertAlmostEqual(curta.standard_erro, -0.002, places=6)
        self.assertAlmostEqual(longa.standard_erro, -0.003, places=6)
        self.assertNotEqual(curta.standard_line_id, longa.standard_line_id)
