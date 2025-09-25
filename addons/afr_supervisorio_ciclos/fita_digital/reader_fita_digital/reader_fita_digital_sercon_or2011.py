from .reader_fita_digital import ReaderFitaDigitalInterface
import re
from datetime import datetime,timedelta
import os
import logging
import sys
_logger = logging.getLogger(__name__)



class ReaderFitaDigitalSerconOr2011(ReaderFitaDigitalInterface):
    """
    Classe para leitura de fitas digitais do equipamento Vapor Sercon OR 2011.
    
    Esta classe implementa a interface ReaderFitaDigitalInterface para processar arquivos
    de fita digital específicos do equipamento Vapor Sercon OR 2011, extraindo informações do cabeçalho
    e dados das medições realizadas durante o ciclo de vapor.

    Attributes:
        size_header (int): Tamanho do cabeçalho em linhas (padrão: 24 linhas)
    """

    def __init__(self, full_path_file):
        """
        Inicializa o leitor de fita Sercon OR 2011.

        Args:
            full_path_file (str): Caminho completo do arquivo a ser lido
        """
        super().__init__(full_path_file)
        self.size_header = 21

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
        
         
        header_columns = [col for i, col in enumerate(header_line.split()) if i not in (2, 4)]
        body_dict['header_columns'] = header_columns
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
            padrao = r'^\s*(\d{2}:\d{2}:\d{2})\s+(\d{3},\d)\s+(\d,\d{2})\s+(\d{4},\d)\s*$'
            match = re.match(padrao, line.strip())
            
            
            if not match:
                return body_dict
                
            valores = line.split()
            # Adiciona ":00" ao horário (primeiro valor)
            hora_completa = valores[0] 
            medicao = [
                hora_completa if i == 0 else float(valor.replace(',', '.'))
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
           
            # Regex para encontrar texto (com pontos opcionais) seguido de hora (HH:MM:SS)
            padrao = r'^\s*([^\d:]+)[.]*:?\s*(\d{2}:\d{2}:\d{2})\s*$'
            match = re.match(padrao, line.strip())
          
            
            if match:
              
                hora = match.group(2)  # Captura a hora
                # Adiciona ":00" ao horário (primeiro valor)
                hora = hora 
                fase = match.group(1).strip().replace('.', '')  # Captura o texto após a hora e remove espaços extras
                
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
        
        
        try:
            header = header_values
            for line in file_content:

                # procurando data e hora de inicia do ciclo
                value = line.split()
            
                if len(value) == 2:
                    if value[0].startswith('DATA:'):
                        
                        date = value[0].split(':')[1].split('/')
                    
                        header['Data:'] = f"{date[0]}-{date[1]}-{date[2]}"
                        hora = value[1].split(':')
                        header['Hora:'] = f"{hora[1]}:{hora[2]}:{hora[3]}"
                        
                
                if line.strip().startswith('LOTE....'):
                    header['LOTE'] = line.split(':')[1].strip() or ''
                    
                if line.strip().startswith('CICLO:'):
                    header['CICLO'] = line.split(':')[1].strip().replace('\n', '') or ''
                
                if line.strip().startswith('SET-POINT'):
                    setpoint = line.split(':')[1].strip().replace('\n', '') or ''
                    if setpoint != '':
                        setpoint = setpoint.split(' ')[0].strip()
                        setpoint = float(setpoint.replace(',', '.'))
                        header['SET-POINT'] = setpoint
                    break
        

            if 'Data:' not in header or 'Hora:' not in header:
                header['Data:'] = header_values['create_date'].strftime('%d-%m-%Y')
                header['Hora:'] = header_values['create_date'].strftime('%H:%M:%S')
                _logger.warning(f"Data e Hora não encontradas no arquivo {self.file_name}, usando data e hora do arquivo")
        except Exception as e:
            _logger.error(f"Erro ao ler cabeçalho: {str(e)}")

        _logger.debug(f"header: {header}")
        try:
            header[self.header_fields.date_key] = datetime.strptime(header[self.header_fields.date_key], '%d-%m-%Y')
        except Exception as e:
            _logger.error(f"Erro ao converter data: {str(e)} no metodo {sys._getframe().f_code.co_name}")
        
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
            self.state_finalized_keys = ["FINAL DO CICLO"]
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
        
    def _get_fases_permitidas(self):
        """
        Obtém as fases permitidas para o ciclo.
        """
        return  [
                'INICIO DO AQUECIMENTO',
                
                'INICIO DA HOMOGENIZACAO', 
                'INICIO DA ESTERILIZACAO',
                'TERMINO DA ESTERILIZACAO',
          
            ]
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
                    temperatures.append(float(row[1]))  # TCI(Celsius)
            
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
            fases_permitidas = self._get_fases_permitidas()
            
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
            #TODO: Verificar se o header['TEMPERATURA DA AGUA'] se está pegando o valor correto
            ax1.axhline(y=header.get(header['SET-POINT'], 0), color='black', linestyle='--', label='Set-Point')
            
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

    def compute_statistics(self, phases=None, header=None, body=None):
        """
        Calcula as estatísticas do ciclo (máximo, mínimo, média e moda) para cada variável.

        Args:
            fases (list, opcional): Lista de fases para cálculo das estatísticas

        Returns:
            dict: Dicionário com as estatísticas de cada variável do ciclo
                {   'ESTERILIZACAO': {'Duration': '00:00:00', 'PCI(Bar)': {'max': float, 'min': float, 'media': float, 'moda': float}, 
                    'TCI(Celsius)': {'max': float, 'min': float, 'media': float, 'moda': float},
                    'ETO(Kg)': {'max': float, 'min': float, 'media': float, 'moda': float},
                    ...},
                    'LAVAGEM': {'Duration': '00:00:00', 'PCI(Bar)': {'max': float, 'min': float, 'media': float, 'moda': float}, 
                    'TCI(Celsius)': {'max': float, 'min': float, 'media': float, 'moda': float},
                    'ETO(Kg)': {'max': float, 'min': float, 'media': float, 'moda': float},
                    ...}
                }
                
        Raises:
            ValueError: Se os dados da fita não foram carregados ou se as fases não forem encontradas
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/caminho/")
            >>> do.read_all_fita()
            >>> stats = do.calcular_estatisticas_ciclo(fases=['ESTERILIZACAO','LAVAGEM','AERACAO'])
            >>> print(stats['ESTERILIZACAO'])
            {'Duration': '00:00:00', 'PCI(Bar)': {'max': float, 'min': float, 'media': float, 'moda': float}, 
        """
       
        error_msg = []
        duration = None
         
        if not body or 'data' not in body:
            raise ValueError("Dados da fita não foram carregados")

        if not phases:
            raise ValueError("Lista de fases não fornecida")
        #filtrando as fases de interesse no body_fita
        body_fases_filtradas = [x for x in body['fase'] if x[1] in phases]
        
        estatisticas = {}
        # Para cada fase na lista
        for i in range(len(phases)-1):
            fase_atual = phases[i]
            fase_proxima = None
    
            # Calcula a duração entre as fases usando os índices
            try:
                idx_fase_atual = [f[1] for f in body['fase'] ].index(fase_atual)
                print(f"idx_fase_atual: {idx_fase_atual}, fase_atual: {fase_atual}")
                if idx_fase_atual is None:
                    error_msg[i] = f"Não foi possível encontrar a fase {fase_atual}"
                    continue
                print(f"idx_fase_atual: {idx_fase_atual}")
                idx_fase_proxima = None

                for fproxima in phases[i+1:]:
                    try:
                        idx_fase_proxima =  [f[1] for f in body['fase']].index(fproxima)
                        fase_proxima = fproxima
                        break
                    except ValueError as e:
                        error_msg.append( f"Não foi possível encontrar a próxima fase {fproxima} para {fase_atual}: {str(e)}"  )  
                        continue
               
                    
                    
                print(f"idx_fase_proxima: {idx_fase_proxima}")
                duration = self.calcular_tempo_entre_fases(fase_atual, fproxima)
                print(f"duration: {duration}")
           
            except ValueError as e:
                error_msg.append( f"A fase {fase_atual} não foi encontrada: {str(e)}")
                continue
            except Exception as e:
                error_msg.append( f"Erro ao calcular estatísticas do ciclo {fase_atual}: {str(e)}")
                
            # Calcula as estatísticas entre as fases
            if fase_proxima is None:
                error_msg.append( f"Não foi possível encontrar a próxima fase para {fase_atual}. Calculando até o final do ciclo")

                
            duration = self.calcular_tempo_entre_fases(fase_atual, fase_proxima)
            stats = self.compute_statistics_between_phases(fase_atual, fase_proxima,header,body)
            # Adiciona as estatísticas ao dicionário
            estatisticas[fase_atual] = {
                'Duration': duration,
                **stats
               
            }
        
        return self.formatar_estatisticas_colunas(estatisticas),error_msg

    def formatar_estatisticas_colunas(self,statistics):
        """
        Formata o dicionário de estatísticas do ciclo em colunas alinhadas.
        """
        print(f"statistics: {statistics}")
        linhas = []
        for fase, dados in statistics.items():
            minutos, segundos = dados['Duration'].split(':')
            linhas.append(f"## {fase.upper()} - {minutos} min {segundos} seg\n")
            linhas.append(f"{'Grandeza':<12} {'Min':>10} {'Max':>10} {'Med':>10} {'Moda':>10}")
            for var, valores in dados.items():
                if var == 'Duration':
                    continue
                if isinstance(valores, dict):
                    linhas.append(
                        f"{var:<12} "
                        f"{str(valores.get('min', '')):>10} "
                        f"{str(valores.get('max', '')):>10} "
                        f"{str(valores.get('media', '')):>10} "
                        f"{str(valores.get('moda', '')):>10}"
                    )
            linhas.append("")  # Linha em branco entre fases
        return '\n'.join(linhas)
    
    def compute_statistics_between_phases(self, fase_inicial=None, fase_final=None,header=None,body=None):
        """
        Calcula as estatísticas do ciclo (máximo, mínimo, média e moda) para cada variável entre fases específicas.
        
        Args:
            fase_inicial (str, opcional): Nome da fase inicial para cálculo das estatísticas
            fase_final (str, opcional): Nome da fase final para cálculo das estatísticas
        
        Returns:
            dict: Dicionário com as estatísticas de cada variável do ciclo
                {
                    'PCI(Bar)': {'max': float, 'min': float, 'media': float, 'moda': float},
                    'TCI(Celsius)': {'max': float, 'min': float, 'media': float, 'moda': float},
                    ...
                }
                
        Raises:
            ValueError: Se os dados da fita não foram carregados ou se as fases não forem encontradas
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/caminho/")
            >>> do.read_all_fita()
            >>> stats = do.calcular_estatisticas_ciclo(fase_inicial='LEAK-TEST', fase_final='ACONDICIONAMENTO')
            >>> print(stats['TCI(Celsius)'])
            {'max': 55.2, 'min': 20.1, 'media': 35.6, 'moda': 34.8}
        """
        try:
            if not body or 'data' not in body:
                raise ValueError("Dados da fita não foram carregados")
                
            dados = body['data']
            if not dados:
                #raise ValueError("Não há dados de medição disponíveis")
                estatisticas= {'error': 'Não há dados de medição disponíveis'}
                return estatisticas

            # Se fases foram especificadas, filtra os dados entre elas
            if fase_inicial and fase_final:
                if 'fase' not in body:
                    raise ValueError("Dados de fases não disponíveis")
                    
                # Encontra os timestamps das fases
                fases = body['fase']
                timestamp_inicial = None
                timestamp_final = None
                
                for fase in fases:
                    if fase[1] == fase_inicial:
                        timestamp_inicial = fase[0]
                    elif fase[1] == fase_final:
                        timestamp_final = fase[0]
                        break
                
                if not timestamp_inicial or not timestamp_final:
                    raise ValueError(f"Fases '{fase_inicial}' e/ou '{fase_final}' não encontradas")
                
                # Filtra dados entre as fases
                dados = [linha for linha in dados 
                        if timestamp_inicial <= linha[0] <= timestamp_final]
                
            # Inicializa dicionário de estatísticas
            estatisticas = {}
            
            # Pega os nomes das colunas, excluindo a coluna de tempo (índice 0)
            colunas = body.get('header_columns', [])[1:]
            print(f"colunas: {colunas}")
            # Para cada coluna numérica (índice > 0 nos dados)
            for i, coluna in enumerate(colunas, start=1):
                # Extrai valores da coluna
                valores = [linha[i] for linha in dados]
                if len(valores) == 0:
                    continue
                # Calcula estatísticas
                maximo = max(valores)
                minimo = min(valores)
                media = sum(valores) / len(valores)
                
                # Calcula a moda
                from statistics import mode
                try:
                    moda = mode(valores)
                except:
                    moda = None
                    
                estatisticas[coluna] = {
                    'max': round(maximo, 2),
                    'min': round(minimo, 2),
                    'media': round(media, 2),
                    'moda': round(moda, 2) if moda is not None else None
                }
                
            return estatisticas
            
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Erro ao calcular estatísticas entre as fases do ciclo: {str(e)}")

    def calcular_tempo_entre_fases(self, fase_inicio, fase_fim):
        """
        Calcula o tempo decorrido entre duas fases do ciclo.

        Args:
            fase_inicio (str): Nome da fase inicial
            fase_fim (str): Nome da fase final

        Returns:
            str: Tempo decorrido no formato mm:ss
        """
        try:
            # Garante que as fases existem no body
            if 'fase' not in self.body or not isinstance(self.body['fase'], list):
                raise ValueError("Fases não encontradas no body.")

            fases = self.body['fase']
            # Busca os datetimes das fases
            inicio = next((f[0] for f in fases if f[1] == fase_inicio), None)
            fim = next((f[0] for f in fases if f[1] == fase_fim), None)

            if not inicio or not fim:
                raise ValueError(f"Fase(s) '{fase_inicio}' ou '{fase_fim}' não encontrada(s).")

            tempo_decorrido = fim - inicio
            total_segundos = int(tempo_decorrido.total_seconds())
            minutos = total_segundos // 60
            segundos = total_segundos % 60
            return f"{minutos:02d}:{segundos:02d}"
        except Exception as e:
            return f"Erro: {str(e)}"

    
       

