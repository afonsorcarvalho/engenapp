
from odoo import models, fields, api


class EngcCalibration(models.Model):
    _name = 'engc.calibration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Calibração de Equipamentos'
    _check_company_auto = True

    name = fields.Char()
    
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    

    technician_id = fields.Many2one('hr.employee', 'Técnico',check_company=True)
 
   
    next_calibration = fields.Date('Próxima Calibração')
    
    
    duration = fields.Float('Duração da Calibração')
    note = fields.Text()
    oses = fields.One2many(
        string='Ordens de serviço',
        comodel_name='engc.os',
        inverse_name='equipment_id',
        check_company=True,
        store=False,
        
    )

    
  
    
   
    
    
      
    
    @api.depends('model','marca_id','serial_number')
    def _compute_name(self):
        
        for record in self:
            if not record.category_id.name or not record.model or not record.marca_id.name or not record.serial_number:
                record.name = ""
            else:
                record.name = record.category_id.name + " " + record.model + " " + record.marca_id.name + " "  + record.serial_number
    
    
    
   
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []

        if operator == 'ilike' and not (name or '').strip():
            recs = self.search([] + args, limit=limit)
        elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
            recs = self.search(['|', '|', ('name', operator, name), (
                'id', operator, name), ('serial_number', operator, name)] + args, limit=limit)

        return recs.name_get()




class CalibrationIntrument(models.Model):
    _name = 'engc.calibration.instruments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Instrumentos de calibração'

    name = fields.Char("Nome",track_visibility='always')
    id_number = fields.Char("Nº Idenficação")
    marca = fields.Char("Marca")
    modelo = fields.Char("Modelo")
    certificate_calibration = fields.Binary("Certificado de Calibração", track_visibility='always')
    certificate_number = fields.Char(string='Nº Certificado', track_visibility='always')
    certificate_partner = fields.Many2one(string='Certificadora', comodel_name='res.partner', ondelete='restrict',track_visibility='always')
    date_calibration = fields.Date('Data da Calibração',track_visibility='always')
    
    validate_calibration = fields.Date('Data de Validade',track_visibility='always')
    
  





   

