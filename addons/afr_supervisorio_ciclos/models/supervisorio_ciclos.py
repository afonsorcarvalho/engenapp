from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging
from ..fita_digital.data_object.dataobject_fita_digital import DataObjectFitaDigital

from ..fita_digital.reader_fita_digital.reader_fita_digital_afr13 import ReaderFitaDigitalAfr13
import re
import os
_logger = logging.getLogger(__name__)
import sys
import base64

class SupervisorioCiclos(models.Model):
    _name = 'afr.supervisorio.ciclos'
    _description = 'Supervisório de Ciclos de Esterilização, Lavagem e Desinfecção'
    _order = 'start_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    directory_path = "/var/lib/odoo/filestore/odoo-steriliza/ciclos/"
   
    # Campos básicos
    name = fields.Char(string='Ciclo', required=True, tracking=True)
    equipment_id = fields.Many2one('engc.equipment', string='Equipamento', required=True, tracking=True)
    equipment_nickname = fields.Char(related='equipment_id.apelido', string='Apelido do Equipamento', store=True)
    equipment_category_id = fields.Many2one(related='equipment_id.category_id', string='Categoria do Equipamento', store=True)
    cycle_type_id = fields.Many2one('afr.cycle.type', string='Tipo de Ciclo', required=True,
        domain="[('active', '=', True)]", tracking=True)
    cycle_features_id = fields.Many2one('afr.cycle.features', string='Ciclo Selecionado',
         tracking=True, domain="[('cycle_type_id', '=', cycle_type_id)]")   

    @api.onchange("cycle_features_id")
    def _onchange_cycle_features_id(self):
        vals = {}
    
        
        vals['duration_planned'] = self.cycle_features_id.tempo_estimado
    
    
    
        return vals
   
    # Campos de data/hora
    start_date = fields.Datetime(string='Data Início', default=fields.Datetime.now, tracking=True)
    end_date = fields.Datetime(string='Data Fim')
    duration = fields.Float(string='Duração (h)', compute='_compute_duration', store=True)
    
    # Status do ciclo
    state = fields.Selection([
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
        ('erro', 'Erro'),
        ('abortado', 'Abortado'),
        ('aguardando', 'Aguardando'),
        ('pausado', 'Pausado'),
    ], string='Status', default='aguardando', tracking=True)


    # Campos adicionais
    notes = fields.Text(string='Observações', tracking=True)
    operator_id = fields.Many2one('res.users', string='Operador', 
        default=lambda self: self.env.user, tracking=True)
    
    # Campos de arquivo
    file_path = fields.Char(
        string='Caminho do Arquivo',
        tracking=True,
        help='Caminho completo do arquivo de ciclo'
    )
    #download_url = fields.Char(string='URL de Download', compute='_compute_pdf_link_html')
    download_url  = fields.Html(string='URL de Download', compute='_compute_pdf_link_html')
    
    
    @api.depends('file_path')
    def _compute_pdf_link_html(self):
        for rec in self:
            if rec.file_path:
                rec.download_url = (
                    f'<a href="/web/content/download_file_txt_to_pdf/{rec.id}" target="_blank">'
                    f'<i class="fa fa-file-pdf-o" style="color:red"></i> PDF'
                    '</a>&nbsp;&nbsp;'
                    f'<a href="/web/content/download_file_txt/{rec.id}" target="_blank">'
                    f'<i class="fa fa-file-text-o" style="color:red"></i> TXT'
                    '</a>'
                )
            else:
                rec.download_url = ''
    # @api.depends('file_path')
    # def _compute_download_url(self):
    #     for record in self:
    #         if record.file_path:
    #             record.download_url = f'/web/content/download_file_txt_to_pdf/{record.id}'
    #         else:
    #             record.download_url = False

    cycle_statistics_txt = fields.Text(
        string='Estatísticas do Ciclo',
        compute='_compute_cycle_statistics_txt',
        store=False,
        help='Estatísticas do ciclo'
    )
    cycle_statistics_data = fields.Json(
        string='Dados das Estatísticas',
        compute='_compute_cycle_statistics_data',
        store=False,
        help='Dados estruturados das estatísticas do ciclo'
    )
    cycle_txt = fields.Text(
        string='Conteúdo do Arquivo',
        compute='_compute_cycle_txt',
        store=False,
        help='Conteúdo do arquivo de ciclo'
    )
    cycle_txt_filename = fields.Char(
        string='Nome do Arquivo TXT'
    )
    cycle_pdf = fields.Binary(
        string='PDF do Ciclo',
        attachment=True,
        tracking=True
    )
    cycle_pdf_filename = fields.Char(
        string='Nome do Arquivo PDF'
    )
    cycle_graph = fields.Image(
        string='Gráfico do Ciclo',
        compute='compute_cycle_graph', 
        store=False,
        help='Gráfico gerado a partir dos dados do ciclo',
        # Opções disponíveis para o campo Image:
        max_width=1920,  # Largura máxima da imagem
        max_height=1080, # Altura máxima da imagem 
        verify_resolution=True, # Verifica resolução da imagem
        # Widget options:
        # image - Widget padrão para imagens
        # image_url - Para imagens via URL
        # image_preview - Miniatura da 
        # binary - Mostra como arquivo binário
    )
    cycle_graph_filename = fields.Char(
        string='Nome do Arquivo do Gráfico',
        default='cycle_graph.png'
    )
   
    batch_number = fields.Char(string='Número do Lote', tracking=True)
    company_id = fields.Many2one('res.company', string='Empresa', 
        default=lambda self: self.env.company)

    # Campos computados
    state_color = fields.Integer(string='Cor do Status', compute='_compute_state_color')
    is_overdue = fields.Boolean(string='Atrasado', compute='_compute_is_overdue',store=True)
    str_is_overdue = fields.Char(string='Atrasado', compute='_compute_is_overdue')
    duration_planned = fields.Float(string='Duração Prevista (min)', compute='_compute_duration_planned')

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                duration = (record.end_date - record.start_date).total_seconds() / 3600  # Convertendo para horas
                record.duration = round(duration, 2)
            else:
                record.duration = 0.0
   

    @api.depends('state')
    def _compute_state_color(self):
        colors = {
            'aguardando': 4,    # azul
            'em_andamento': 3,  # verde
            'concluido': 7,     # cinza
            'cancelado': 1,     # vermelho
            'erro': 2,          # laranja
            'abortado': 1,      # vermelho
            'pausado': 4,       # azul
        }
        for record in self:
            record.state_color = colors.get(record.state, 0)

    @api.depends('start_date', 'end_date', 'duration_planned')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = False
            record.str_is_overdue = ""

            #verifica se o ciclo está concluido e se a data de fim é maior que a data de inicio
            if record.end_date and record.start_date:
                tempo_decorrido_minutos = (record.end_date - record.start_date).total_seconds()/60
            else:
                tempo_decorrido_minutos = (now - record.start_date).total_seconds()/60
                
            if record.state == 'concluido':
                #verifica se o ciclo está atrasado
                if tempo_decorrido_minutos > record.duration_planned:
                    record.is_overdue = True
                    atraso_minutos = int(tempo_decorrido_minutos - record.duration_planned)
                    record.str_is_overdue = f"Atrasado em {atraso_minutos:02d} minutos"
                    
                if tempo_decorrido_minutos < record.duration_planned:    
                
                    record.is_overdue = False
                    # Calcula a diferença em minutos e converte para inteiro
                    adiantado_minutos = int(record.duration_planned - tempo_decorrido_minutos)
                    record.str_is_overdue = f"{adiantado_minutos:02d} minutos adiantado"
                if tempo_decorrido_minutos == record.duration_planned:
                    record.is_overdue = False
                    record.str_is_overdue = "Pontual"

            if record.start_date and record.state == 'em_andamento':
                tempo_decorrido_minutos = (now - record.start_date).total_seconds()/60
                if tempo_decorrido_minutos > record.duration_planned:               
                    record.is_overdue = True
                    atraso_minutos = int(tempo_decorrido_minutos - record.duration_planned)
                    record.str_is_overdue = f"Atrasado em {atraso_minutos:02d} minutos"
                
                if tempo_decorrido_minutos < record.duration_planned:
                    record.is_overdue = False
                    faltando_minutos = int(record.duration_planned - tempo_decorrido_minutos)
                    record.str_is_overdue = f"Faltando {faltando_minutos:02d} minutos"
                
               
               

    @api.depends('cycle_type_id')
    def _compute_duration_planned(self):
        for record in self:
            # Aqui você pode definir uma duração padrão baseada no tipo de ciclo
            record.duration_planned = record.cycle_features_id.tempo_estimado # valor padrão de 60 minutos

    @api.onchange('equipment_id')
    def _onchange_equipment(self):
        if self.equipment_id:
            self.cycle_type_id = False

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError('A data de início não pode ser posterior à data de fim.')

    def action_start(self):
        self.ensure_one()
        if self.state != 'aguardando':
            raise UserError('Apenas ciclos em aguardo podem ser iniciados.')
        self.write({
            'state': 'em_andamento',
            'start_date': fields.Datetime.now()
        })

    def action_conclude(self):
        self.ensure_one()
        if self.state != 'em_andamento':
            raise UserError('Apenas ciclos em andamento podem ser concluídos.')
        self.write({
            'state': 'concluido',
            'end_date': fields.Datetime.now()
        })

    def action_cancel(self):
        self.ensure_one()
        if self.state in ['concluido', 'cancelado']:
            raise UserError('Este ciclo não pode ser cancelado.')
        self.write({
            'state': 'cancelado',
            'end_date': fields.Datetime.now()
        })

    def action_pause(self):
        self.ensure_one()
        if self.state != 'em_andamento':
            raise UserError('Apenas ciclos em andamento podem ser pausados.')
        self.write({'state': 'pausado'})

    def action_resume(self):
        self.ensure_one()
        if self.state != 'pausado':
            raise UserError('Apenas ciclos pausados podem ser retomados.')
        self.write({'state': 'em_andamento'})
    
    def action_abrir_wizard_ler_diretorio_ciclos(self):
        """
        Abre o wizard para configurar as datas da leitura do diretório de ciclos.
        Funciona tanto no formulário quanto na tree view.
        """
        # Se chamado da tree view (sem registro específico), não usa ensure_one()
        if len(self) == 1:
            self.ensure_one()
            active_id = self.id
            default_equipment_id = self.equipment_id.id if self.equipment_id else False
        else:
            # Chamado da tree view sem seleção específica
            active_id = False
            default_equipment_id = False
        
        # Abre o wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configurar Leitura de Diretório',
            'res_model': 'wizard.ler.diretorio.ciclos',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_id': active_id,
                'default_equipment_id': default_equipment_id,
            }
        }

    def action_atualizar_dados_ciclo_atual(self):
        """
        Atualiza os dados do ciclo atual lendo o arquivo da fita digital.
        """
        self.ensure_one()
        
        # Verifica se o ciclo tem um arquivo associado
        if not self.file_path:
            raise UserError('Este ciclo não possui um arquivo associado para atualização.')
        
        # Verifica se o arquivo existe
        if not os.path.exists(self.file_path):
            raise UserError(f'O arquivo {self.file_path} não foi encontrado no sistema.')
        
        # Verifica se o equipamento está definido
        if not self.equipment_id:
            raise UserError('Este ciclo não possui um equipamento associado.')
        
        try:
            # Cria o objeto arquivo no formato esperado pelo método update_cycle
            arquivo_info = {
                'name': os.path.basename(self.file_path),
                'path': os.path.dirname(self.file_path)
            }
            
            # Chama o método update_cycle para atualizar os dados
            self.update_cycle(arquivo_info, self.equipment_id)
            
            # Força o recálculo dos campos computados
            self._compute_cycle_txt()
            self._compute_cycle_statistics_txt()
            self._compute_cycle_statistics_data()
            self.compute_cycle_graph()
            
            # Força o recálculo de todos os campos computados no registro
            self.invalidate_cache()
            
            # Força a atualização da view atual sem abrir nova janela
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
            
        except Exception as e:
            _logger.error(f"Erro ao atualizar dados do ciclo {self.name}: {str(e)}")
            raise UserError(f'Erro ao atualizar dados do ciclo: {str(e)}')

    def action_ler_diretorio_ciclos(self,equipment_alias=None,equipment_ns=None,equipment_id=None,data_inicial=None,data_final=None):
        #self.ensure_one()
        _logger.info(f"action_ler_diretorio_ciclos equipamento: {equipment_id}")
        if not equipment_id:
            if equipment_alias:
                equipment_id = self.env['engc.equipment'].search([('apelido', '=', equipment_alias)], limit=1)
            if not equipment_id:
                equipment_id = self.env['engc.equipment'].search([('serial_number', '=', equipment_ns)], limit=1)
            if not equipment_id:
                if not self.equipment_id:
                    raise UserError("Nenhum equipamento informado.")
                equipment_id = self.equipment_id
        _logger.info(f"equipment_id: {equipment_id}")
        data_inicial = data_inicial or datetime.now() - timedelta(days=365)
        data_final = data_final or datetime.now()

        lista_arquivos = self.ler_diretorio_ciclos(equipment_id=equipment_id,data_inicial=data_inicial,data_final=data_final)
        _logger.debug(f"lista_arquivos: {lista_arquivos}")

        self.processar_ciclos(lista_arquivos,equipment_id=equipment_id)
  
    def processar_ciclos(self,lista_arquivos,equipment_id=None):

        # equipment_alias = equipment_alias or self.equipment_id.apelido
        # equipment_id = self.env['engc.equipment'].search([('apelido', '=', equipment_alias)], limit=1)
        if not equipment_id:
            raise UserError(f"Equipamento não informado equipment_id=None")
 
        for arquivo in lista_arquivos:
            #verifica se o ciclo já existe
            _logger.debug(f"arquivo: {arquivo}")
            ciclo_name = arquivo['name'].replace('.txt','')
            ciclo = self.env['afr.supervisorio.ciclos'].search([('name', '=', ciclo_name)])
            if ciclo:
                _logger.debug(f"Ciclo {ciclo_name} já existe. Update dados do ciclo")
                if ciclo.state == 'cancelado':
                    _logger.debug(f"Ciclo {ciclo_name} está cancelado. Não será atualizado")
                    continue
                ciclo.update_cycle(arquivo,equipment_id)
                continue
               
            _logger.debug(f"Ciclo {ciclo_name} sendo criado para o equipamento {equipment_id}")
            self.update_cycle(arquivo,equipment_id)


    def _carregar_classe_leitor(self, equipment_id):
            """
            Carrega dinamicamente a classe do leitor de fita baseado no tipo de equipamento.
            
            Args:
                equipment_id: Registro do equipamento contendo a classe do leitor
                
            Returns:
                classe_leitor: Classe do leitor de fita carregada
                
            Exemplo:
                >>> equipment = self.env['engc.equipment'].browse(1)
                >>> classe_leitor = self._carregar_classe_leitor(equipment)
                >>> leitor = classe_leitor('/path/to/file.txt')
                >>> header, body = leitor.read_all()
            """
            try:
                # Obtém o nome da classe do leitor a partir do equipamento
                nome_classe_leitor = equipment_id.cycle_type_id.reader_class_dataobject or 'ReaderFitaDigitalAfr'
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
              
              
                sys.path.append(base_path)
               
                # Importa dinamicamente o módulo que contém a classe
                modulo = __import__(f"fita_digital.reader_fita_digital." +  re.sub(r'(?<!^)(?=[A-Z])', '_', nome_classe_leitor).lower(),fromlist=[nome_classe_leitor])
                _logger.debug(f"modulo: {modulo}")     
                
                # Obtém a classe do módulo
                classe_leitor = getattr(modulo, nome_classe_leitor)
                
                _logger.debug(f"Classe de leitor carregada: {nome_classe_leitor}")
                
            except (ImportError, AttributeError) as e:
                _logger.error(f"Erro ao carregar classe do leitor: {str(e)}. Usando leitor padrão ReaderFitaDigitalAfr13")
                # Em caso de erro, usa o leitor padrão
                classe_leitor = ReaderFitaDigitalAfr13
                
            return classe_leitor

    def update_cycle(self,arquivo,equipment_id):
        header = None
        body = None
        try:
            do = self._get_dataobject(equipment_id=equipment_id,file_path=arquivo['path'] + '/' + arquivo['name'])
            header, body = do.read_all_fita()
        except Exception as e:
            _logger.error(f"Erro ao atualizar ciclo: {str(e)}")
            
        
        #verificando se header e body estão definidos
        if not header or not body:
            _logger.error(f"Header ou body não definidos para o ciclo {arquivo['name']}")
            return
        
        cycle_type_id = self.cycle_type_id if self.id else equipment_id.cycle_type_id
        file_path = os.path.join(arquivo['path'], arquivo['name'])
        pdf_path = file_path.replace('.txt', '.pdf')
        
        # Prepara os valores base
        base_values = {
            'equipment_id': equipment_id.id,
            'cycle_type_id': cycle_type_id.id,
            'file_path': file_path,
            'cycle_txt_filename': arquivo['name'],
           # 'cycle_pdf': base64.b64encode(pdf_content) if pdf_content else False,
            'cycle_pdf_filename': arquivo['name'].replace('.txt', '.pdf'),
            'company_id': equipment_id.company_id.id if equipment_id.company_id else False
        }
        
        # Chamando método dinamicamente do cycle_type_id
        metodo_nome = cycle_type_id.method_name_create_cycle
        if not metodo_nome:
            raise UserError(f"Nome do método para criar dados do ciclo não definido para o tipo de ciclo {cycle_type_id.name}")
        
        if not hasattr(self, metodo_nome):
            raise UserError(f"Método '{metodo_nome}' não encontrado para o tipo de ciclo {cycle_type_id.name}")
        
        update_cycle_method = getattr(self, metodo_nome)
        dados = update_cycle_method(header, body, values=base_values)

        

   
                
    def ler_diretorio_ciclos(self,equipment_alias=None,equipment_ns=None,equipment_id=None,data_inicial='2025-03-23',data_final=None):
        """
        Lê o diretório de ciclos e filtra por data.

        Args:
            equipment_alias (str): Alias do equipamento
            data_inicial (datetime|str): Data inicial para filtro. Se string, deve estar no formato 'YYYY-MM-DD'
            data_final (datetime|str): Data final para filtro. Se string, deve estar no formato 'YYYY-MM-DD'

        Returns:
            list: Lista de arquivos filtrados por data
            
        Exemplo:
            >>> ciclos.ler_diretorio_ciclos('ETO01', '2024-01-01', '2024-01-31')
            [
                {
                    'name': 'ciclo_001.txt',
                    'path': '/ciclos/ETO01',
                    'create_date': datetime(2024,1,15,10,30,0),
                    'change_date': datetime(2024,1,15,11,45,0)
                },
                {
                    'name': 'ciclo_002.txt', 
                    'path': '/ciclos/ETO01',
                    'create_date': datetime(2024,1,16,14,20,0),
                    'change_date': datetime(2024,1,16,15,10,0)
                }
            ]
        """
        # Converte data_inicial para datetime se necessário
        if isinstance(data_inicial, str):
            try:
                data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d')
            except ValueError as e:
                raise UserError(f"Formato de data inicial inválido. Use YYYY-MM-DD: {str(e)}")
                
        # Converte data_final para datetime se necessário    
        if isinstance(data_final, str):
            try:
                data_final = datetime.strptime(data_final, '%Y-%m-%d')
            except ValueError as e:
                raise UserError(f"Formato de data final inválido. Use YYYY-MM-DD: {str(e)}")
        
        if isinstance(equipment_id,int):
            equipment_id = self.env['engc.equipment'].browse(equipment_id)
            if not equipment_id:
                raise UserError(f"Nenhum equipamento encontrado com id = {equipment_id}.")
            
        if not equipment_id:
            #procurar equipamento
            if equipment_alias:
                equipment_id = self.env['engc.equipment'].search([('apelido', '=', equipment_alias)], limit=1)
            elif equipment_ns:
                equipment_id = self.env['engc.equipment'].search([('serial_number', '=', equipment_ns)], limit=1)
                if not equipment_id:
                    raise UserError("Nenhum equipamento informado.")

            

        #Atualizando DataObjectFitaDigital 
        if not equipment_id.cycle_type_id:
            raise UserError(f"Equipamento {equipment_alias} não possui tipo de ciclo definido")
        
        path_ciclo =equipment_id.cycle_type_id.path_ciclo
        if not path_ciclo:
            raise UserError(f"Equipamento {equipment_alias} não possui path_ciclo do tipo de ciclo definido")
        
        #Atualizando DataObjectFitaDigital 
        do = self._get_dataobject(equipment_id=equipment_id)
        
             
        
        lista_arquivos = do.ler_diretorio_ciclos(directory_path=equipment_id.cycle_path,extension_file_search=None,data_inicial=data_inicial,data_final=data_final)       
        
        _logger.debug(f"lista_arquivos: {lista_arquivos}")
        return lista_arquivos
  
    @api.depends('file_path')
    def _compute_cycle_txt(self):
        for record in self:
            if record.file_path and os.path.exists(record.file_path):
                try:
                    with open(record.file_path, 'r', encoding='utf-8') as file:
                        record.cycle_txt = file.read()
                        record.cycle_txt = record.cycle_txt.replace('\x00', '')
                except Exception as e:
                    _logger.error(f"Erro ao ler arquivo TXT: {str(e)}")
                    record.cycle_txt = False
            else:
                record.cycle_txt = False

    def _get_dataobject(self,equipment_id=None,file_path=None):
        _logger.debug(f"_get_dataobject equipment_id: {equipment_id}")
        equipment_id = self.equipment_id if self.id else equipment_id
        if not equipment_id:
            raise UserError("Nenhum equipamento informado")
        cycle_type_id = self.cycle_type_id if self.id else equipment_id.cycle_type_id

        
        if not cycle_type_id:
            if self.id:
                raise UserError(f"O ciclo {self.name} não possui tipo de ciclo definido. \n")
            if equipment_id:
                raise UserError(f"O equipamento {equipment_id} não possui tipo de ciclo definido. \n")
            raise UserError("Nenhum tipo de ciclo informado")
        
        #diretorio onde os ciclos estão armazenados
        path_ciclo = equipment_id.cycle_path
        
        #verifica se o diretorio onde os ciclos estão armazenados está definido
        if not path_ciclo:
            raise UserError(f"Equipamento {equipment_id} não possui path_ciclo do tipo de ciclo definido")
        #criando o objeto DataObjectFitaDigital
        do = DataObjectFitaDigital(directory_path=path_ciclo)

        #se não for informado o file_path, retorna o objeto DataObjectFitaDigital
        if not file_path:
            return do

        #verifica se o header_lines está definido
        if not cycle_type_id.header_lines:
            if self.id:
                raise UserError(f"O ciclo {self.name} não possui header_lines do tipo de ciclo definido")
            if equipment_id:
                raise UserError(f"O equipamento {equipment_id} não possui header_lines do tipo de ciclo definido")
            
            raise UserError("Nenhum header_lines no tipo de ciclo foi informado")
        
        #verificando se o leitor de fita digital está definido
        nome_classe_leitor = cycle_type_id.reader_class_dataobject
        if not nome_classe_leitor:
            if self.id:
                raise UserError(f"O ciclo {self.name} não possui reader_class_dataobject do tipo de ciclo definido")
            if equipment_id:
                raise UserError(f"O equipamento {equipment_id} não possui reader_class_dataobject do tipo de ciclo definido")
            
            raise UserError("Nenhum reader_class_dataobject no tipo de ciclo foi informado")
        

        reader_class = self._carregar_classe_leitor(equipment_id)
        _logger.debug(f"file_path: {file_path}")
       
        do.register_reader_fita(reader_class(file_path), 
                               size_header=cycle_type_id.header_lines)
       
        

        return do
    
    @api.depends('cycle_txt')
    def _compute_cycle_statistics_txt(self):
        for record in self:
            do = self._get_dataobject(record.equipment_id,record.file_path)
            if not record.cycle_txt:
                record.cycle_statistics_txt = False
                continue
            if record.cycle_type_id.fases_fita_digital:
                fases = record.cycle_type_id.fases_fita_digital.split(',')
                statistics = do.compute_statistics(fases)
                record.cycle_statistics_txt = statistics
            else:
                record.cycle_statistics_txt = do.compute_statistics()

    @api.depends('cycle_txt')
    def _compute_cycle_statistics_data(self):
        for record in self:
            if not record.cycle_txt:
                record.cycle_statistics_data = {}
                continue
            try:
                do = self._get_dataobject(record.equipment_id, record.file_path)
                if record.cycle_type_id.fases_fita_digital:
                    fases = record.cycle_type_id.fases_fita_digital.split(',')
                    statistics = do.compute_statistics(fases)
                else:
                    statistics = do.compute_statistics()
                
                # Garantir que os dados estão no formato correto
                if isinstance(statistics, dict):
                    # Converter para lista de tuplas se necessário
                    formatted_data = []
                    for fase, dados in statistics.items():
                        if isinstance(dados, dict):
                            formatted_data.append((fase, dados))
                        else:
                            formatted_data.append((fase, {}))
                    record.cycle_statistics_data = formatted_data
                elif isinstance(statistics, list):
                    record.cycle_statistics_data = statistics
                else:
                    record.cycle_statistics_data = []
                    
            except Exception as e:
                _logger.error(f"Erro ao calcular estatísticas para ciclo {record.name}: {e}")
                record.cycle_statistics_data = []
   

    def compute_cycle_graph(self):
        
        """
        Calcula e gera o gráfico do ciclo a partir dos dados da fita digital.
        O gráfico mostra a temperatura e pressão ao longo do tempo, com marcações
        das fases do ciclo e o tempo entre cada fase.
        """

        for record in self:
            do = self._get_dataobject(record.equipment_id,record.file_path)
            if not record.cycle_txt:
                record.cycle_graph = False
                continue
                
            try:
                process_graph = self.process_graph(record,do)
            except Exception as e:
                _logger.error(f"Erro ao processar gráfico.: {str(e)}")
                record.cycle_graph = False
                continue

            

    def process_graph(self,record,do):
        """
        Processa o gráfico do ciclo a partir dos dados da fita digital.
        """
        cycle_graph = do.make_graph()
        record.cycle_graph = cycle_graph
        

    def get_view(self, view_id=None, view_type='form', **options):
        """
        Sobrescreve o método get_view para retornar o formulário específico configurado no tipo de ciclo
        quando o view_type for 'form'.
        
        Args:
            view_id: ID da view a ser carregada
            view_type: Tipo da view ('form', 'tree', etc)
            options: Opções adicionais
            
        Returns:
            dict: Dados da view
        """
        _logger.debug(f"view_id: {view_id}")
        _logger.debug(f"view_type: {view_type}")
        _logger.debug(f"options: {options}")
        _logger.debug(f"self: {self}")
        _logger.debug(f"self.cycle_type_id: {self.cycle_type_id}")

        # Se for view tipo form e tiver cycle_type_id configurado
        # if view_type == 'form':
        #     view_id = self.cycle_type_id.form_view_id.id or	2211
        #     _logger.debug(f"Usando view específica do tipo de ciclo: {view_id}")
            
        res = super(SupervisorioCiclos, self).get_view(view_id, view_type, **options)
        _logger.debug(f"res: {res}")
            
        return res

    def _get_file_content(self):
        """Lê o conteúdo do arquivo TXT para o relatório PDF"""
        self.ensure_one()
        if not self.file_path or not os.path.exists(self.file_path):
            return "Arquivo não encontrado"
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            _logger.error(f"Erro ao ler arquivo: {str(e)}")
            return f"Erro ao ler arquivo: {str(e)}"

    @api.depends('cycle_txt')
    def _compute_statistics(self):
        """
        Calcula as estatísticas do ciclo a partir do arquivo de fita digital.
        """
        for record in self:
            record.cycle_statistics_txt = "teste"
        # for record in self:
        #     if not record.file_path or not os.path.exists(record.file_path):
        #         record.cycle_statistics_txt = False
        #         continue

        #     try:
        #         # Cria uma instância do leitor apropriado baseado no tipo de equipamento
        #         reader_class = self._carregar_classe_leitor(record.equipment_id)
        #         if not reader_class:
        #             record.cycle_statistics_txt = False
        #             continue

        #         reader = reader_class(record.file_path)
        #         do = self._get_dataobject(record.equipment_id.apelido)
        #         statistics = reader.

        #         # Formata as estatísticas para exibição
        #         formatted_stats = []
                
        #         # Adiciona tempo total
        #         formatted_stats.append(f"Tempo Total: {statistics['tempo_total']}")
                
        #         # Adiciona tempo por fase
        #         formatted_stats.append("\nTempo por Fase:")
        #         for fase, tempo in statistics['tempo_por_fase_formatado'].items():
        #             formatted_stats.append(f"- {fase}: {tempo}")
                
        #         # Adiciona estatísticas de temperatura
        #         formatted_stats.append("\nTemperatura:")
        #         formatted_stats.append(f"- Máxima: {statistics['temperatura_maxima']}")
        #         formatted_stats.append(f"- Mínima: {statistics['temperatura_minima']}")
        #         formatted_stats.append(f"- Média: {statistics['temperatura_media']}")
                
        #         # Adiciona estatísticas de pressão
        #         formatted_stats.append("\nPressão:")
        #         formatted_stats.append(f"- Máxima: {statistics['pressao_maxima']}")
        #         formatted_stats.append(f"- Mínima: {statistics['pressao_minima']}")
        #         formatted_stats.append(f"- Média: {statistics['pressao_media']}")

        #         record.cycle_statistics_txt = '\n'.join(formatted_stats)

        #     except Exception as e:
        #         _logger.error(f"Erro ao calcular estatísticas: {str(e)}")
        #         record.cycle_statistics_txt = False