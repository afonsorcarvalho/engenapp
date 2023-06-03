

import json
from math import sqrt
from statistics import mean, stdev

from datetime import date
from dateutil.relativedelta import relativedelta



from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo import netsvc

from odoo.exceptions import UserError, ValidationError
from babel.dates import  format_date
from odoo.tools.misc import  get_lang

import logging
_logger = logging.getLogger(__name__)

#TODO Não deixar excluir instrumento padrao caso ele esteja sendo utilizado nas medidas adquiridas

class EngcCalibration(models.Model):
    _name = 'engc.calibration'
    _inherit = ['mail.thread']
    _description = 'Calibração de Equipamentos'
    _check_company_auto = True

    name = fields.Char( readonly=True, default=lambda self: _('New'))

    STATES = [
        ('draft', 'Rascunho'),
        ('confirmed', 'Em andamento'),
        ('done', 'Concluída'),
    ]
    state = fields.Selection(string='State', selection=STATES, default="draft", 
    required=True, tracking=True
    )
    
    company_id = fields.Many2one(
        string='Instituição',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.user.company_id
    )
    os_id = fields.Many2one("engc.os", "Ordem de Serviço")
    client_id = fields.Many2one("res.partner", "Cliente", required=True)
    equipment_id = fields.Many2one("engc.equipment",'Equipamento', 
    required=True
    )

    technician_id = fields.Many2one(
        'hr.employee', 'Técnico', check_company=True, required=True)
    date_calibration = fields.Date(
        'Data Cal.', help="Data da realização da calibração", required=True)
    date_next_calibration = fields.Date('Próxima Calibração')
    
    @api.constrains("date_next_calibration", "date_calibration", )
    def _check_date_calibration(self):
        for rec in self:
            if rec.date_calibration > rec.date_next_calibration:
                raise ValidationError(_("A data de calibração não pode ser maor que a data da proxima calibração"))
    
    instruments_ids = fields.Many2many(string='Instrumentos padrão', comodel_name='engc.calibration.instruments', required=True)
    
    issue_date = fields.Date('Data de Emissão', help="Data de emissão do certificado de calibração")
    duration = fields.Float('Duração')
    note = fields.Text("Observações")
    measurement_procedure = fields.Many2one(string='Norma/Procedimento', comodel_name='engc.calibration.measurement.procedure', ondelete='restrict', required=True)
    measurement_ids = fields.One2many(string='Cod. Medidas', comodel_name='engc.calibration.measurement',inverse_name='calibration_id', ondelete='restrict')
    
    environmental_conditions = fields.Char('Condições ambientais', 
    required=True, 
    default='25 ºC, 60% UR',
    
    
    ) 
    @api.onchange('date_calibration')
    def onchange_date_calibration(self):
        if self.date_calibration:
            self.date_next_calibration = self.date_calibration + relativedelta(years=1)
    @api.onchange('measurement_ids')
    def onchange_measurement_ids(self):
        if self.measurement_ids:
            _logger.info(self.measurement_ids)
    
    # @api.ondelete(at_uninstall=False)
    # def _unlink_except_instruments_ids(self):
        
    #     if any(instrument.id in self.instruments_ids.mapped(lambda r: r.id) for instrument in self.measurement_ids.mapped(lambda r: r.instrument_id)):
    #         raise UserError("Não pode deletar um instrumento que está em um medida adquirida ")
        
    @api.model
    def create(self, vals):
        """Salva ou atualiza os dados no banco de dados"""
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.calibration_sequence') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('engc.calibration_sequence') or _('New')
        
        
        result = super(EngcCalibration, self).create(vals)
        self.action_confirmed()
        return result
    
    def get_sign_date(self):
        '''
            Função que retorna uma string da data para impressão 
            no formato: ex. São Luis-MA, 02 de agosto de 2022
        '''
        locale = get_lang(self.env).code

        _logger.info(str(self.company_id.city )+ '-' + str(self.company_id.state_id.code))
        date_str = str(self.company_id.city) + '-' + str(self.company_id.state_id.code) + ', ' + format_date(self.issue_date,format="long",locale=locale)
        return   date_str


    def action_confirmed(self):
        for rec in self:
            resp = rec.write({
                'state': 'confirmed',
            })
            if resp:
                if rec.os_id:
                    rec.os_id.calibration_created = True
                    rec.os_id.calibration_id = self.id

    def action_done(self):
        for rec in self:
            if not rec.date_calibration:
                raise ValidationError(_("Verifique a Data de Calibração"))
            if not rec.date_next_calibration:
                raise ValidationError(_("Verifique a Data da proxima Calibração"))
            if not rec.date_next_calibration:
                raise ValidationError(_("Verifique a Data da proxima Calibração"))
            if not rec.technician_id:
                raise ValidationError(_("Verifique o Calibrado por"))
                
            rec.write({
                    'state': 'done',
                    'issue_date': date.today(),


                })
    def action_draft(self):
        for rec in self:
            rec.write({

                'state': 'draft'
            })


class CalibrationInstrument(models.Model):
    _name = 'engc.calibration.instruments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Instrumentos de calibração'

    name = fields.Char("Nome", tracking=True)
    id_number = fields.Char("Nº Idenficação")
    
    tag = fields.Char("Tag")    
    marca = fields.Char("Marca")
    modelo = fields.Char("Modelo")
   

    certificate_ids = fields.One2many(
        string='Certificado',
        comodel_name='engc.calibration.instruments.certificates',
        inverse_name='instrument_id',)
    
   

    def get_certificate_valid(self):
        return  self.certificate_ids.filtered(lambda rec: rec.is_valid)
    

     
    

    


class CalibrationInstrumentCertificates(models.Model):
    _name = 'engc.calibration.instruments.certificates'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Certificados dos Instrumentos de calibração'

    
    instrument_id = fields.Many2one(
        string='Instrumento',
        comodel_name='engc.calibration.instruments',
        ondelete='restrict',
        required=True
        
    )
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
    environmental_conditions = fields.Char('Condições ambientais') 

    uncertainty_lines = fields.One2many(
        string='Incertezas e erros',
        comodel_name='engc.calibration.instruments.uncertainty.lines',
        inverse_name='certificate',
    )
    is_valid = fields.Boolean("É válido", compute="_compute_is_valid")

    @api.depends('validate_calibration')
    def _compute_is_valid(self):
        if self.validate_calibration :
            self.is_valid()


    @api.onchange('date_calibration')
    def onchange_date_calibration(self):
        if self.date_calibration:
            self.date_next_calibration = self.date_calibration + relativedelta(years=1)
            self.validate_calibration = self.date_calibration + relativedelta(years=1)
    
    def is_valid(self):
        for rec in self:
            return rec.validate_calibration >= date.today()

        
  



class CalibrationIntrumentUncertaintyLines(models.Model):
    _name = 'engc.calibration.instruments.uncertainty.lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Incertezas dos Instrumentos de calibração'
    
    
    certificate = fields.Many2one(
        string='Instrumento',
        comodel_name='engc.calibration.instruments.certificates',
        ondelete='restrict',
        required=True
    )

    
    erro_value= fields.Float(string="Erro fiducial" )
    uncertainty = fields.Float('Incerteza', 
    required=True
    ) 
    coverage_factor= fields.Float(string="Fator K", 
        required=True, default=2.0
     )
    veff = fields.Float(string = "Veff", help="Graus de liberdade efetiva. Para valores infinitos preencha com qualquer número maior que 100")
    resolution = fields.Float(string = "Resolução", help="Resolução do padrão", 
        required=True
    )
    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', ondelete='restrict', 
    required=True
    )

    # _sql_constraints = [
    #     (
    #         'instrument_id_unit_of_measurement_uniq',
    #         'unique (unit_of_measuremen)',
    #         'A unidade de medida deve ser unica para cada instrumento'
    #     ),
    # ]
    


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
    title = fields.Char("Título",help="O título que aparecerá no certificado acima das medidas adquiridas")
    calibration_id = fields.Many2one(string='Cod. Calibração', comodel_name='engc.calibration', ondelete='restrict')
    date_measurement= fields.Date("Data de aquisição")
    measurement_lines = fields.One2many('engc.calibration.measurement.lines', 'measurement_id') 
    uncertainty = fields.Char('Incerteza') 
    coverage_factor= fields.Float(string="Fator K padrão", 
    required=True, default=2.0, help="Fator de abrangência padrão que será utilizado no cálculo da incerteza das medições"
     )
    environmental_conditions = fields.Char('Condições ambientais', default="25 graus Celsius, Umidade Relativa 60%")
    instrument_id = fields.Many2one(
        'engc.calibration.instruments',
        string='Padrão utilizado',
        required=True
        )
    instrument_id_domain = fields.Char(
        compute="_compute_instrument_id_domain",
        readonly=True,
        store=False,
    )
    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', ondelete='restrict')
    unit_of_measurement_domain = fields.Char(
        compute="_compute_unit_of_measurement_domain",
        readonly=True,
        store=False,
    )
    @api.depends('calibration_id')
    def _compute_instrument_id_domain(self):
        domain = []
        for rec in self:
            if rec.instrument_id_domain:
                domain = [('id', 'in', rec.calibration_id.instruments_ids.mapped(lambda r: r.id))]
            
            rec.instrument_id_domain = json.dumps(domain)
            
          


    @api.depends('instrument_id')
    def _compute_unit_of_measurement_domain(self):
        for rec in self:
            certificates  = self.instrument_id.get_certificate_valid()
            uncertainty_lines = certificates.mapped(lambda r: r.uncertainty_lines)
            unit_of_measurement_lines = uncertainty_lines.mapped(lambda r: r.unit_of_measurement)
            rec.unit_of_measurement_domain = json.dumps(
                [('id', 'in', unit_of_measurement_lines.mapped(lambda r: r.id))]
            )
    
    uncertainty_instrument = fields.Float(
        
        readonly=True,
   
        )
    erro_value_instrument = fields.Float(
       
        readonly=True,
   
        )
    coverage_factor_instrument = fields.Float(
        
        readonly=True,
   
        )
    resolution_instrument = fields.Float(
       
        readonly=True,
   
        )
    veff_instrument = fields.Float(
      
        readonly=True,
   
        )
    #TODO fazer ele pegar o certificado valido mais novo, caso tenha mais de um certificado válido
    def _search_certificates_valid(self):
        '''
            Pega os certificados válidos do instrumento de calibração
        '''
        certificates = self.instrument_id.certificate_ids.filtered(lambda rec: rec.validate_calibration >= date.today())
        if len(certificates) == 0:
                raise ValidationError(_("Verifique a Data de vencimento da Calibração do instrumento utilizado. Não é possível utilizar intrumento com calibração vencida"))
        return certificates
    
    def _search_statistics(self):
        # Procura a incerteza 
        uncertainty_id_line = []
        certificates = self._search_certificates_valid()
        if len(certificates) == 0:
            return [],[]
        
        uncertainty_id_line = certificates.uncertainty_lines
        if len(uncertainty_id_line) > 0:
            uncertainty_id_line = uncertainty_id_line.filtered(lambda rec: rec.unit_of_measurement.id == self.unit_of_measurement.id)
            if len(uncertainty_id_line) == 0:
                raise ValidationError(_("Verifique a unidade de medida selecionada. Não existe essa unidade no instrumento padrão utilizado."))
        _logger.info(uncertainty_id_line)   

        return uncertainty_id_line,certificates


    @api.onchange('instrument_id')
    def onchange_instrument_id(self):
        self.unit_of_measurement = None

    @api.onchange('unit_of_measurement')
    def onchange_unit_of_measurement(self):
        if self.unit_of_measurement:
            uncertainty_id_line, certificate_instrument = self._search_statistics()
            _logger.info(self.unit_of_measurement)
            _logger.info(uncertainty_id_line)
            _logger.info(certificate_instrument)
           # self.certificate_instrument = certificate_instrument.id
            self.resolution_instrument = uncertainty_id_line.resolution
            self.coverage_factor_instrument = uncertainty_id_line.coverage_factor
            self.uncertainty_instrument = uncertainty_id_line.uncertainty
            self.erro_value_instrument = uncertainty_id_line.erro_value
            self.veff_instrument = uncertainty_id_line.veff
    
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

   
    measurement_id = fields.Many2one(string='Cod. Medidas', comodel_name='engc.calibration.measurement', ondelete='restrict')
    
    related='field_name',
    readonly=True,
    store=True
    
    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', related='measurement_id.unit_of_measurement' )
    true_quantity_value = fields.Float(string="Valor Real" )
    measurement_quantity_value_1= fields.Float(string="Leitura 01" )
    measurement_quantity_value_2= fields.Float(string="Leitura 02" )
    measurement_quantity_value_3= fields.Float(string="Leitura 03" )
    measurement_quantity_value_mean= fields.Float(string="Média", compute="_compute_statistics", store=True)
    erro_value= fields.Float(string="Valor Erro", compute="_compute_statistics", store=True )
    uncertainty= fields.Float(string="Incerteza",compute="_compute_statistics", store=True )
    coverage_factor= fields.Float(string="Fator K", default=2.0 )
    veff = fields.Float(string = "Veff",compute="_compute_statistics", store=True)
    resolutino_instrument = fields.Float(string = "Resolução do instrumento", compute="_compute_statistics", store=True)

    @api.depends('measurement_id.instrument_id','measurement_id.unit_of_measurement','true_quantity_value','coverage_factor','measurement_quantity_value_1','measurement_quantity_value_2','measurement_quantity_value_3')
    def _compute_statistics(self):
        for rec in self:
            uncertainty_instrument = rec.measurement_id.uncertainty_instrument
            k_instrument = 2.0
            if rec.measurement_id.coverage_factor_instrument != 0: 
                k_instrument = rec.measurement_id.coverage_factor_instrument
        
            erro_instrument = rec.measurement_id.erro_value_instrument
            resolution_instrument= rec.measurement_id.resolution_instrument
            
            for record in rec:
                values = [
                    record.measurement_quantity_value_1,
                    record.measurement_quantity_value_2,
                    record.measurement_quantity_value_3,
                    ]
            
                record.measurement_quantity_value_mean = mean(values)
                record.erro_value = record.measurement_quantity_value_mean - record.true_quantity_value
                # incerteza combinada é igual a raiz quadrada da soma de:
                #    - incerteza das medidas
                #    - incerteza do instrumento
                #    - incerteza do erro do instrumento
                #    - incerteza da resolução do instrumento
            
                combined_uncertainty = sqrt((stdev(values)/2)**2
                        + (uncertainty_instrument/k_instrument)**2
                        + (erro_instrument/sqrt(3))**2
                        + (resolution_instrument/sqrt(12))**2
                        )
                
                # incerteza =  incerteza combinada*k
                record.uncertainty = record.coverage_factor * combined_uncertainty

                #grau de liberdade efetivo
                try:
                    record.veff = 3*(combined_uncertainty/(stdev(values)/2))**4
                except:
                    record.veff = 0





   
    
class CalibrationMeasurementProcedure (models.Model):
    _name = 'engc.calibration.measurement.procedure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Procedimentos de Medições da Calibração'

    STATES = [
        ('review', 'Em Revisão'),
        ('emited', 'Emitido'),
        ('confered', 'Conferido'),
        ('aproved', 'Aprovado'),
    ]
    state = fields.Selection(string='State', selection=STATES, default="review", 
    required=True
    )

    name = fields.Char( readonly=True, default=lambda self: _('New'))
    codigo = fields.Char("Código", tracking=True)
    description = fields.Char("Descrição")
    
    environmental_conditions = fields.Char("Condições ambientais")
    revision = fields.Integer(string='Revisão',tracking=True)
    emission = fields.Many2one(string= "Emitido por",
        comodel_name='hr.employee',tracking=True
    )
    checked = fields.Many2one( string="Conferido por",comodel_name='hr.employee',tracking=True)
    aproved = fields.Many2one( string="Aprovado por",comodel_name='hr.employee',tracking=True)

    
    objective = fields.Html("Objetivo")
    application = fields.Html("Aplicação")
    reference_documents = fields.Html("Documentos de Referência")
    terminology = fields.Html("Terminologia")
    materials_used = fields.Html("Materiais utilizados")
    ambiental_conditions = fields.Html("Condições ambientais")
    precaution_and_preparation = fields.Html("Precauções e Preparação")
    method = fields.Html("Método")
    analysis = fields.Html("Determinação e análise dos resultados")
    measurement_uncertainty = fields.Html("Incerteza da medição")
    presentation_of_results = fields.Html("Apresentação dos resultados")
    
    anexos_ids = fields.One2many(string='Anexos',comodel_name='engc.calibration.measurement.procedure.anexos',inverse_name='measurements_procedure_ids' )
    changes = fields.Html("Alterações")
    document = fields.Binary(
        "Documento do PM", tracking=True)

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

    #******************************************
    #  ACTIONS
    #
    #******************************************
    
    def action_emited(self):
        self.write({
            'state':'emited'
        })
        

    def action_confered(self):
        self.write({
            'state':'confered'
        })

    def action_aproved(self):
        self.write({
            'state':'aproved'
        })

    def action_review(self):
        self.write({
            'state':'review'
        })
    

    def action_cancel(self):
        self.write({
            'state':'cancel'
        })
    


class CalibrationMeasurementProcedureAnexos(models.Model):
    _name = 'engc.calibration.measurement.procedure.anexos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Anexos do Procedimentos de Medições da Calibração'

    measurements_procedure_ids = fields.Many2one(string ='Procedimento de medição',comodel_name = 'engc.calibration.measurement.procedure')
    name = fields.Char("Título")
    text = fields.Html("Corpo do Texto")
    

class CalibrationMeasurementUnit (models.Model):
    _name = 'engc.calibration.measurement.unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Unidade de Medida da Calibração'

    name = fields.Char("Unidade", tracking=True)
    
    simbolo = fields.Char("Símbolo", tracking=True)
