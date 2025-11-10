from odoo import _,  fields, models, api
#import odoo.addons.decimal_precision as dp


class VerifyOsCheckList(models.Model):
    _name = 'engc.os.verify.checklist'
    os_id = fields.Many2one('engc.os', "OS")
    relatorio_id = fields.Many2one(
        'engc.os.relatorios',
        string='Relatório',
        help='Relatório de atendimento relacionado (usado para atualizar o resumo automaticamente)'
    )
    section = fields.Many2one(
        string='Seção',
        comodel_name='engc.maintenance_plan.section',
    
    )
    state = fields.Selection(selection=[('draft','Rascunho'),('done','concluido')])
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
    peca_qtd = fields.Float('Qtd', default=0.0)
    
    def write(self, vals):
        """
        Sobrescreve o método write para atualizar automaticamente o resumo do relatório
        quando um item do checklist for marcado ou atualizado.
        """
        result = super(VerifyOsCheckList, self).write(vals)

        # Se check, observations ou medicao foram alterados, atualiza o resumo dos relatórios afetados
        if any(field in vals for field in ['check', 'observations', 'medicao', 'instruction']):
            # Agrupa por relatorio_id para evitar atualizações duplicadas
            relatorios_to_update = {}
            for record in self:
                if record.relatorio_id:
                    if record.relatorio_id.id not in relatorios_to_update:
                        relatorios_to_update[record.relatorio_id.id] = record.relatorio_id

            # Atualiza o resumo de cada relatório
            for relatorio in relatorios_to_update.values():
                relatorio._update_summary_from_checklist()

        # Se um item foi marcado, garante que outros relatórios não tenham o mesmo item marcado
        if 'check' in vals and vals.get('check'):
            for record in self:
                if record.check and record.relatorio_id:
                    # Busca outros itens marcados do mesmo checklist na mesma OS
                    other_checked = self.env['engc.os.verify.checklist'].search([
                        ('os_id', '=', record.os_id.id),
                        ('instruction', '=', record.instruction),
                        ('check', '=', True),
                        ('id', '!=', record.id)
                    ])
                    # Desmarca os outros
                    if other_checked:
                        other_checked.write({'check': False})

        return result
    