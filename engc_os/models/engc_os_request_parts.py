from odoo import models, fields,  api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class RequestParts(models.Model):
    _name = 'engc.os.request.parts'
    _description = "Requisição de peças"
    _check_company_auto = True
    name = fields.Char()
    
    
    @api.depends('name', 'request_parts_id')
    def name_get(self):
        result = []
        for record in self:
            
            name = '[' + record.product_id.default_code + '] ' + record.product_id.name
            
            result.append((record.id, name))
        return result
    
    company_id = fields.Many2one(
        string='Instituição', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    state = fields.Selection(selection = [
        ('requisitada','Requisitada'),
        ('autorizada','Autorizada'),
        ('aplicada','Aplicada'),
        ('nao_autorizada','Não Autorizada'),
        ('cancel','Cancelada'),
        ],
        default = 'requisitada',
        required=True
        

        )

    product_id = fields.Many2one('product.product', u'Peças', 
                                  required=True, check_company=True, 
                                  domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")


    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if not line.product_id:
                continue    
           
            line.name = line.product_id.name 
       
    product_uom_qty = fields.Float(
        string="Quantity",
        compute='_compute_product_qty',
        digits='Product Unit of Measure', default=1.0,
        store=True, readonly=False, required=True, precompute=True)
    
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])
    
    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id
    
    
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        for line in self:
            if not line.product_id or not line.product_uom or not line.product_uom_qty:
                line.product_uom_qty = 0.0
                continue
            line.product_uom_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)

    placed = fields.Boolean('Aplicada')
    
    @api.onchange('placed')
    def onchange_placed(self):
        print(self.env.context)
        #if self.placed:
        #    self.relatorio_application_id = self.
    
    
    os_id = fields.Many2one(
        'engc.os', 'Ordem de Serviço',
         index=True, ondelete='cascade', check_company=True)
    relatorio_request_id = fields.Many2one('engc.os.relatorios', 'Relatório Solicitante')
    relatorio_application_id = fields.Many2one('engc.os.relatorios', 'Relatório Aplicado')

    #******************************************
    #  ACTIONS
    #
    #******************************************

    def action_application_request_parts(self):
        _logger.info("Aplicando peças")
