# -*- encoding: utf-8 -*-
# © 2024 Afonso Carvalho


from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError
import csv
from datetime import datetime, timezone, timedelta
import pytz
class EngcEquipment(models.Model):
    _inherit = 'engc.equipment'

    cycle_model = fields.Many2one(string='Modelo de ciclo', comodel_name='steril_supervisorio.cycle_model', ondelete='restrict')
    cycle_type_id = fields.Many2one(string='Tipo de ciclo', comodel_name='afr.cycle.type', ondelete='restrict')
    chamber_size = fields.Float(string="Volume Câmara (L)")
    cycle_path = fields.Char(string="Diretorio do ciclo")
    
    def name_get(self):
        """
        Personaliza a exibição do nome do equipamento para mostrar o apelido primeiro.
        """
        result = []
        print("######    entrou no name_get")
        print(self.env.context)
        for record in self:
            # Verifica se deve mostrar apelido primeiro (contexto do wizard)
            show_apelido_first = self.env.context.get('show_apelido_first', False)
            
            if show_apelido_first:
                apelido = record.apelido or ""
                nome = record.name or ""
                if apelido and nome:
                    display_name = f"{apelido} - {nome}"
                elif apelido:
                    display_name = apelido
                elif nome:
                    display_name = nome
                else:
                    display_name = f"Equipamento {record.id}"
            else:
                # Comportamento padrão
                display_name = record.name or f"Equipamento {record.id}"
            
            result.append((record.id, display_name))
        return result

    def action_read_cycles(self):
        _logger.info(f"Lendo ciclos do equipamento {self}")
        self.env['afr.supervisorio.ciclos'].action_ler_diretorio_ciclos(equipment_id=self)





    
