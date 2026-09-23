from datetime import date

from dateutil.relativedelta import relativedelta

from .common import CalibrationCase


class TestCertificateValidity(CalibrationCase):

    def test_certificado_vencido_nao_e_valido(self):
        self.certificate.validate_calibration = date.today() - relativedelta(days=1)
        self.assertFalse(self.certificate.is_valid)

    def test_certificado_no_prazo_e_valido(self):
        self.assertTrue(self.certificate.is_valid)

    def test_certificado_vence_hoje_ainda_e_valido(self):
        self.certificate.validate_calibration = date.today()
        self.assertTrue(self.certificate.is_valid)

    def test_certificado_sem_data_de_validade_nao_estoura(self):
        """Review Focus 2: validate_calibration vazio comparava False com date."""
        cert = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'SEM-DATA',
        })
        self.assertFalse(cert.is_valid)

    def test_is_valid_em_lote(self):
        """O compute precisa atribuir todos os registros do recordset."""
        cert2 = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'R9999/2026',
            'validate_calibration': date.today() - relativedelta(days=1),
        })
        lote = self.certificate | cert2
        self.assertEqual(lote.mapped('is_valid'), [True, False])

    def test_verify_is_valid_sem_data_nao_estoura(self):
        """verify_is_valid() é API pública (base do get_valid_certificates da
        Task 3); precisa ser segura contra data vazia tanto quanto o compute."""
        cert = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'SEM-DATA-2',
        })
        self.assertFalse(cert.verify_is_valid())


class TestCertificateSelection(CalibrationCase):

    def _novo_certificado(self, numero, validade_anos=1, calibrado_em=None):
        return self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': numero,
            'date_calibration': calibrado_em or date.today(),
            'validate_calibration': date.today() + relativedelta(years=validade_anos),
        })

    def test_um_certificado_valido_devolve_ele(self):
        self.assertEqual(self.instrument.get_certificate_valid(), self.certificate)

    def test_varios_validos_devolve_singleton(self):
        """O caso QPT-014 real: 3 certificados válidos quebravam o PDF."""
        self._novo_certificado('R1236/2026')
        self._novo_certificado('R1236/2026 - Inglês')
        escolhido = self.instrument.get_certificate_valid()
        self.assertEqual(len(escolhido), 1)

    def test_escolhe_o_de_calibracao_mais_recente(self):
        antigo = self.certificate
        antigo.date_calibration = date.today() - relativedelta(years=2)
        novo = self._novo_certificado('R1236/2026', calibrado_em=date.today())
        self.assertEqual(self.instrument.get_certificate_valid(), novo)

    def test_certificado_substituido_e_ignorado(self):
        dup = self._novo_certificado('R0712/2026 - Inglês')
        dup.superseded_by_id = self.certificate.id
        self.assertEqual(self.instrument.get_certificate_valid(), self.certificate)
        self.assertNotIn(dup, self.instrument.get_valid_certificates())

    def test_search_certificates_valid_ignora_substituido(self):
        """_search_certificates_valid() é o segundo caminho de validade (usado
        no onchange da medição, via _search_statistics) — não checava
        superseded_by_id, reabrindo a mesma classe de erro do P0 (Expected
        singleton) quando a duplicata carrega uma uncertainty_line na mesma
        unidade do certificado mantido."""
        dup = self._novo_certificado('R1236/2026 - Inglês')
        self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': dup.id,
            'unit_of_measurement': self.unit_tempo.id,
            'uncertainty': 0.999,
            'coverage_factor': 2.0,
            'erro_value': 0.999,
            'resolution': 0.999,
            'veff': 2.0,
        })
        dup.superseded_by_id = self.certificate.id

        measurement = self.make_measurement()

        self.assertEqual(measurement.resolution_instrument, 0.01)

    def test_sem_certificado_valido_devolve_vazio_sem_estourar(self):
        """Review Focus 1: instrumento sem certificado válido."""
        self.certificate.validate_calibration = date.today() - relativedelta(days=1)
        self.assertEqual(len(self.instrument.get_certificate_valid()), 0)

    def test_domain_unidade_sem_padrao_escolhido_nao_estoura(self):
        """get_certificate_valid() agora faz ensure_one() no instrumento; uma
        medição sem instrument_id ainda escolhido não pode quebrar o
        _compute_unit_of_measurement_domain (mesma classe de erro do P0)."""
        measurement = self.env['engc.calibration.measurement'].new({'title': 'X'})
        self.assertEqual(measurement.unit_of_measurement_domain, '[["id", "in", []]]')

    def test_arquivos_de_idioma_no_mesmo_certificado(self):
        en = self.env['res.lang'].search([('code', '=', 'en_US')], limit=1)
        arquivo = self.env['engc.calibration.instruments.certificates.file'].create({
            'certificate_id': self.certificate.id,
            'name': 'R0712/2026 - Inglês',
            'lang_id': en.id if en else False,
        })
        self.assertIn(arquivo, self.certificate.certificate_file_ids)
