
from odoo import _, api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)

class ApplicationPartsWizard(models.TransientModel):
    _name = 'application.parts.wizard'

    list_parts_request = fields.One2many('application.parts.wizard.lines',  inverse_name="application_parts_wizard",
       string="Peças Requisitadas",
      )
    
    os_id = fields.Many2one('engc.os')
    def action_done(self):
        _logger.info("Done!!")
        _logger.debug(self)

        _logger.debug(self.env.context)
        _logger.debug(self.list_parts_request)
        list_parts_request = self.list_parts_request.mapped('id')
        for index, list_parts in enumerate(self.list_parts_request):
            
            _logger.debug(list_parts)
            
            if(list_parts.cancel):
                state = 'cancel'
            elif(list_parts.applied):
                state = 'aplicada'
            elif(list_parts.not_autorized):
                state = 'nao_autorizada'
            else:
                return
                
            request_parts = self.env['engc.os.request.parts'].search([('id','=',self.env.context['default_list_parts_request'][index][2]['request_parts'])])
            request_parts.write({
                'state':state,
                'relatorio_application_id':self.env.context.get('default_relatorio_id')
            })
        #next_action = {'type': 'ir.actions.client', 'tag': 'reload'}
        #self.env.reset()
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'type': 'success',
        #         'message': _('As peças foram aplicadas com sucesso!!!'),
        #         'next': next_action,
        #     }
        # }
        
        
    
class ListPartsLine(models.TransientModel):
    _name = 'application.parts.wizard.lines'

    application_parts_wizard = fields.Many2one(string='Wizard id', comodel_name='application.parts.wizard', ondelete='restrict')
    request_parts = fields.Many2one(string='Peças', comodel_name='engc.os.request.parts',readonly=True, ondelete='restrict')
    
    applied=fields.Boolean()
    cancel=fields.Boolean()
    not_autorized=fields.Boolean()
    @api.onchange('applied')
    def onchange_applied(self):
        value = self.applied
        if value:
            self.not_autorized = not value
            self.cancel = not value
    
    @api.onchange('cancel')
    def onchange_cancel(self):
        value = self.cancel
        if value:
            self.applied = not value
            self.not_autorized = not value

    @api.onchange('not_autorized')
    def onchange_not_autorized(self):
        
        value = self.not_autorized
        _logger.debug(value)
        if value:
            self.applied = not value
            self.cancel = not value

    
    state = fields.Selection(
        related='request_parts.state',
        readonly=True,
        
    
    )
    product_uom_qty = fields.Float(
        string="Quantity",
        
        related='request_parts.product_uom_qty',
        readonly=True,
       
        
        )
    
    product_uom = fields.Many2one(
        string="Unidade",
        
        related='request_parts.product_uom',
        readonly=True,
       
        
    )

   
