from odoo import _,  fields, models
import odoo.addons.decimal_precision as dp


class VerifyOsCheckList(models.Model):
    _name = 'engc.os.verify.checklist'
    os_id = fields.Many2one('engc.os', "OS")
    section = fields.Many2one(
        string='Seção',
        comodel_name='engc.maintenance_plan.section',
    
    )
    instruction = fields.Char('Instruções')
    check = fields.Boolean()
    sequence = fields.Integer(string='Sequence', default=10)
    tem_medicao = fields.Boolean("tem medição?")
    medicao = fields.Float("Medições")
    magnitude = fields.Char('Grandeza')
    tipo_de_campo = fields.Selection(
        string=u'Tipo de Campo',
        selection=[('float', 'Valor'), ('checkbox', 'Checkbox'),('selection','Seleção')],
        default='checkbox'
    )
    observations = fields.Char()
    troca_peca = fields.Boolean(string="Substituição de Peça?",required=False)    
    peca = fields.Many2one('product.product', u'Peça', required=False)
    peca_qtd = fields.Float('Qtd', default=0.0,	digits=dp.get_precision('Product Unit of Measure'))