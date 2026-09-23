from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError

from .common import CalibrationCase


class TestCalibrationBugs(CalibrationCase):

    def test_create_confirma_o_registro_criado(self):
        """create() chamava action_confirmed() em self (recordset vazio)."""
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        self.assertEqual(cal.state, 'confirmed')
        self.assertNotEqual(cal.name, 'New')

    def test_create_multi(self):
        cals = self.env['engc.calibration'].create([
            self.make_calibration_vals(), self.make_calibration_vals(),
        ])
        self.assertEqual(len(cals), 2)
        self.assertEqual(len(set(cals.mapped('name'))), 2)

    def test_proxima_calibracao_vazia_nao_estoura(self):
        """Review Focus 3: comparava date > False."""
        cal = self.env['engc.calibration'].create(
            self.make_calibration_vals(date_next_calibration=False))
        self.assertFalse(cal.date_next_calibration)

    def test_proxima_calibracao_anterior_e_rejeitada(self):
        with self.assertRaises(ValidationError):
            self.env['engc.calibration'].create(self.make_calibration_vals(
                date_calibration=date.today(),
                date_next_calibration=date.today() - relativedelta(days=1),
            ))

    def test_dominio_do_padrao_restringe_aos_da_calibracao(self):
        """_compute_instrument_id_domain condicionava ao próprio valor."""
        cal = self.env['engc.calibration'].create(self.make_calibration_vals())
        medicao = self.env['engc.calibration.measurement'].create({
            'calibration_id': cal.id,
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        })
        self.assertIn(str(self.instrument.id), medicao.instrument_id_domain)
