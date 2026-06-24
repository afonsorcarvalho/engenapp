from odoo import models, fields


class LabqualiHomepage(models.Model):
    _name = 'afr.labquali.homepage'
    _description = 'LabQuali Homepage Images'

    name = fields.Char(default='LabQuali Homepage')

    # Serviços
    svc_qualificacao      = fields.Image(string='Serviço: Qualificação IQ/OQ/PQ')
    svc_calibracao        = fields.Image(string='Serviço: Calibração de Sensores')
    svc_nr13              = fields.Image(string='Serviço: Inspeção NR13')
    svc_mapeamento        = fields.Image(string='Serviço: Mapeamento Térmico')

    # Diferenciais
    dif_rastreabilidade   = fields.Image(string='Diferencial: Rastreabilidade Metrológica')
    dif_laudos            = fields.Image(string='Diferencial: Laudos em 5 dias')
    dif_equipe            = fields.Image(string='Diferencial: Equipe Especializada')
    dif_portal            = fields.Image(string='Diferencial: Portal do Cliente')
    dif_nacional          = fields.Image(string='Diferencial: Atendimento Nacional')
    dif_conformidade      = fields.Image(string='Diferencial: Conformidade Regulatória')

    # Equipamentos
    eqp_autoclave         = fields.Image(string='Equip: Autoclaves a Vapor')
    eqp_estufa            = fields.Image(string='Equip: Estufas de Esterilização')
    eqp_camara_estab      = fields.Image(string='Equip: Câmaras de Estabilidade')
    eqp_camara_fria       = fields.Image(string='Equip: Câmaras Frias')
    eqp_incubadora        = fields.Image(string='Equip: Incubadoras')
    eqp_geladeira         = fields.Image(string='Equip: Geladeiras Farmacêuticas')
    eqp_vaso_pressao      = fields.Image(string='Equip: Vasos de Pressão')
    eqp_caldeira          = fields.Image(string='Equip: Caldeiras')
    eqp_liofilizador      = fields.Image(string='Equip: Liofilizadores')
    eqp_tunel_calor       = fields.Image(string='Equip: Túneis de Calor')
    eqp_lavadora          = fields.Image(string='Equip: Lavadoras Ultrassônicas')
    eqp_termometro        = fields.Image(string='Equip: Termômetros e Sondas')
