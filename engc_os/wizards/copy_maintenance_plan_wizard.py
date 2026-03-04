# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CopyMaintenancePlanWizard(models.TransientModel):
    _name = 'copy.maintenance.plan.wizard'
    _description = 'Wizard para Copiar Plano de Manutenção'

    maintenance_plan_id = fields.Many2one(
        'engc.maintenance_plan',
        string='Plano de Manutenção Atual',
        required=True,
        readonly=True
    )
    
    source_plan_id = fields.Many2one(
        'engc.maintenance_plan',
        string='Plano de Manutenção a Copiar',
        required=True,
        domain="[('id', '!=', maintenance_plan_id)]",
        help='Selecione o plano de manutenção do qual deseja copiar periodicidades, seções e instruções'
    )
    
    copy_periodicities = fields.Boolean(
        string='Copiar Periodicidades',
        default=True,
        help='Se marcado, copiará as periodicidades do plano selecionado'
    )
    
    copy_sections = fields.Boolean(
        string='Copiar Seções',
        default=True,
        help='Se marcado, copiará as seções e suas instruções do plano selecionado'
    )
    
    copy_instructions_without_section = fields.Boolean(
        string='Copiar Instruções sem Seção',
        default=True,
        help='Se marcado, copiará as instruções que não possuem seção associada'
    )

    @api.model
    def default_get(self, fields_list):
        """Preenche valores padrão ao abrir o wizard"""
        res = super(CopyMaintenancePlanWizard, self).default_get(fields_list)
        
        # Obtém o plano de manutenção do contexto
        active_id = self.env.context.get('active_id')
        if active_id:
            res['maintenance_plan_id'] = active_id
        
        return res

    def action_copy_plan(self):
        """Copia periodicidades, seções e instruções do plano selecionado para o plano atual"""
        self.ensure_one()
        
        if not self.source_plan_id:
            raise UserError(_('Por favor, selecione um plano de manutenção para copiar.'))
        
        if self.maintenance_plan_id.id == self.source_plan_id.id:
            raise UserError(_('Não é possível copiar o plano para ele mesmo.'))
        
        target_plan = self.maintenance_plan_id
        source_plan = self.source_plan_id
        
        # Mapeamento de seções antigas para novas (para associar instruções corretamente)
        section_mapping = {}
        
        try:
            # 1. Copiar periodicidades
            if self.copy_periodicities:
                target_plan.periodicity_ids = [(6, 0, source_plan.periodicity_ids.ids)]
                _logger.info(f"Copiadas {len(source_plan.periodicity_ids)} periodicidades")
            
            # 2. Copiar seções e suas instruções
            if self.copy_sections:
                for source_section in source_plan.section_ids.sorted('sequence'):
                    # Cria nova seção no plano atual
                    new_section = self.env['engc.maintenance_plan.section'].create({
                        'name': source_section.name,
                        'sequence': source_section.sequence,
                        'maintenance_plan': target_plan.id,
                    })
                    section_mapping[source_section.id] = new_section.id
                    
                    # Copia instruções da seção
                    for source_instruction in source_section.instrucion_ids.sorted('sequence'):
                        self.env['engc.maintenance_plan.instruction'].create({
                            'name': source_instruction.name,
                            'sequence': source_instruction.sequence,
                            'maintenance_plan': target_plan.id,
                            'section': new_section.id,
                            'periodicity': source_instruction.periodicity.id if source_instruction.periodicity else False,
                            'time_duration': source_instruction.time_duration,
                            'is_measurement': source_instruction.is_measurement,
                            'magnitude': source_instruction.magnitude.id if source_instruction.magnitude else False,
                            'tipo_de_campo': source_instruction.tipo_de_campo,
                        })
                    
                    _logger.info(f"Copiada seção '{source_section.name}' com {len(source_section.instrucion_ids)} instruções")
            
            # 3. Copiar instruções sem seção
            if self.copy_instructions_without_section:
                instructions_without_section = source_plan.get_instructions_without_section()
                for source_instruction in instructions_without_section:
                    self.env['engc.maintenance_plan.instruction'].create({
                        'name': source_instruction.name,
                        'sequence': source_instruction.sequence,
                        'maintenance_plan': target_plan.id,
                        'section': False,
                        'periodicity': source_instruction.periodicity.id if source_instruction.periodicity else False,
                        'time_duration': source_instruction.time_duration,
                        'is_measurement': source_instruction.is_measurement,
                        'magnitude': source_instruction.magnitude.id if source_instruction.magnitude else False,
                        'tipo_de_campo': source_instruction.tipo_de_campo,
                    })
                
                _logger.info(f"Copiadas {len(instructions_without_section)} instruções sem seção")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sucesso'),
                    'message': _('Plano de manutenção copiado com sucesso!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Erro ao copiar plano de manutenção: {str(e)}")
            raise UserError(_('Erro ao copiar plano de manutenção: %s') % str(e))
