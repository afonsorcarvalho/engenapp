from dateutil.relativedelta import relativedelta
from datetime import date

from odoo.tests.common import TransactionCase


class CalibrationCase(TransactionCase):
    """Fixture com os valores reais do padrão QPS-001 (cert. R0712/2026).

    Lidos da base odoo-labquali em 23/09/2026:
        incerteza 0,035 | k 2,0 | erro 0,01 | resolução 0,01 | veff 2 | unidade Tempo
    """

    def setUp(self):
        super().setUp()
        self.unit_tempo = self.env['engc.calibration.measurement.unit'].create({
            'name': 'Tempo',
            'simbolo': 's',
        })
        self.instrument = self.env['engc.calibration.instruments'].create({
            'name': 'QPS-001 - Cronômetro Digital',
            'id_number': 'QPS-001',
            'marca': 'Minipa',
            'modelo': 'MTH-1501',
        })
        self.certificate = self.env['engc.calibration.instruments.certificates'].create({
            'instrument_id': self.instrument.id,
            'certificate_number': 'R0712/2026',
            'date_calibration': date.today(),
            'validate_calibration': date.today() + relativedelta(years=1),
        })
        self.unc_line = self.env['engc.calibration.instruments.uncertainty.lines'].create({
            'certificate': self.certificate.id,
            'unit_of_measurement': self.unit_tempo.id,
            'uncertainty': 0.035,
            'coverage_factor': 2.0,
            'erro_value': 0.01,
            'resolution': 0.01,
            'veff': 2.0,
        })

    def make_measurement(self, **kw):
        """Cria uma medição já com o onchange do padrão disparado."""
        vals = {
            'title': 'Tempo',
            'date_measurement': date.today(),
            'instrument_id': self.instrument.id,
            'unit_of_measurement': self.unit_tempo.id,
        }
        vals.update(kw)
        measurement = self.env['engc.calibration.measurement'].create(vals)
        # O preenchimento dos campos *_instrument só acontece via onchange hoje.
        measurement.onchange_unit_of_measurement()
        return measurement

    def make_line(self, measurement, true_value, r1, r2, r3):
        return self.env['engc.calibration.measurement.lines'].create({
            'measurement_id': measurement.id,
            'true_quantity_value': true_value,
            'measurement_quantity_value_1': r1,
            'measurement_quantity_value_2': r2,
            'measurement_quantity_value_3': r3,
            'coverage_factor': 2.0,
        })

    def make_equipment(self, name=None):
        """engc.equipment tem 6 campos obrigatórios além do nome; todos
        precisam de registro próprio. Conferido no código do modelo.

        `engc.equipment.marca` tem `unique(name)` e `engc.equipment` tem
        `unique(serial_number, marca_id)` — chamar este helper mais de uma
        vez por teste (ex.: `create()` em lote) precisa de nome/serial
        distintos a cada chamada, daí o contador.
        """
        self._equip_seq = getattr(self, '_equip_seq', 0) + 1
        if name is None:
            name = 'Autoclave %03d' % self._equip_seq
        return self.env['engc.equipment'].create({
            'name': name,
            'category_id': self.env['engc.equipment.category'].create(
                {'name': 'Categoria Teste'}).id,
            'means_of_aquisition_id': self.env[
                'engc.equipment.means.of.aquisition'].create(
                {'name': 'Compra'}).id,
            'location_id': self.env['engc.equipment.location'].create(
                {'name': 'Sala Teste'}).id,
            'marca_id': self.env['engc.equipment.marca'].create(
                {'name': 'Marca Teste %03d' % self._equip_seq}).id,
            'model': 'MOD-001',
            'serial_number': 'SN-%s' % name,
        })

    def make_calibration_vals(self, **kw):
        """Dicionário mínimo que satisfaz os required de engc.calibration."""
        vals = {
            'client_id': self.env['res.partner'].create(
                {'name': 'Hospital Teste'}).id,
            'equipment_id': self.make_equipment().id,
            'technician_id': self.env['hr.employee'].create(
                {'name': 'Técnico Teste'}).id,
            'measurement_procedure': self.env[
                'engc.calibration.measurement.procedure'].create({
                    'codigo': 'PM-001',
                    'description': 'Procedimento de teste',
                }).id,
            'date_calibration': date.today(),
            'date_next_calibration': date.today() + relativedelta(years=1),
            'instruments_ids': [(6, 0, [self.instrument.id])],
        }
        vals.update(kw)
        return vals
