
from odoo import models, fields, api, _


class EngcCalibration(models.Model):
    _name = 'engc.calibration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Calibração de Equipamentos'
    _check_company_auto = True

    name = fields.Char( readonly=True, default=lambda self: _('New'))

    STATES = [
        ('draft', 'Rascunho'),
        ('confirmed', 'Em andamento'),
        ('done', 'Concluída'),
    ]
    state = fields.Selection(string='State', selection=STATES)
    
    company_id = fields.Many2one(
        string='Instituição',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.user.company_id
    )
    client_id = fields.Many2one("res.partner", "Cliente")
    equipment_id = fields.Many2one("engc.equipment",'Equipamento')
    technician_id = fields.Many2one(
        'hr.employee', 'Técnico', check_company=True)
    date_calibration = fields.Date(
        'Data Cal.', help="Data da realização da calibração")
    date_next_calibration = fields.Date('Próxima Calibração')
    
    instruments_ids = fields.Many2many(string='Instrumentos padrão', comodel_name='engc.calibration.instruments')
    
    issue_date = fields.Date('Data de Emissão', help="Data de emissão do certificado de calibração")
    duration = fields.Float('Duração')
    note = fields.Text()
    measurement_procedure = fields.Many2one(string='Norma/Procedimento', comodel_name='engc.calibration.measurement.procedure', ondelete='restrict')
    measurement_ids = fields.One2many(string='Cod. Medidas', comodel_name='engc.calibration.measurement',inverse_name='calibration_id', ondelete='restrict')
    
    @api.model
    def create(self, vals):
        """Salva ou atualiza os dados no banco de dados"""
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.calibration_sequence') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('engc.calibration_sequence') or _('New')
        

        result = super(EngcCalibration, self).create(vals)
        return result
    
    def action_confirmed(self):
        for rec in self:
            rec.write({
                'state': 'confirmed'
            })

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done'
            })
    def action_draft(self):
        for rec in self:
            rec.write({
                'state': 'draf'
            })

    # @api.depends('model', 'marca_id', 'serial_number')
    # def _compute_name(self):

    #     for record in self:
    #         if not record.category_id.name or not record.model or not record.marca_id.name or not record.serial_number:
    #             record.name = ""
    #         else:
    #             record.name = record.category_id.name + " " + record.model + \
    #                 " " + record.marca_id.name + " " + record.serial_number

    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     args = args or []

    #     if operator == 'ilike' and not (name or '').strip():
    #         recs = self.search([] + args, limit=limit)
    #     elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
    #         recs = self.search(['|', '|', ('name', operator, name), (
    #             'id', operator, name), ('serial_number', operator, name)] + args, limit=limit)

    #     return recs.name_get()


class CalibrationIntrument(models.Model):
    _name = 'engc.calibration.instruments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Instrumentos de calibração'

    name = fields.Char("Nome", tracking=True)
    id_number = fields.Char("Nº Idenficação")
    
    
    marca = fields.Char("Marca")
    modelo = fields.Char("Modelo")
    certificate_calibration = fields.Binary(
        "Certificado de Calibração", tracking=True)
    certificate_number = fields.Char(
        string='Nº Certificado', tracking=True)
    certificate_partner = fields.Many2one(
        string='Certificadora', comodel_name='res.partner', ondelete='restrict', tracking=True)
    date_calibration = fields.Date(
        'Data da Calibração', tracking=True)
    date_next_calibration = fields.Date(
        'Data Prox. Cal.', tracking=True)
    validate_calibration = fields.Date(
        'Data de Validade', tracking=True)
    


class CalibrationTypes(models.Model):
    _name = 'engc.calibration.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tipos de calibração'

    name = fields.Char("Nome", tracking=True)


class CalibrationMeasurement (models.Model):
    _name = 'engc.calibration.measurement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Medições da Calibração'

    name = fields.Char( readonly=True, default=lambda self: _('New'))
    calibration_id = fields.Many2one(string='Cod. Calibração', comodel_name='engc.calibration', ondelete='restrict')
    date_measurement= fields.Date("Data de aquisição")
    measurement_lines = fields.One2many('engc.calibration.measurement.lines', 'measurement_id') 
    environmental_conditions = fields.Char('Condições ambientais') 

    @api.model
    def create(self, vals):
        """Salva ou atualiza os dados no banco de dados"""
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.calibration_measurement_sequence') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('engc.calibration_measurement_sequence') or _('New')
        

        result = super(CalibrationMeasurement, self).create(vals)
        return result
   
class CalibrationMeasurementLines (models.Model):
    _name = 'engc.calibration.measurement.lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Medições da Calibração'

    name = fields.Char("Nome", tracking=True)
    measurement_id = fields.Many2one(string='Cod. Medidas', comodel_name='engc.calibration.measurement', ondelete='restrict')
    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', ondelete='restrict')
    true_quantity_value = fields.Float(string="Valor Real" )
    measurement_quantity_value= fields.Float(string="Valor Medido" )
    erro_value= fields.Float(string="Valor Erro" )
    uncertainty= fields.Float(string="Incerteza" )
    coverage_factor= fields.Float(string="Fator K" )
   
    
class CalibrationMeasurementProcedure (models.Model):
    _name = 'engc.calibration.measurement.procedure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Procedimentos de Medições da Calibração'

    name = fields.Char( readonly=True, default=lambda self: _('New'))
    codigo = fields.Char("Código", tracking=True)
    description = fields.Char("Descrição")
    
    environmental_conditions = fields.Char("Condições ambientais")
    revision = fields.Integer(string='Revisão')
    emission = fields.Many2one(string= "Emitido por",
        comodel_name='hr.employee'
    )
    checked = fields.Many2one( string="Conferido por",comodel_name='hr.employee')
    aproved = fields.Many2one( string="Aprovado por",comodel_name='hr.employee')
    text = fields.Html("Texto")

    @api.model
    def create(self, vals):
        """Salva ou atualiza os dados no banco de dados"""
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.calibration_procedure_sequence') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('engc.calibration_procedure_sequence') or _('New')
        

        result = super(CalibrationMeasurementProcedure, self).create(vals)
        return result

class CalibrationMeasurementUnit (models.Model):
    _name = 'engc.calibration.measurement.unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Unidade de Medida da Calibração'

    name = fields.Char("Grandeza", tracking=True)
    unit_name = fields.Char("Unidade", tracking=True)
    simbolo = fields.Char("Símbolo", tracking=True)
