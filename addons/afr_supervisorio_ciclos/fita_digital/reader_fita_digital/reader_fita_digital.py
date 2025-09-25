from abc import ABC, abstractmethod
import os
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class HeaderFields:
    date_key = "Data:"
    time_key = "Hora:"
    equipment_key = "Equipamento:"
    operator_key = "Operador:"
    cycle_code_key = "Cod. ciclo:"
    selected_cycle_key = "Ciclo Selecionado:"

class ReaderFitaDigitalInterface(ABC):
    """
    Interface para leitura de fitas digitais de equipamentos.
    
    Esta interface define os métodos necessários para ler e processar arquivos de fita digital,
    que contêm registros de ciclos de equipamentos como autoclaves e lavadoras.

    Attributes:
        file_name (str): Caminho completo do arquivo de fita digital
        
        header_fields (list): Lista dos campos do cabeçalho da fita digital
    """

    def __init__(self,full_path_file):
        """
        Inicializa o leitor de fita digital.

        Args:
            full_path_file (str): Caminho completo do arquivo a ser lido
        """
        if not full_path_file:
            raise ValueError("full_path_file não definido ao instanciar o leitor de fita digital")
        self.file_name = full_path_file
        
        # Tamanho padrão do cabeçalho em bytes
        self.size_header = 25
        
        # Lista que armazenará todas as linhas do arquivo após a leitura
        self.lines_file = []
        
        # Lista que armazenará as linhas do corpo do arquivo sem processamento
        # Útil para debug e análise do conteúdo bruto
        self.lines_body_raw = []
        
        # Dicionário que armazenará o corpo do arquivo após processamento
        # Estrutura organizada dos dados do corpo da fita digital
        self.body = {}
        
        # Instância da classe que define as chaves do cabeçalho
        # Facilita o acesso e manutenção das chaves utilizadas no cabeçalho
        self.header_fields = HeaderFields()

        self.state_finalized_keys = ["CICLO FINALIZADO", "CICLO CONCLUIDO","AERACAO"]
        self.state_aborted_keys = ["CICLO ABORTADO"]
    
        
       
  
  
    def read_file(self):
        """
        Lê o conteúdo completo do arquivo de fita.

        Returns:
            str: Conteúdo do arquivo
            
        Raises:
            FileNotFoundError: Se o arquivo não for encontrado
            IOError: Se houver erro na leitura do arquivo
        """
        try:
            print(f"Lendo o arquivo: {self.file_name}")
            with open(self.file_name, 'r') as file:
                self.lines_file = file.readlines()
                return self.lines_file
        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo não encontrado: {self.file_name}")
        except IOError as e:
            raise IOError(f"Erro ao ler o arquivo {self.file_name}: {str(e)}")

    def read_files_information(self):
        """
        Lê as informações do arquivo de fita digital.
        """
        return {
            'file_name': os.path.splitext(os.path.basename(self.file_name))[0],
            'create_date': datetime.fromtimestamp(os.path.getctime(self.file_name)).strftime('%d-%m-%Y %H:%M:%S'),
            'change_date': datetime.fromtimestamp(os.path.getmtime(self.file_name)).strftime('%d-%m-%Y %H:%M:%S')
        }
    def read_header_file_content(self):
        """
        Lê o conteúdo do arquivo de fita digital.

        """
        if self.lines_file == []:
            self.read_file()

        return self.lines_file[:self.size_header]
    def read_body_file_content(self):
        """
        Lê o conteúdo do arquivo de fita digital.

        """
        if self.lines_file == []:
            self.read_file()

        return self.lines_file[self.size_header:]   

    @abstractmethod
    def read_header(self):
        """
        Método abstrato para ler o cabeçalho da fita digital.
        Deve ser implementado pelas classes concretas.

        Args:
            size_header (int): Tamanho do cabeçalho em bytes. Padrão é 25.

        Returns:
            str: Conteúdo do cabeçalho da fita
            
        Exemplo:
            >>> reader = ReaderFitaDigital("arquivo.txt")
            >>> header = reader.read_header()
            >>> print(header)
            {
                'Data:': '13-4-2024',
                'Hora:': '17:21:17',
                'Equipamento:': 'ETO01',
                'Operador:': 'FLAVIOR', 
                'Cod. ciclo:': '7819',
                'Ciclo Selecionado:': 'CICLO 01'
            }
        """
        # Obtém informações do arquivo
        header_values = self.read_files_information()

        # Obtém o conteúdo do arquivo
        file_content = self.read_header_file_content()
        
        # Itera sobre cada linha do conteúdo do arquivo
        for line in file_content:
            # Remove caracteres nulos e espaços em branco do início e fim da linha
            line = line.replace('\x00', '').strip()
            
            # Obtém todos os nomes dos campos do cabeçalho definidos na classe
            header_fields_names = [getattr(self.header_fields, attr) for attr in dir(self.header_fields) if not attr.startswith('_')]
            
            # Itera sobre cada campo do cabeçalho
            for field in header_fields_names:
                
                
                # Se o campo for encontrado na linha, extrai seu valor
                if field in line:
                    # Divide a linha no campo e pega o valor após ele, removendo espaços
                    header_values[field] = line.split(field)[1].strip()

        print(f"header_values: {header_values}")
        return header_values
    
    @abstractmethod
    def get_state(self):
        """
        Obtém o estado da fita digital.
        """
        return ""
 
    def set_header_fields(self,fields_name):
        """
        Define os campos do cabeçalho da fita.

        Args:
            fields_name (list): Lista com os nomes dos campos do cabeçalho

        Returns:
            list: Lista atualizada dos campos do cabeçalho
        """
        self.header_fields = fields_name
        return self.header_fields

    @abstractmethod
    def _process_header_line(lines_body, body_dict):
        pass
    @abstractmethod
    def _process_phase_line(line, body_dict):
        pass
    @abstractmethod
    def _process_body_line(line, body_dict):
        pass


    def read_body(self):
        """
        Lê e processa o corpo do arquivo de fita digital.

        Returns:
            dict: Dicionário contendo os dados processados do arquivo, incluindo:
                - header: Colunas do cabeçalho
                - cabecalho: Informações gerais do cabeçalho
                - data: Lista de medições realizadas durante o ciclo
                - fase: Dicionário com horários e nomes das fases do ciclo
        """
        lines_body = self.read_body_file_content()
       
        body_dict = {}
        body_dict['data'] = []
        body_dict['fase'] = []
       
        # Processa o cabeçalho
        body_dict = self._process_header_line(lines_body, body_dict)
        
        for line in lines_body[1:]:

            line = line.strip()
            
            # Verifica se é uma linha de fase
            is_phase, body_dict = self._process_phase_line(line, body_dict)
            
            if is_phase:
                continue
                    
            # Processa linha de dados
            body_dict = self._process_body_line(line, body_dict)
            self.body = body_dict
        return self.body

    # def read_body_lines_raw(self):
    #     """
    #     Lê as linhas brutas do corpo do arquivo.

    #     Returns:
    #         list: Lista contendo as linhas do corpo do arquivo
    #     """
    #     # Obtém o conteúdo do arquivo
    #     file_content = self.read_file_content()
        
    #     self.lines_body_raw = file_content[self.size_header:]

    #     return self.lines_body_raw


    def get_fases(self, fases):
        """
        Obtém as fases do ciclo da fita digital filtrando apenas as fases enviadas como argumento.
        
        Args:
            fases (list): Lista de fases a serem filtradas
            
        Returns:
            list: Lista de fases encontradas que correspondem ao filtro
        """
        fases_filtradas = []
        if self.body.get('fase'):
            # Filtra as fases que estão na lista de fases desejadas
            fases_filtradas = [fase[1] for fase in self.body['fase'] if fase[1] in fases]
        else:
            fases_filtradas = []
        return fases_filtradas
        
    def get_parametros(self):
        """
        Obtém os parâmetros medidos na fita digital.
        
        Returns:
            list: Lista de parâmetros encontrados
        """
        parametros = []
        if self.body.get('header_columns'):
            # Pega os parâmetros do cabeçalho excluindo a primeira coluna (horas)
            parametros = self.body['header_columns'][1:]
        return parametros

    @abstractmethod
    def make_graph(self, header, body):    
        pass
    
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
        print(f"header: {header}")
        print(f"body: {body}")
        print(f"phases: {phases}")
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
        linhas = [f'### Estatísticas do Ciclo {self.file_name.split("/")[-1].replace(".txt", "")}']
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
        estatisticas = {}
        try:
            if not body or 'data' not in body:
                raise ValueError("Dados da fita não foram carregados")
                
            dados = body['data']
            if not dados:
                #raise ValueError("Não há dados de medição disponíveis")
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
            
            
            # Pega os nomes das colunas, excluindo a coluna de tempo (índice 0)
            colunas = body.get('header_columns', [])[1:]
            
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
            _logger.error(f"Erro ao calcular estatísticas entre as fases do ciclo: {str(e)}")
            return estatisticas
        except Exception as e:
            _logger.error(f"Erro ao calcular estatísticas entre as fases do ciclo: {str(e)}")
            return estatisticas

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
    
    
       

