# -*- coding: utf-8 -*-

import random
from odoo import models, fields, api, _

from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from calendar import monthcalendar
from odoo.exceptions import UserError, ValidationError
import pytz
import logging
import calendar
import holidays
from ..tools.schedule_preventive import SchedulePreventive,calcular_divisores
import math


_logger = logging.getLogger(__name__)



class EngcPreventiva(models.Model):
    _name = 'engc.preventive'
    _description = 'Preventiva'
    _order = 'data_programada DESC'
    _inherit =['mail.thread','mail.activity.mixin']

    _check_company_auto = True

   
    
    STATE_SELECTION = [
        ('draft', 'Criada'),
        ('cancel', 'Cancelada'),
        ('atrasada', 'Atrasada'),
        ('programada', 'Ordem Gerada'),
        ('reagendada','Reagendada'),
        ('done', 'Concluída'),
    ]
    state = fields.Selection(STATE_SELECTION, string='Status',
                             copy=False, default='draft',  tracking=True,
                             help="*  \'Criada\' usado quando a preventiva está somente criada.\n"
                                  "*  \'Cancelada\' usado quando a preventiva foi cancelada pelo usuário.\n"
                                  "*  \'Atrasada\' usado quando a preventiva não foi executada no dia programado.\n"
                                  "*  \'Ordem Gerada\' usado quando já existe OS gerada para execução.\n"
                                  "*  \'Reagendada\' usada quando OS gerada e foi reagendada a execução.\n"
                                  "*  \'Concluída\' a ordem de serviço já foi executada."
                            )
    name = fields.Char()
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )
    equipment = fields.Many2one(
        string=u'Equipamento',
        comodel_name='engc.equipment',
        ondelete='cascade',
        check_company=True
    )
    client = fields.Many2one(
        string=u'Cliente',
        comodel_name='res.partner',
        ondelete='set null',
        company_dependent=True
    )
    cronograma = fields.Many2one(
        string=u'Cronograma',
        comodel_name='engc.preventive.cronograma',
        ondelete='set null',
        check_company=True
    )
    maintenance_plan = fields.Many2one(
        string=u'Cronograma',
        comodel_name='engc.maintenance_plan',
        ondelete='set null',
        company_dependent=True
    )
    periodicity_ids = fields.Many2many(
        string=u'Preventiva',
        comodel_name='engc.maintenance_plan.periodicity',
       
        
    )
    
    
    tecnico = fields.Many2one(
        string=u'Técnico',
        comodel_name='hr.employee',
        ondelete='set null',
        tracking=True,
        company_dependent=True
    )
    # grupo_id = fields.Many2many(
    #     'engc.instruction.grupo',
    #     string='Grupo de Instruções',
    #     tracking=True,
    #     company_dependent=True,
    # )
    
    # tempo_estimado = fields.Float(
    #     string=u'Tempo Estimado', 
    #     help="Tempo estimado de conclusão da preventiva.", default=1.0)
    tempo_estimado = fields.Float(
        string=u'Tempo Estimado', 
        compute = "_compute_tempo_estimado",
        help="Tempo estimado de conclusão da preventiva.", default=1.0)
    @api.depends('data_programada','data_programada_fim')
    def _compute_tempo_estimado(self):
        for record in self:
            if record.data_programada_fim  and record.data_programada:
                data_inicio = record.data_programada
                data_fim = record.data_programada_fim
                 # Calcular a diferença de tempo
                diferenca = data_fim - data_inicio #type: ignore
                record.tempo_estimado = diferenca.total_seconds()/3600.0
    
    
    data_programada = fields.Datetime(
        string=u'Data Programada',

        default=fields.Datetime.now(),tracking=True,
        help="Data e hora programada do início da preventiva.",
    )

    data_programada_fim = fields.Datetime(
        string=u'Data Programada fim',
        default=fields.Datetime.now(),tracking=True,
        help="Data e hora programada do fim da preventiva.",
    )

    data_execucao = fields.Datetime(
        string=u'Início Execução',
        default=fields.Datetime.now(),tracking=True,
        help="Data e hora do início da execuão da preventiva.",
    )

    data_execucao_fim = fields.Datetime(
        string=u'Fim da Execução',
        default=fields.Datetime.now(),tracking=True,
        help="Data e hora do fim da execuão da preventiva.",
    )
    
    dias_de_atraso = fields.Integer(
        string=u'Dias de atraso',
        help="Dias de atraso da prevetiva, valores negativos indicam quantos dias para a data programada de execução.",
    )
    
    gerada_os = fields.Boolean(
        string=u'Gerada Os',tracking=True,
        help="Indica ordem de serviço gerada.",
    )
    os_id = fields.Many2one(
        string="Ordem de serviço",
        comodel_name="engc.os",
        ondelete="set null",
        help="Ordem de serviço referente a preventiva.",tracking=True,
        company_dependent=True
    )
    preventiva_executada = fields.Boolean(
        string=u'Preventiva executada?',tracking=True,
        help="Indica que preventiva foi executada.",
    )
    
    color = fields.Char(string='Color', compute='_compute_color', store=True)

    @api.depends('state')
    def _compute_color(self):
        for record in self:
            # Substitua esta lógica pela lógica que define a cor com base no estado.
            # Neste exemplo, estamos gerando cores aleatórias.
            color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            record.color = color
            
    
    @api.onchange('data_programada')
    def _onchange_data_programada(self):
        tempo = timedelta(hours=1)
        tempo_estimado = timedelta(hours=self.tempo_estimado) 
        if tempo_estimado.total_seconds() > 3600:
            tempo = tempo_estimado
        self.data_programada_fim = self.data_programada + tempo
    
    @api.onchange('data_programada_fim')
    def _onchange_data_programada_fim(self):
        tempo: timedelta = self.data_programada_fim - self.data_programada
        if tempo.total_seconds() < 3600:
            tempo = timedelta(hours=1)
            self.data_programada_fim = self.data_programada + tempo
        self.tempo_estimado = tempo.total_seconds()/3600
    
    @api.onchange('tempo_estimado')
    def _onchange_tempo_estimado(self):
        if self.tempo_estimado < 1:
            self.tempo_estimado = 1
        
        tempo_estimado = timedelta(hours=self.tempo_estimado)
        self.data_programada_fim = self.data_programada + tempo_estimado
        
         
    
    @api.onchange('gerada_os')
    def _onchange_gerada_os(self):
        self.state = 'programada'
        
    @api.onchange('preventiva_executada')
    def _onchange_preventiva_executada(self):
        self.state = 'done'
    
    @api.model
    def set_executada(self):
        self.state = 'done'
        self.preventiva_executada = True
        
    
    def write(self, vals):
        """
        Sobrescreve write para:
        1) Impedir alteração de data quando a preventiva já está concluída.
        2) Sincronizar a data programada da OS relacionada quando a preventiva
           tiver sua data alterada e já possuir OS gerada.
        """
        for record in self:
            record._check_write_preventiva_concluida(vals)
            record._sync_os_dates_on_preventiva_change(vals)

        result = super(EngcPreventiva, self).write(vals)
        return result

    def _check_write_preventiva_concluida(self, vals):
        """
        Impede alteração de data programada quando a preventiva já está concluída.
        """
        self.ensure_one()
        if not (self.state == 'done' or self.preventiva_executada):
            return
        blocked = []
        if vals.get('data_programada') is not None:
            blocked.append(_('Data programada (início)'))
        if vals.get('data_programada_fim') is not None:
            blocked.append(_('Data programada (fim)'))
        if blocked:
            raise UserError(
                _("Não é permitido alterar a data da preventiva quando ela já está concluída.\n"
                  "Campos bloqueados: %s") % ', '.join(blocked)
            )

    def _sync_os_dates_on_preventiva_change(self, vals):
        """
        Quando a preventiva tem OS gerada e ainda não está concluída,
        atualiza a data programada da OS relacionada ao alterar data da preventiva.
        """
        self.ensure_one()
        if self.preventiva_executada or self.state == 'done':
            return
        if not self.gerada_os or not self.os_id:
            return

        os_vals = {}
        if 'data_programada' in vals and vals['data_programada'] is not None:
            os_vals['date_scheduled'] = vals['data_programada']
        if 'tempo_estimado' in vals and vals.get('tempo_estimado') is not None:
            os_vals['maintenance_duration'] = vals['tempo_estimado']

        if os_vals:
            self.os_id.write(os_vals)
            _logger.info(
                "OS %s (ID: %s) atualizada com data programada da preventiva %s (ID: %s)",
                self.os_id.name, self.os_id.id, self.name, self.id
            )
    
    
    
    def action_gera_os(self):
        
        _logger.info("gerando os!!!")
        _logger.debug(self)
        if not self.gerada_os:
            os = self.gera_os()
             
        else:
                _logger.info("Os já gerada!!!")
                #if os.id:
                msg = "A Ordem de serviço já foi gerada!!!."
                message_id = self.env['engc.preventive.message.wizard'].create({'message': _(msg)})
                return {
                        'name': _('Aviso!!'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'engc.preventive.message.wizard',
                        'res_id': message_id.id,
                        'target': 'new'
                    }
                return True
        
        return False
    
    #TODO
    # Colocar serviço de manutenção preventiva default do contrato na service.line da Ordem de serviço
    
    def gera_os(self):
        """
        Gera uma ordem de serviço automaticamente para a preventiva.
        
        Returns:
            recordset: Ordem de serviço criada.
            
        Raises:
            ValidationError: Se faltarem dados necessários para criar a OS.
        """
        rec = self
        self.ensure_one()
        
        _logger.info("Gerando OS para preventiva: %s", rec.name)
        
        # Validações antes de criar a OS
        if not rec.equipment:
            raise ValidationError(
                _('⚠️ Não é possível gerar OS: Equipamento não informado na preventiva %s.') % rec.name
            )
        
        if not rec.data_programada:
            raise ValidationError(
                _('⚠️ Não é possível gerar OS: Data programada não informada na preventiva %s.') % rec.name
            )
        
        # Busca o plano de manutenção: primeiro na preventiva, depois no equipamento, depois na categoria
        maintenance_plan = rec.maintenance_plan
        if not maintenance_plan and rec.equipment:
            # Usa o método do equipamento que busca no equipamento ou na categoria
            maintenance_plan = rec.equipment.get_maintenance_plan()
        
        if not maintenance_plan:
            raise ValidationError(
                _('⚠️ Não é possível gerar OS: Plano de manutenção não encontrado.\n'
                  'Verifique se o plano está configurado na preventiva, no equipamento %s ou na sua categoria.') % 
                (rec.equipment.name if rec.equipment else 'N/A')
            )
        
        _logger.info("Plano de manutenção encontrado: %s", maintenance_plan.name)
        
        # Prepara listas de instruções e periodicidades
        instructions_list = []
        periodicity_list = []
        
        for instruction in maintenance_plan.instrucion_ids:
            _logger.debug("INSTRUÇÃO: %s", instruction.name)
            instructions_list.append(instruction.id)
        
        periodicity_list = maintenance_plan.periodicity_ids.mapped('id')
        
        if not periodicity_list:
            raise ValidationError(
                _('⚠️ Não é possível gerar OS: Plano de manutenção não possui periodicidades cadastradas.')
            )
        
        # Prepara dados para criação da OS
        who_executor = 'own'
        current_datetime = fields.Datetime.now()
        
        # A data de requisição deve ser sempre menor ou igual à data programada
        # Se a data programada for no futuro, usa a data atual
        # Se a data programada for no passado ou hoje, usa a data programada
        if rec.data_programada >= current_datetime:
            date_request = current_datetime
        else:
            date_request = rec.data_programada
        
        description = 'Manutenção Preventiva referente ao mês ' + rec.data_programada.strftime('%m/%Y')
        
        # Prepara valores para criação da OS
        os_vals = {
            'origin': rec.name,
            'maintenance_type': 'preventive',
            'solicitante': 'Automático',
            'problem_description': description,
            'who_executor': who_executor,
            'periodicity_ids': [(6, 0, periodicity_list)],
            'equipment_id': rec.equipment.id,
            'date_request': date_request,
            'date_scheduled': rec.data_programada,
            'date_execution': rec.data_programada,
            'state': 'execution_ready',
            'company_id': rec.company_id.id if rec.company_id else False,
        }
        
        # Adiciona cliente se existir
        if rec.client:
            os_vals['client_id'] = rec.client.id
        
        # Adiciona técnico se existir
        if rec.tecnico:
            os_vals['tecnico_id'] = rec.tecnico.id
            
        # Cria a ordem de serviço
        try:
            os = self.env['engc.os'].create(os_vals)
            _logger.info("OS criada com sucesso: %s (ID: %s) para preventiva %s", os.name, os.id, rec.name)
            
            # IMPORTANTE: Atualiza a preventiva para marcar que a OS foi gerada
            # Atualiza gerada_os=True e os_id com o ID da OS gerada
            rec.write({
                'gerada_os': True,
                'state': 'programada',
                'os_id': os.id
            })
            
            # Força flush para garantir que a atualização foi persistida no banco
            self.env.flush_all()
            
            # Invalida o cache para garantir que os dados estão atualizados
            rec.invalidate_recordset(['gerada_os', 'os_id', 'state'])
            
            # Log detalhado da atualização
            _logger.info("Preventiva %s (ID: %s) atualizada com sucesso:", rec.name, rec.id)
            _logger.info("  - gerada_os: %s", rec.gerada_os)
            _logger.info("  - os_id: %s (OS nº: %s)", rec.os_id.id if rec.os_id else None, rec.os_id.name if rec.os_id else None)
            _logger.info("  - state: %s", rec.state)
            
            return os
            
        except Exception as e:
            _logger.error("Erro ao criar OS para preventiva %s: %s", rec.name, str(e))
            raise ValidationError(
                _('⚠️ Erro ao gerar OS para preventiva %s:\n%s') % (rec.name, str(e))
            )
    
    
    def set_preventiva_atrasada(self):
        if not self.preventiva_executada:
            self.state = 'atrasada'
    
    
    def envia_email_aviso_preventiva(self,tipo='aviso') :
        _logger.info("Email de Preventivas.. ")
        _logger.info(self)
        for preventiva in self:
            if tipo == 'aviso':
                _logger.info("Email de aviso de Preventivas.. ")
                #template_client_id = self.env.ref('engc.preventive.mail_aviso_preventiva_cliente')
                #template_tecnico_id = self.env.ref('engc.preventive.mail_aviso_preventiva_tecnico')
             
            if tipo == 'atraso':
                _logger.info("Email de aviso de atraso de Preventivas.. ")
                #template_client_id = self.env.ref('engc.preventive.mail_aviso_atraso_preventiva_cliente')
                #template_tecnico_id = self.env.ref('engc.preventive.mail_aviso_atraso_preventiva_tecnico')
                
            _logger.info("Eviando email para tecnico: ")
            #preventiva.message_post_with_template( template_tecnico_id.id)
            _logger.info("Eviando email para cliente: ")
            #preventiva.message_post_with_template( template_client_id.id)
            
           
    
    def aviso_preventiva(self):
        hoje = fields.Date.today()
        dias_aviso_preventiva = 2
       # dia_procura_inicio = hoje + timedelta(days=dias_aviso_preventiva)
       # dia_procura_fim
        res = self.env['engc.preventive'].search(
            [('gerada_os', '=', True),
             ('data_programada', '>=', hoje + timedelta(days=0,hours=0)),('data_programada', '<=', hoje + timedelta(days=dias_aviso_preventiva,hours=0))])
        _logger.info("Aviso de Preventivas.. ")
        _logger.info(res)
        
        res.envia_email_aviso_preventiva()
        
    
    def aviso_preventiva_atrasada(self):
        _logger.info("entrou no aviso de preventiva atrasada...")
        hoje = fields.Datetime.now()
        _logger.info("procurando preventiva atrasada...")
       # dia_procura_inicio = hoje + timedelta(days=dias_aviso_preventiva)
       # dia_procura_fim
        res = self.env['engc.preventive'].search(
            [('gerada_os', '=', True),('preventiva_executada','=',False),
             ('data_programada', '<', hoje)])
        
        _logger.info("Preventivas atrasadas...")
        for r in res:
            _logger.info("Preventiva %s",r.name)
        _logger.info(res)
        res.envia_email_aviso_preventiva('atraso')
        
    
    def calc_dias_de_atraso(self):
        p=self
        for p in self:
            umdia = (3600*24)  
            # res = []
            #for p in self:
            if p.preventiva_executada:
                _logger.debug("Preventiva %s Executada", p.name)
                dias =  datetime.now() - p.data_execucao
            else:
                _logger.debug("Preventiva %s não Executada", p.name)
                dias =  datetime.now() - p.data_programada
            res = dias.total_seconds()
            res = res/umdia
            _logger.debug("%s dias de atraso float da preventica %s", res, p.name)
            p.dias_de_atraso = int(res)
            if p.dias_de_atraso > 0:
                p.state = 'atrasada'
        
            
        
    
    # *************************
    #  CRON  gera OS e verifica atrasos de preventiva
    #
    # *************************
    
    def cron_agenda_preventiva(self,dias_antecipa_gera_os = 5, dias_avisa_preventica = 2):
        dias_antecipa_gera_os = dias_antecipa_gera_os
        dias_avisa_prev = dias_avisa_preventica
        _logger.info("Entrou no agendamento da preventiva...")
        hoje = fields.Date.today()
        
        res = self.env['engc.preventive'].search(
            [('gerada_os', '=', False), ('data_programada', '>=', hoje),('data_programada', '<=', hoje + timedelta(days=dias_antecipa_gera_os))])
        _logger.debug(res)

        for r in res:
            os = r.gera_os()
        _logger.info("chamando aviso de preventiva...")
        #aviso prévio de vencimento de preventivas
        self.aviso_preventiva()
                
        _logger.info("calculando dias de atraso de preventiva...")
        #atualizando dias de atraso/que faltam das preventivas
        #valores negativos dias que faltam para preventiva
        #valores positivos dias de atraso
        res = self.env['engc.preventive'].search([('preventiva_executada', '=', False)])
        res.calc_dias_de_atraso()
        
            
        
        _logger.info("chamando aviso de atraso de preventiva...")        
        #aviso de manutenção preventiva atrasada
        self.aviso_preventiva_atrasada()
    
    @api.model
    def cron_gera_os_preventivas_7_dias(self):
        """
        Ação agendada que verifica preventivas programadas em até 7 dias
        e gera as OS automaticamente.
        Executa diariamente às 02:00 da manhã.
        """
        _logger.info("Iniciando geração automática de OS para preventivas programadas em até 7 dias...")
        hoje = fields.Date.today()
        data_limite = hoje + timedelta(days=7)
        
        # Busca preventivas programadas que ainda não tiveram OS gerada
        # Nota: state pode ser 'draft' ou outros estados, mas não 'programada' (que é setado após gerar OS)
        preventivas = self.env['engc.preventive'].search([
            ('gerada_os', '=', False),
            ('data_programada', '>=', hoje),
            ('data_programada', '<=', data_limite),
            ('state', 'in', ['draft', 'reagendada']),  # Estados válidos antes de gerar OS
        ])
        
        _logger.info(f"Encontradas {len(preventivas)} preventivas para gerar OS")
        
        os_geradas = 0
        erros = 0
        
        for preventiva in preventivas:
            try:
                if not preventiva.gerada_os:
                    _logger.info(f"Gerando OS para preventiva {preventiva.name} (ID: {preventiva.id})")
                    os = preventiva.gera_os()
                    if os:
                        # Força flush para garantir que a atualização foi persistida
                        self.env.flush_all()
                        
                        # Recarrega o registro para garantir que os dados estão atualizados
                        preventiva.invalidate_recordset(['gerada_os', 'os_id', 'state'])
                        
                        # Valida se os campos foram atualizados corretamente
                        if preventiva.gerada_os and preventiva.os_id:
                            os_geradas += 1
                            _logger.info(f"✓ OS gerada com sucesso para preventiva {preventiva.name} (ID: {preventiva.id}):")
                            _logger.info(f"  - OS nº: {preventiva.os_id.name}")
                            _logger.info(f"  - Equipamento: {preventiva.equipment.name if preventiva.equipment else 'N/A'}")
                            _logger.info(f"  - gerada_os: {preventiva.gerada_os}")
                            _logger.info(f"  - os_id: {preventiva.os_id.id}")
                            _logger.info(f"  - state: {preventiva.state}")
                        else:
                            erros += 1
                            _logger.error(f"✗ Erro: OS criada mas campos não foram atualizados na preventiva {preventiva.name} (ID: {preventiva.id})")
                            _logger.error(f"  - gerada_os: {preventiva.gerada_os} (esperado: True)")
                            _logger.error(f"  - os_id: {preventiva.os_id.id if preventiva.os_id else None} (esperado: {os.id if os else None})")
                            _logger.error(f"  - state: {preventiva.state} (esperado: 'programada')")
                    else:
                        erros += 1
                        _logger.error(f"✗ Erro: gera_os() retornou None para preventiva {preventiva.name}")
            except Exception as e:
                erros += 1
                _logger.error(f"✗ Erro ao gerar OS para preventiva {preventiva.name} (ID: {preventiva.id}): {str(e)}")
                import traceback
                _logger.error(traceback.format_exc())
        
        _logger.info(f"Processo concluído: {os_geradas} OS geradas, {erros} erros")
        
        # Atualiza o status das preventivas para verificar se já estão atrasadas
        _logger.info("Iniciando atualização de status das preventivas (verificação de atrasos)...")
        preventivas_nao_executadas = self.env['engc.preventive'].search([
            ('preventiva_executada', '=', False)
        ])
        
        if preventivas_nao_executadas:
            _logger.info(f"Verificando {len(preventivas_nao_executadas)} preventivas não executadas para atualizar status de atraso...")
            preventivas_nao_executadas.calc_dias_de_atraso()
            
            # Conta quantas preventivas foram marcadas como atrasadas
            preventivas_atrasadas = self.env['engc.preventive'].search([
                ('preventiva_executada', '=', False),
                ('state', '=', 'atrasada')
            ])
            _logger.info(f"Atualização concluída: {len(preventivas_atrasadas)} preventivas marcadas como atrasadas")
        else:
            _logger.info("Nenhuma preventiva não executada encontrada para verificação de atraso")
        
        return True


class dgtPreventivaMessageWizard(models.TransientModel):
    _name = 'engc.preventive.message.wizard'
    _description = u'Model para menus Popups de confirmação de ações'
    

    message = fields.Text('Message', required=True)

    
    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}       


class CronogramaPreventivaWeekday(models.Model):
    """Modelo para representar os dias da semana permitidos"""
    _name = 'engc.preventive.cronograma.weekday'
    _description = 'Dia da Semana para Cronograma'
    _order = 'sequence'
    
    name = fields.Char(string='Nome', required=True)
    weekday_number = fields.Integer(string='Número do Dia', required=True, help='0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo')
    sequence = fields.Integer(string='Sequência', default=10)


class CronogramaPreventiva(models.Model):
    _name = 'engc.preventive.cronograma'
    _description = u'Cronogramas de preventivas'
    _check_company_auto = True
    _rec_name = 'name'
    _order = 'create_date DESC'
    
    STATE_SELECTION = [
		('draft', 'nova'),
		('cancel', 'Cancelada'),
		('done', 'Concluída'),
	]
    Diasemana = ['S','T','Q',
                'Q','S','S','D']
    meses_nome=['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
           'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    
    name = fields.Char(
        string=u'Name',
        required=True,
        default=lambda self: _('New'),
        copy=False
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    state = fields.Selection(
        string="Status",
        selection=STATE_SELECTION,
    )
    cal = calendar.Calendar()
    

#
# funcão de criação do cronograma
#
    @api.model
    def default_get(self, fields_list):
        """Define valores padrão ao criar um novo cronograma"""
        res = super(CronogramaPreventiva, self).default_get(fields_list)
        
        # Define dias da semana padrão: Segunda a Sexta (0, 1, 2, 3, 4)
        if 'allowed_weekdays_ids' in fields_list:
            weekday_ids = self.env['engc.preventive.cronograma.weekday'].search([
                ('weekday_number', 'in', [0, 1, 2, 3, 4])
            ]).ids
            if weekday_ids:
                res['allowed_weekdays_ids'] = [(6, 0, weekday_ids)]
        
        # Define horários padrão
        if 'morning_start_time' in fields_list and 'morning_start_time' not in res:
            res['morning_start_time'] = '08:00'
        if 'morning_end_time' in fields_list and 'morning_end_time' not in res:
            res['morning_end_time'] = '12:00'
        if 'afternoon_start_time' in fields_list and 'afternoon_start_time' not in res:
            res['afternoon_start_time'] = '14:00'
        if 'afternoon_end_time' in fields_list and 'afternoon_end_time' not in res:
            res['afternoon_end_time'] = '18:00'
        
        return res
    
    @api.model
    def create(self, vals_list):
        """Salva ou atualiza os dados no banco de dados"""
        if vals_list.get('name', _('New')) == _('New'):
            if 'company_id' in vals_list:
                vals_list['name'] = self.env['ir.sequence'].with_context(
                    force_company=vals_list['company_id']).next_by_code('engc.preventive.cronograma') or _('New')
            else:
                vals_list['name'] = self.env['ir.sequence'].next_by_code(
                    'engc.preventive.cronograma') or _('New')
        
        # Se não foram especificados dias da semana, define padrão: Segunda a Sexta
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        for vals in vals_list:
            if 'allowed_weekdays_ids' not in vals or not vals.get('allowed_weekdays_ids'):
                weekday_ids = self.env['engc.preventive.cronograma.weekday'].search([
                    ('weekday_number', 'in', [0, 1, 2, 3, 4])
                ]).ids
                if weekday_ids:
                    vals['allowed_weekdays_ids'] = [(6, 0, weekday_ids)]
            
            # Define horários padrão se não foram especificados
            if 'morning_start_time' not in vals or not vals.get('morning_start_time'):
                vals['morning_start_time'] = '08:00'
            if 'morning_end_time' not in vals or not vals.get('morning_end_time'):
                vals['morning_end_time'] = '12:00'
            if 'afternoon_start_time' not in vals or not vals.get('afternoon_start_time'):
                vals['afternoon_start_time'] = '14:00'
            if 'afternoon_end_time' not in vals or not vals.get('afternoon_end_time'):
                vals['afternoon_end_time'] = '18:00'

        result = super(CronogramaPreventiva, self).create(vals_list)
        return result
    
        
    description = fields.Text(
        required=True, help="Descreva o cronograma com nome de cliente se faz parte de algum contrato etc...")
    equipments = fields.Many2many(
        'engc.equipment', string='Equipamentos', required=True, help="Insira os equipamentos que farão parte deste cronograma"
    )
    date_start = fields.Date(
        string="Data de início do cronograma", help="Data de início do cronograma")
    date_stop = fields.Date(
        string="Data de fim do cronograma", help="Data de fim do cronograma")
    tecnicos = fields.Many2many(
		'hr.employee',	
		string = 'Técnicos')
    
    @api.constrains('date_start', 'date_stop')
    def _check_date_range(self):
        """Valida que a data de início não seja maior que a data de fim"""
        for record in self:
            if record.date_start and record.date_stop:
                if record.date_start > record.date_stop:
                    raise ValidationError(
                        _('A data de início do cronograma não pode ser maior que a data de fim.')
                    )
    
    allowed_weekdays_ids = fields.Many2many(
        'engc.preventive.cronograma.weekday',
        'cronograma_weekday_rel',
        'cronograma_id',
        'weekday_id',
        string='Dias da Semana Permitidos',
        help='Selecione os dias da semana em que as preventivas podem ser agendadas. Deixe vazio para permitir todos os dias.',
    )
    
    # Horários de trabalho
    morning_start_time = fields.Char(
        string='Horário Início Manhã',
        default='08:00',
        help='Horário de início do período da manhã (formato HH:MM)'
    )
    morning_end_time = fields.Char(
        string='Horário Fim Manhã',
        default='12:00',
        help='Horário de fim do período da manhã (formato HH:MM)'
    )
    afternoon_start_time = fields.Char(
        string='Horário Início Tarde',
        default='14:00',
        help='Horário de início do período da tarde (formato HH:MM)'
    )
    afternoon_end_time = fields.Char(
        string='Horário Fim Tarde',
        default='18:00',
        help='Horário de fim do período da tarde (formato HH:MM)'
    )
    
    #TODO
    # Pegar o ano do cronograma
    
    ''' Usado no report_cronograma_preventiva_template da impressao do cronograma
        Retorna todas as preventivas de um dado ano e mes
    
    '''
    
    def report_get_preventivas(self, ano=2021,mes=0):        
 
        _logger.debug("GET PREVENTIVAS")
        _logger.debug("ANO")
        _logger.debug(ano)
        _logger.debug("MES")
        _logger.debug(mes)
        
        first_day =datetime(ano,mes,1,0,0,0,0).strftime("%Y-%m-%d %I:%M:%S")
        last_day = datetime(ano, mes, monthrange(ano, mes)[1], 23, 59, 59, 0).strftime("%Y-%m-%d %I:%M:%S")
        
        res = self.env['engc.preventive'].search([(
            'cronograma', '=', self.id),
            ('data_programada', '>=', first_day),
            ('data_programada', '<', last_day)],
            offset=0,
            limit=None,
            order='data_programada ASC',
            count=False)

        _logger.debug(res)
        return res
   
   
    ''' Usado no report_cronograma_preventiva_template da impressao do cronograma
        Retorna quais os meses que tem preventivas
    
    '''
    def report_get_meses_que_tem_preventivas(self, ano):
        first_day = datetime(ano,1, 1, 0, 0, 0, 0).strftime("%Y-%m-%d %I:%M:%S")
        last_day = datetime(ano,12,monthrange(ano,12)[1],23,59,59,0).strftime("%Y-%m-%d %I:%M:%S")
        res = self.env['engc.preventive'].search([(
            'cronograma', '=', self.id),
            ('data_programada', '>=', first_day),
            ('data_programada', '<', last_day)
            ],
            offset=0,
            limit=None,
            order='data_programada DESC',
            count=False)

        meses_com_preventiva = []
        _logger.debug("Meses com preventiva:")
        for rec in res:
            rec_mes = rec.data_programada.month
            
            meses_com_preventiva = list(set(meses_com_preventiva) | set([rec_mes]))

        _logger.debug(sorted(meses_com_preventiva))
        return sorted(meses_com_preventiva)
   
    ''' Usado no report_cronograma_preventiva_template da impressao do cronograma
    
    '''
    def report_get_calendar(self):
        cal = calendar.Calendar()
        res = cal.yeardayscalendar(2021,1)
        return res

    ''' Usado no report_cronograma_preventiva_template da impressao do cronograma
    
    '''
    def report_get_calendar_mes(self,ano,mes):
        cal = calendar.Calendar()
        res = cal.yeardayscalendar(ano,mes)
        return res
    
    ''' Usado no report_cronograma_preventiva_template da impressao do cronograma
    
    '''
    def report_get_preventivas_date(self,data_programada):
        res = self.env['engc.preventive'].search([(
            'cronograma', '=', self.id),
            ('data_programada', '=', data_programada)],
            offset=0,
            limit=None,
            order='data_programada ASC',
            count=False)
        return res
   
    ''' Usado no report_cronograma_preventiva_template da impressao do cronograma
    
    '''
    def report_get_number_weeks(self,ano, mes):
        res = len(monthcalendar(ano,mes))
        return res
    
    def get_programmed_days_by_equipment_month(self, ano, mes):
        """
        Retorna um dicionário com os dias programados de preventiva por equipamento para um mês específico.
        
        Args:
            ano: ano (int)
            mes: mês (int, 1-12)
            
        Returns:
            dict: {equipment_id: [lista de dias do mês programados]}
        """
        self.ensure_one()
        first_day = datetime(ano, mes, 1, 0, 0, 0, 0)
        last_day = datetime(ano, mes, monthrange(ano, mes)[1], 23, 59, 59, 0)
        
        preventivas = self.env['engc.preventive'].search([
            ('cronograma', '=', self.id),
            ('data_programada', '>=', first_day),
            ('data_programada', '<=', last_day)
        ])
        
        result = {}
        for prev in preventivas:
            if prev.equipment:
                equipment_id = prev.equipment.id
                # Obtém o dia do mês da data programada
                if prev.data_programada:
                    day = prev.data_programada.day
                    
                    if equipment_id not in result:
                        result[equipment_id] = []
                    if day not in result[equipment_id]:
                        result[equipment_id].append(day)
        
        # Ordena os dias para cada equipamento
        for equipment_id in result:
            result[equipment_id].sort()
        
        return result
    
    def get_calendar_month(self, ano, mes):
        """
        Retorna o calendário de um mês específico organizado por semanas.
        
        Args:
            ano: ano (int)
            mes: mês (int, 1-12)
            
        Returns:
            list: lista de semanas, cada semana é uma lista de 7 dias (0 = dia não do mês, 1-31 = dia do mês)
        """
        cal = calendar.Calendar()
        return cal.monthdayscalendar(ano, mes)
    
    def get_calendar_month_filtered(self, ano, mes):
        """
        Retorna o calendário de um mês específico organizado por semanas,
        mas apenas com os dias que pertencem ao mês (remove os zeros).
        Cada semana terá no mínimo 3 colunas. Se tiver menos dias do mês,
        preenche com colunas vazias (None).
        - Na primeira semana: células vazias vêm ANTES dos dias do mês
        - Na última semana: células vazias vêm DEPOIS dos dias do mês
        Também retorna informações sobre os dias da semana para cada dia.
        
        Args:
            ano: ano (int)
            mes: mês (int, 1-12)
            
        Returns:
            list: lista de semanas, cada semana é uma lista de tuplas (dia, dia_semana) ou None
                  onde dia é o número do dia (1-31) e dia_semana é o índice do dia da semana (0-6, 0=Segunda)
                  None representa uma coluna vazia
        """
        cal = calendar.Calendar()
        weeks = cal.monthdayscalendar(ano, mes)
        
        # Dias da semana em português (Segunda=0, Terça=1, Quarta=2, Quinta=3, Sexta=4, Sábado=5, Domingo=6)
        filtered_weeks = []
        
        for week_idx, week in enumerate(weeks):
            filtered_week = []
            for idx, day in enumerate(week):
                if day != 0:  # Apenas dias que pertencem ao mês
                    # idx é o índice do dia da semana (0=Segunda, 6=Domingo)
                    filtered_week.append((day, idx))
            
            # Garante que cada semana tenha no mínimo 3 colunas
            if filtered_week:
                is_first_week = (week_idx == 0)
                is_last_week = (week_idx == len(weeks) - 1)
                
                while len(filtered_week) < 3:
                    if is_first_week:
                        # Na primeira semana: adiciona células vazias no INÍCIO
                        filtered_week.insert(0, None)
                    else:
                        # Nas outras semanas (incluindo a última): adiciona no FINAL
                        filtered_week.append(None)
                
                filtered_weeks.append(filtered_week)
        
        return filtered_weeks
    
    def get_year_from_cronograma(self):
        """
        Retorna o ano do cronograma baseado na data de início.
        """
        self.ensure_one()
        if self.date_start:
            return self.date_start.year
        return datetime.now().year
    
    def _concatenate_days_schedule(self,schedule_for_periodicity_equipment_list):
        concatenate_list ={}
        temporary_schedule = schedule_for_periodicity_equipment_list.copy()

        for k,v in schedule_for_periodicity_equipment_list.items():
            this_schedule = schedule_for_periodicity_equipment_list[k]
            del temporary_schedule[k]
            _logger.info(f"temporary_schedule:{temporary_schedule}")
            _logger.info(f"schedule_for_periodicity_equipment_list:{schedule_for_periodicity_equipment_list}")
            if 'schedule' in this_schedule:
                for schedule_item in this_schedule['schedule']:
                    _logger.info(f"Schedule item:{schedule_item}")
                    start, end = schedule_item
                    if start not in concatenate_list:
                        concatenate_list[start] = {'schedule': schedule_item, 'periodicity': [k]}
                        for periodicity, values in temporary_schedule.items():
                            if schedule_item in temporary_schedule[periodicity]['schedule']:
                                _logger.info(f"Tem no {periodicity}")
                                _logger.info(f"Voce esta no  {k}")
                                periodicity_list =[]
                                #pegando a datahora fim do agendamento do dia
                                conc_start, conc_end = concatenate_list[start]['schedule']
                                _logger.info(f"Como esta concatenate_list[start]['periodicity'] = {concatenate_list[start]['periodicity']} e o k é {k}")                             
                                periodicity_list = concatenate_list[start]['periodicity'] +[periodicity]
                                concatenate_list[start]={'schedule': (start,conc_end + timedelta(hours=1)), 'periodicity': periodicity_list}
                            else:
                                _logger.info(f"Não tem no {periodicity}")
                            
        _logger.info(f"Lista concatenada: {concatenate_list}")
        return concatenate_list
                        
    def _make_preventives(self, concatenate_list):
        user_tz = self.env.user.tz
        local = pytz.timezone(user_tz)

        _logger.info("Montando preventivas para serem adicionadas")
        result = []
        for equipment, value in concatenate_list.items():
            _logger.info(equipment)
            _logger.info(value)
            for k, v in value.items():
                if 'schedule' in v:
                    schedule = v['schedule']
                    periodicity = v['periodicity']
                    _logger.info(schedule)
                    date_start,date_end = schedule
                    #procurando as periodicidades pelo nome
                    periodicity_ids = self.env['engc.maintenance_plan.periodicity'].search([('name','in',periodicity)]).mapped('id')
                    #transformando horario em UTC para colocar no banco
                    date_start = local.localize(date_start).astimezone(pytz.utc).replace(tzinfo=None)
                    date_end = local.localize(date_end).astimezone(pytz.utc).replace(tzinfo=None)
                    dict_prev  =    {
                            "name": str(self.name) + "/" + str(equipment.name),
                            "client": equipment.client_id.id,
                            "equipment": equipment.id,
                            "periodicity_ids": [(6,0,periodicity_ids)],
                            "data_programada": date_start,
                            "data_programada_fim": date_end,
                            "cronograma":self.id,
                            "tecnico": self.tecnicos[0].id,
                        }
                    result.append(dict_prev)
                    
        return result
    def _get_other_appointments(self,concatenate_schedule):
        _logger.info(f"Other_appointments:{concatenate_schedule}")
        other_appointments = []
        for equipment,schedule_equipment in concatenate_schedule.items():
            for day,data in schedule_equipment.items():
                other_appointments.append(data['schedule'])
        return other_appointments
    
#
# funcão de gera cronograma de preventivas
#  para cada equipamento cadastrado no cronograma
#
    
    def action_gera_cronograma(self):
        user_tz = self.env.user.tz
        local = pytz.timezone(user_tz)
        _logger.info(local)
        today = date.today()

        if self.date_start > self.date_stop:
            raise UserError(
                _("Data de início maior que data de fim da geração do cronograma. Não é possivel gerar cronograma"))
        if self.date_stop < today:
            raise UserError(
                _("Data de fim do cronograma menor que a data atual. Não é possivel gerar cronograma"))

        # data de inicio e fim de cronograma
        start_date = self.date_start.strftime('%Y-%m-%d')
        start_year = int(self.date_start.strftime('%Y'))
        end_date = self.date_stop.strftime('%Y-%m-%d')
        end_year = int(self.date_stop.strftime('%Y'))
        
        #pegando apenas o ano das datas de inicio e fim
        years = set()
        years.add(start_year)
        years.add(end_year)
        years_list = list(years)
        
        #configurando os periodos de preventiva hora de inicio e fim de cada 
        # Converte strings 'HH:MM' para inteiros (horas)
        def time_str_to_hour(time_str):
            """Converte string 'HH:MM' para inteiro de horas"""
            if not time_str:
                return None
            try:
                # Remove espaços e extrai a parte das horas (antes do ':')
                time_str = str(time_str).strip()
                hour = int(time_str.split(':')[0])
                return hour
            except (ValueError, IndexError, AttributeError) as e:
                _logger.warning(f"Erro ao converter horário '{time_str}': {e}")
                return None
        
        # Usa os horários configurados no cronograma ou valores padrão
        morning_start = time_str_to_hour(self.morning_start_time) or 8
        morning_end = time_str_to_hour(self.morning_end_time) or 12
        afternoon_start = time_str_to_hour(self.afternoon_start_time) or 14
        afternoon_end = time_str_to_hour(self.afternoon_end_time) or 18
        
        _logger.info(f"Horários configurados - Manhã: {morning_start}:00 às {morning_end}:00 | Tarde: {afternoon_start}:00 às {afternoon_end}:00")

        # pegando feriados do periodo
        
        br_holidays = holidays.country_holidays(country="BR",subdiv='MA', years=years_list).items()
        holidays_list = list(map(lambda x: x[0].strftime('%Y-%m-%d'), br_holidays))
    
        # hora_ini_dia = time(8,0,0, tzinfo=local) # hora de início do dia
        # hora_fim_dia = time(18,0,0, tzinfo=local) # hora de fim do dia

        # today_time = datetime.combine(today,hora_ini_dia) #começa sempre 8 da manhã brazil

        #verificando se todos os equipamentos tem plano de manutenção cadastrado
        msg_error_maintenance_plan = []
        concatenate_schedule={}
        maintenance_plan_dict ={}
        for equipment in self.equipments:
            maintenance_plan_dict[equipment] = equipment.maintenance_plan if equipment.maintenance_plan else equipment.category_id.maintenance_plan
            if not maintenance_plan_dict[equipment]:
                msg_error_maintenance_plan.append(f"Equipamento: {equipment.name}")
            
        if msg_error_maintenance_plan:
            raise ValidationError(
                    _("Os seguintes equipamentos não tem plano de manutenção cadastrados:\n\n"+ 
                      "\n".join(msg_error_maintenance_plan) +
                      "\n\nCadastre um plano de manutenção para gerar preventivas dos cronogramas!"))   
        other_appointments = []
        schedule_periodicity_equipment_list = []
        for equipment in self.equipments:
            
            maintenance_plan = maintenance_plan_dict[equipment]
            periodicity_list = maintenance_plan.periodicity_ids
            divisores_periodicity_list = calcular_divisores(periodicity_list.mapped('frequency'))
            _logger.info(divisores_periodicity_list)
            _logger.info(periodicity_list)
            time_duration_list = maintenance_plan.get_time_duration(periodicitys=periodicity_list)
            time_duration_list = time_duration_list[0]
            # time_duration_list = sorted(time_duration_list, key=lambda x: x.) 
            _logger.info(time_duration_list)
            schedule_for_periodicity_equipment = {}
            for index,periodicity in enumerate(periodicity_list):
                _logger.info(f"Gerando {periodicity.name}")
                
                other_appointments = self._get_other_appointments(concatenate_schedule)
                # Converte os dias da semana permitidos para lista de inteiros
                allowed_weekdays_list = None
                if self.allowed_weekdays_ids:
                    allowed_weekdays_list = self.allowed_weekdays_ids.mapped('weekday_number')
                
                schedule = SchedulePreventive(
                            "Preventiva",
                            preventive_duration_hours=int(math.ceil(time_duration_list[periodicity.name])) if int(math.ceil(time_duration_list[periodicity.name])) else 1,
                            periodicity_days = periodicity.frequency,
                            start_date=start_date,
                            end_date=end_date,
                            holidays=holidays_list,
                            other_appointments=other_appointments,
                            time_increment_minutes=15,
                            morning_start=morning_start,
                            morning_end=morning_end,
                            afternoon_start=afternoon_start,
                            afternoon_end=afternoon_end,
                            allowed_weekdays=allowed_weekdays_list)
                schedule.generate_schedule() 
                schedule_for_periodicity_equipment[periodicity.name] = {
                    'schedule' : schedule.get_schedule(),
                    'time_duration': time_duration_list[periodicity.name]
                }
            _logger.info(schedule_for_periodicity_equipment)

            #concatenando dias periodicidades que caeem em dias iguais
            concatenate_schedule[equipment] = self._concatenate_days_schedule(schedule_for_periodicity_equipment)
        
        preventives_maked = self._make_preventives(concatenate_schedule)
        _logger.info(preventives_maked)
        
        # inserindo preventivas
        self.env['engc.preventive'].create(preventives_maked)
           
           
                

            #if not maintenance_plan:
                

                   # verificando se existe alguma preventiva já programada para esse equipamento
                   # str_data_prog = data_programada.strftime("%d/%m/%Y")
                   
                    # prev = self.env['engc.preventive'].search([
                    #     ['data_programada','>=',da],['data_programada','<=',dp],
                    #     ['equipment','=',equipment.id],
                    #     ['cronograma','=',self.id]])
                    # _logger.info("Preventiva igual, mano:")
                    # _logger.info(prev)
                    # if prev:
                    #     _logger.info("jA TEM PREVENTIVA")
                    #     _logger.info(prev)
                    #     prev.write({
                    #         "name": str(self.name) + "/" + str(equipment.name),
                    #         "client": equipment.client_id.id,
                    #         "equipment": equipment.id,
                    #         "grupo_id": [(4,grupo_instruction.id)],
                    #         "data_programada": data_programada.replace(hour=hora_ini_dia.hour,minute=hora_ini_dia.minute, tzinfo=timezone.utc),
                    #         "data_programada_fim": data_programada.replace(hour=15,minute=0, tzinfo=timezone.utc),
                    #         "cronograma":self.id,
                    #         "tecnico": self.tecnicos[0].id,
                    #     })
                    # else:   
                    #     self.env['engc.preventive'].create({
                    #         "name": str(self.name) + "/" + str(equipment.name),
                    #         "client": equipment.client_id.id,
                    #         "equipment": equipment.id,
                    #         "grupo_id": [(4,grupo_instruction.id)],
                    #         "data_programada": data_programada.replace(hour=hora_ini_dia.hour,minute=hora_ini_dia.minute, tzinfo=timezone.utc),
                    #         "data_programada_fim": data_programada.replace(hour=15,minute=0, tzinfo=timezone.utc),
                    #         "cronograma":self.id,
                    #         "tecnico": self.tecnicos[0].id,

                    #     })
            # chama adiciona_preventiva(self,equipments, data_programada, grupo_instrucao)