from .reader_fita_digital import ReaderFitaDigitalInterface
import re
from datetime import datetime,timedelta
import os
import logging
_logger = logging.getLogger(__name__)



class ReaderFitaDigitalSerconJpLac210(ReaderFitaDigitalInterface):
    """
    Classe para leitura de fitas digitais do equipamento Vapor Sercon JP LAC 210.
    
    Esta classe implementa a interface ReaderFitaDigitalInterface para processar arquivos
    de fita digital específicos do equipamento Vapor Sercon JP LAC 210, extraindo informações do cabeçalho
    e dados das medições realizadas durante o ciclo de vapor.

    Attributes:
        size_header (int): Tamanho do cabeçalho em linhas (padrão: 24 linhas)
    """

    def __init__(self, full_path_file):
        """
        Inicializa o leitor de fita Sercon JP LAC 210.

        Args:
            full_path_file (str): Caminho completo do arquivo a ser lido
        """
        super().__init__(full_path_file)
        self.size_header = 25

    def _process_header_line(self, lines_body, body_dict):
        """
        Processa a linha de cabeçalho e cria um dicionário com as colunas.

        Args:
            lines_body (list): Lista com as linhas do corpo do arquivo
            body_dict (dict): Dicionário para armazenar os dados processados

        Returns:
            dict: Dicionário atualizado com as colunas do cabeçalho
        """
        # Retorna body_dict original se não houver linhas no corpo
       
        if not lines_body:
            return body_dict
        # Processa o cabeçalho se houver linhas
        header_line = ''
        for line in lines_body:
            if line.strip().startswith('HORA'):
                header_line = line
                break
        header_line = header_line.strip()
        
         
        header_columns = header_line
        body_dict['header_columns'] = header_columns.split()
        return body_dict

    def _process_body_line(self, line, body_dict):
        """
        Processa uma linha do corpo do arquivo e adiciona ao dicionário de dados.

        Args:
            line (str): Linha a ser processada
            body_dict (dict): Dicionário para armazenar os dados processados

        Returns:
            dict: Dicionário atualizado com os dados da linha processada
        """
        try:
            
            
            # Regex para validar linha com hora e valores numéricos com vírgulas
            # padrao = r'^\s*(\d{2}:\d{2}:\d{2})\s+(\d{3},\d)\s+(\d,\d{2})\s+(\d{4},\d)\s*$'
            # match = re.match(padrao, line.strip())
            
            valores = line.split()
            
            if len(valores) < 4:
                return body_dict
            
                         
            
            # Adiciona ":00" ao horário (primeiro valor)
            hora_completa = valores[0]+ ":00"
            medicao = [
                hora_completa if i == 0 else float(valor)
                for i, valor in enumerate(valores)
            ]
            body_dict['data'].append(medicao)
            
        except Exception as e:
            print(f"Erro ao processar linha de medição: {str(e)}")
            
        return body_dict

    def _process_phase_line(self, line, body_dict):
        """
        Processa uma linha de fase do ciclo e adiciona ao dicionário de dados.

        Args:
            line (str): Linha a ser processada
            body_dict (dict): Dicionário para armazenar os dados processados

        Returns:
            tuple: (bool, dict) - Indica se é uma linha de fase e o dicionário atualizado
        """
        
        try:
           # print(line)
            # Regex para encontrar o padrão: hora (HH:MM) seguido de qualquer texto
            padrao = r'^\s*(\d{2}:\d{2})\s+(.+?)\s*$'
            match = re.match(padrao, line)
          
            if match:
                try:
                    float(match.group(2).split()[0])
                    return False, body_dict
                except:
                    pass

                hora = match.group(1)  # Captura a hora
                # Adiciona ":00" ao horário (primeiro valor)
                hora = hora + ":00"
                fase = match.group(2).strip()  # Captura o texto após a hora e remove espaços extras
                
                # Adiciona como array ao invés de dicionário
                body_dict['fase'].append([
                    hora,
                    fase
                ])
                return True, body_dict
            
            return False, body_dict
            
        except Exception as e:
            # Log do erro para debug
            print(f"Erro ao processar linha de fase: {str(e)}")
            return False, body_dict
            
    def read_header(self):
        """
        Lê e processa o cabeçalho do arquivo de fita digital.

        Returns:
            dict: Dicionário contendo as informações do cabeçalho
        """
        # Obtém informações do arquivo
        header_values = self.read_files_information()
        
        # Obtém o conteúdo do arquivo
        file_content = self.read_header_file_content()
       
        
        
        header = header_values
        for line in file_content:

            # procurando data e hora de inicia do ciclo
            value = line.split()
            
            
            if line.strip().startswith('LOTE'):
                header['LOTE'] = line.split(':')[1].strip() or ''
                continue
                
            if line.strip().startswith('CICLO.'):
                header['CICLO'] = line.split(':')[1].strip().replace('\n', '') or ''
                continue

            if line.strip().startswith('SETPOINT'):
                setpoint = line.split(':')[1].strip().replace('\n', '') or ''
                if setpoint != '':
                    setpoint = setpoint.split(' ')[0].strip()
                    setpoint = float(setpoint.replace(',', '.'))
                    header['SETPOINT'] = setpoint
                continue
            if len(value) == 2:
                if value[1].startswith('INICIANDO'):
                    
                    date = value[0].split(':')[1].split('/')
                 
                    header['Data:'] = f"{date[0][2:]}-{date[1]}-{date[2]}"
                    

                    hora = value[0][:5].split(':')
                    header['Hora:'] = f"{hora[0]}:{hora[1]}:00"
                    break
        
        if 'Data:' not in header or 'Hora:' not in header:
            header['Data:'] = header_values['create_date'].strftime('%d-%m-%Y')
            header['Hora:'] = header_values['create_date'].strftime('%H:%M:%S')
            _logger.warning(f"Data e Hora não encontradas no arquivo {self.file_name}, usando data e hora do arquivo")
                    
       

        
        
        
        header[self.header_fields.date_key] = datetime.strptime(header[self.header_fields.date_key], '%d-%m-%Y')
        
        return header
  

    def get_state(self):
        """
        Obtém o estado atual do ciclo da fita digital.
        
        Este método analisa as fases registradas no ciclo para determinar seu estado final.
        O estado é determinado com base nas palavras-chave definidas em state_finalized_keys e state_aborted_keys.
        
        Returns:
            str: Estado do ciclo, podendo ser:
                - 'concluido': Quando encontra uma fase com palavras-chave de finalização
                - 'abortado': Quando encontra uma fase com palavras-chave de aborto
                - 'incompleto': Quando não encontra fases de finalização ou aborto
                - 'erro': Em caso de falha na análise
            
        Raises:
            KeyError: Se a chave 'fase' não existir no dicionário body
            AttributeError: Se houver erro ao acessar os dados da fase
            Exception: Para erros inesperados durante a análise
            
        Exemplo:
            >>> reader = ReaderFitaDigitalAfr13("arquivo.txt")
            >>> estado = reader.get_state()
            >>> print(estado)
            'concluido'
        """
        try:
            if 'fase' not in self.body:
                raise KeyError("Chave 'fase' não encontrada no dicionário body")
            self.state_finalized_keys = ["FIM DE CICLO"]
            self.state_aborted_keys = ["CICLO ABORTADO"]   
            # Verifica se é uma lista de fases
            if isinstance(self.body['fase'], list):
                # Procura por fases de conclusão ou cancelamento
                for fase in self.body['fase']:
                    # Verifica se a fase contém alguma das chaves de finalização
                    if any(key in fase[1] for key in self.state_finalized_keys):
                        return 'concluido'
                    # Verifica se a fase contém alguma das chaves de aborto
                    elif any(key in fase[1] for key in self.state_aborted_keys):
                        return 'abortado'
                # Se não encontrou nenhuma fase de finalização ou aborto, retorna em andamento
                return 'incompleto'
           
                
        except AttributeError as e:
            _logger.error(f"Erro ao acessar dados da fase: {str(e)}")
            return 'erro'
        except Exception as e:
            _logger.error(f"Erro inesperado ao obter estado: {str(e)}")
            return 'erro'
        
     
    def make_graph(self, header, body):
        """
        Gera um gráfico do ciclo de termodesinfecção.

        Este método cria uma visualização gráfica do ciclo de termodesinfecção,
        mostrando as curvas de temperatura e pressão ao longo do tempo, além
        de marcar as fases importantes do ciclo.

        Args:
            header (dict): Dicionário com informações do cabeçalho da fita
            body (dict): Dicionário com dados do corpo da fita

        Returns:
            bytes: Imagem do gráfico em formato base64

        Raises:
            Exception: Se houver erro na geração do gráfico
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import io
            import base64
            
            # Cria uma figura e dois eixos com escalas diferentes
            fig, ax1 = plt.subplots(figsize=(16, 9))
            ax2 = ax1.twinx()  # Cria um segundo eixo Y compartilhando o mesmo eixo X
            
            # Extrai os dados do body
            times = []
            temperatures = []
            pressures = []
            
            for row in body.get('data', []):
                if len(row) >= 3:
                    times.append(row[0])
                    pressures.append(float(row[2]))  # PCI(Bar)
                    temperatures.append(float(row[3]))  # TCI(Celsius)


            # Configura o formato do eixo X para mostrar HH:mm:ss
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax1.xaxis.set_major_locator(plt.MaxNLocator(50))
            ax1.yaxis.set_major_locator(plt.MaxNLocator(30))
            ax2.yaxis.set_major_locator(plt.MaxNLocator(30))
            
            # Rotaciona os rótulos do eixo X
            plt.setp(ax1.get_xticklabels(), rotation=90, ha='right', fontsize=6)
            
            # Plota temperatura no eixo Y esquerdo
            color1 = '#1f77b4'  # Azul
            ax1.plot(times, temperatures, color=color1, label='Temperatura (°C)')
            ax1.set_xlabel('Tempo (HH:mm:ss)')
            ax1.set_ylabel('Temperatura (°C)', color=color1)
            ax1.tick_params(axis='y', labelcolor=color1)
            #ax1.set_ylim(40, 140)  # Escala de temperatura para termodesinfecção
            
            # Plota pressão no eixo Y direito
            color2 = '#d62728'  # Vermelho
            ax2.plot(times, pressures, color=color2, label='Pressão (bar)')
            ax2.set_ylabel('Pressão (bar)', color=color2)
            ax2.tick_params(axis='y', labelcolor=color2)
            #ax2.set_ylim(0, 2.5)  # Escala de pressão
            
            # Adiciona as fases como linhas verticais
            fases_permitidas = [
                'INICIO DE PRE-VACUO',
                
                'AQUECIMENTO C. INTERNA', 
                'INICIO DA ESTERILIZACAO',
                'TERMINO DA ESTERILIZACAO',
                 'INICIO ESTERILIZACAO',
                 'INICIO DESCOMPRESSAO',
                 'INICIO SECAGEM',
                 'FIM DE CICLO',
                # 'TERMINO DA SECAGEM',
                # 'FINAL DO CICLO'
            ]
            
            fases_validas = []
            for fase in body.get('fase', []):
                if len(fase) >= 2 and fase[1] in fases_permitidas:
                    fases_validas.append(fase)
            
            # Adiciona as fases e calcula o tempo entre elas
            for i, fase in enumerate(fases_validas):
                tempo_fase = fase[0].strftime('%H:%M:%S')
                ax1.axvline(x=fase[0], color='g', linestyle='--', alpha=0.5)
                
                # Calcula o tempo até a próxima fase
                if i < len(fases_validas) - 1:
                    tempo_entre_fases = fases_validas[i+1][0] - fase[0]
                    segundos_totais = tempo_entre_fases.total_seconds()
                    minutos = int(segundos_totais // 60)
                    segundos = int(segundos_totais % 60)
                    texto_fase = f"{tempo_fase} - {fase[1]}\n{minutos:02d} min {segundos:02d} seg"
                else:
                    texto_fase = f"{tempo_fase} - {fase[1]}"
                
               
                    
                ax1.text(fase[0]+timedelta(seconds=10), ax1.get_ylim()[0] + 2,
                        texto_fase,
                        rotation=90,
                        verticalalignment='bottom',
                        fontsize=8)
                            
            # Adiciona grade
            ax1.grid(True, alpha=0.3)

            #Adiciona set-point
           
            ax1.axhline(y=header.get('SETPOINT', 0), color='black', linestyle='--', label=f'Set-Point: {header.get("SETPOINT", 0)}')
            
            # Adiciona título
            plt.title(f'Curvas Paramétricas do Ciclo - {header.get("file_name", "Ciclo")}')
            
            # Adiciona legendas
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # Ajusta o layout
            plt.tight_layout()
            
            # Salva o gráfico em um buffer de memória
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            
            # Converte para base64
            cycle_graph = base64.b64encode(buf.getvalue())
            
            # Fecha a figura para liberar memória
            plt.close()
            return cycle_graph
                
        except Exception as e:
            _logger.error(f"Erro ao gerar gráfico: {str(e)}")
            cycle_graph = False
            return cycle_graph
