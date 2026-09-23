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
