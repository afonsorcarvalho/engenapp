import os
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
_logger = logging.getLogger(__name__)
import numpy as np
class DataObjectFitaDigital:
    """
    Classe para manipulação de arquivos de fita digital.

    Esta classe fornece funcionalidades para leitura e processamento de arquivos de fita digital,
    que contêm registros de ciclos de equipamentos como autoclaves e lavadoras.

    Attributes:
        directory_path (str): Caminho do diretório onde estão os arquivos de fita
        header_fita (dict): Dicionário com informações do cabeçalho da fita
        body_fita (dict): Dicionário com dados do corpo da fita

    Example:
        >>> # Criando uma instância
        >>> do = DataObjectFitaDigital("/caminho/para/ciclos/")
        >>> 
        >>> # Lendo arquivos de um diretório específico
        >>> arquivos = do.ler_diretorio_ciclos("ETO01")
        >>> 
        >>> # Registrando um leitor de fita
        >>> do.register_reader_fita(ReaderFitaDigitalAfr("/caminho/completo/arquivo.txt"))
        >>> 
        >>> # Lendo dados da fita
        >>> header, body = do.read_all_fita()
    """

    def __init__(self, directory_path=""):
        """
        Inicializa o objeto de manipulação de fita digital.

        Args:
            directory_path (str): Caminho do diretório dos arquivos. Não pode ser vazio.

        Raises:
            ValueError: Se directory_path estiver vazio
        """
        if not directory_path:
            raise ValueError("O caminho do diretório (directory_path) deve ser fornecido")
        self.directory_path = directory_path
        self.header_fita = {}
        self.body_fita = {}
        self.header_fields = ["Data:","Hora:","Ciclo:","Equipamento:","Operador:","Cod. ciclo:","Ciclo Selecionado:"]
        self.size_header = 25
        self.lines_file = []
        self.lines_body_raw = []
        self.body = {}
    def set_size_header(self, size_header):
        """
        Define o tamanho do cabeçalho do arquivo de fita.

        Args:
            size_header (int): Tamanho do cabeçalho em bytes
            
        Raises:
            ValueError: Se reader_fita não estiver definido
        """
        if not hasattr(self, 'reader_fita'):
            raise ValueError("reader_fita não está definido. Use register_reader_fita() primeiro.")
            
        self.reader_fita.size_header = size_header
        
    def ler_diretorio_ciclos(self, directory_path="", extension_file_search=None, data_inicial=None, data_final=None):
        """
        Método para leitura recursiva de diretório de ciclos com filtro por data.

        Args:
            directory (str): Nome do diretório
            extension_file_search (list): Lista de extensões para filtrar. Se None, usa [".txt"]
            data_inicial (datetime): Data inicial para filtro (opcional)
            data_final (datetime): Data final para filtro (opcional)

        Returns:
            list: Lista de arquivos encontrados e filtrados por data
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/ciclos/")
            >>> arquivos = do.ler_diretorio_ciclos(
            ...     "ETO01", 
            ...     data_inicial=datetime(2024,1,1),
            ...     data_final=datetime(2024,1,31)
            ... )
        """
        arquivos = []
        
        # Define extensão padrão se None
        if extension_file_search is None:
            extension_file_search = [".txt"]
        
        # Usa pathlib para manipulação de caminhos
        base_path = Path(directory_path)
        
        # Verifica se o diretório existe
        if not base_path.exists():
            return arquivos
            
        # Se data_inicial não fornecida mas data_final sim, não precisa filtrar por data inicial
        # Se data_final não fornecida mas data_inicial sim, usa data atual como final
        if data_inicial and not data_final:
            data_final = datetime.now()
            
        # Itera recursivamente sobre todos os arquivos em todos os subdiretórios
        for arquivo in base_path.rglob("*"):
            if not arquivo.is_file():
                continue
        
            # Verifica extensões
            if extension_file_search and not any(str(arquivo).endswith(ext) for ext in extension_file_search):
                continue
                
            try:
                # Obtém datas de criação e modificação
                create_date = datetime.fromtimestamp(os.path.getctime(arquivo))
                change_date = datetime.fromtimestamp(os.path.getmtime(arquivo))
                
                # Só aplica filtro de data se alguma data foi fornecida
                if data_inicial or data_final:
                    if data_inicial and change_date < data_inicial:
                        continue
                    if data_final and change_date > data_final:
                        continue
                    
                arquivo_info = {
                    'name': arquivo.name,
                    'path': str(arquivo.parent),
                    'create_date': create_date, 
                    'change_date': change_date
                }
                arquivos.append(arquivo_info)
                
            except Exception:
                continue

        return arquivos
    def _cut_header_fita(self,file_name, size_header=25 ):
        """
        Extrai o cabeçalho de um arquivo de fita.

        Args:
            file_name (str): Nome do arquivo
            size_header (int): Tamanho do cabeçalho em bytes

        Returns:
            str: Conteúdo do cabeçalho
        """
        with open(self.directory_path + file_name, 'r') as file:
            header = file.read(size_header)
            return header
    
    def _read_file_fita(self,file_name, size_header=25 ):
        """
        Lê um arquivo de fita completo.

        Args:
            file_name (str): Nome do arquivo
            size_header (int): Tamanho do cabeçalho
        """
        _cut_header = self._cut_header_fita(file_name, size_header)
    
    def register_reader_fita(self, reader_fita,size_header=None):
        """
        Registra um leitor de fita para processamento.

        Args:
            reader_fita (ReaderFitaInterface): Instância do leitor de fita
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/caminho/para/ciclos/")
            >>> do.register_reader_fita(ReaderFitaDigitalAfr("arquivo.txt"))
        """
        self.reader_fita = reader_fita
        self.reader_fita.size_header = size_header or self.size_header

    def read_body_fita(self):
        """
        Lê e processa o corpo da fita digital, convertendo os horários para objetos datetime.

        Esta função é responsável por:
        1. Ler o corpo da fita digital através do leitor registrado
        2. Converter os horários das medições e fases para objetos datetime
        3. Adicionar o estado do ciclo ao corpo da fita
        4. Retornar os dados processados em um dicionário estruturado

        Returns:
            dict: Dicionário contendo os dados processados do corpo da fita com:
                - header_columns (list): Nomes das colunas dos dados
                - data (list): Lista de medições com horários convertidos para datetime
                - fase (list): Lista de fases do ciclo com horários convertidos
                - state (str): Estado atual do ciclo (concluido/abortado/em_andamento/erro)
                
        Raises:
            ValueError: 
                - Se o cabeçalho não foi lido previamente
                - Se não houver dados válidos no corpo da fita
            Exception: Para erros inesperados durante o processamento
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/caminho/para/ciclos/")
            >>> do.register_reader_fita(ReaderFitaDigitalAfr("arquivo.txt"))
            >>> body = do.read_body_fita()
            >>> print(body)
            {
                'header_columns': ['Hora', 'PCI(Bar)', 'TCI(Celsius)', 'UR(%)', 'ETO(Kg)'],
                'data': [
                    [datetime(2024,1,1,14,28,34), 0.000, 49.80, 50, 0.0],
                    [datetime(2024,1,1,14,29,07), -0.120, 49.90, 51, 0.0],
                ],
                'fase': [
                    [datetime(2024,1,1,14,28,36), 'LEAK-TEST'],
                    [datetime(2024,1,1,14,41,03), 'ACONDICIONAMENTO']
                ],
                'state': 'concluido'
            }
        """
        try:
            # Verifica se o cabeçalho foi lido
            if not self.header_fita:
                self.read_header_fita()
                
            # Lê o corpo da fita
            self.body_fita = self.reader_fita.read_body()
            
            # Valida se há dados para processar
            if not self.body_fita or 'data' not in self.body_fita:
                raise ValueError("Não foram encontrados dados válidos no corpo da fita")
                
            # Extrai e converte os horários para datetime
            horarios = [linha[0] for linha in self.body_fita['data']]
            # Converte os horários para datetime utilizando como base a data do cabeçalho da fita
            times = self.time_to_datetime(horarios, self.header_fita[self.reader_fita.header_fields.date_key])
            
            # Atualiza os horários no body_fita['data']
            for i, time in enumerate(times):
                self.body_fita['data'][i][0] = time

            # Converte os horários das fases para datetime
            if 'fase' in self.body_fita:
                horarios_fase = [fase[0] for fase in self.body_fita['fase']]
                # convertendo para datetime utilizando como base a data do cabeçalho da fita
                times_fase = self.time_to_datetime(horarios_fase, self.header_fita[self.reader_fita.header_fields.date_key])
                
                # Atualiza os horários no body_fita['fase']
                for i, time in enumerate(times_fase):
                    self.body_fita['fase'][i][0] = time
                    
            # Adiciona o estado do ciclo ao corpo da fita
            self.body_fita['state'] = self.reader_fita.get_state()
            _logger.debug(f"Processados {len(times)} registros de medição")
            
            return self.body_fita
            
        except ValueError as e:
            _logger.info(f"Erro ao processar dados da fita: {str(e)}")
            return self.body_fita
        except Exception as e:
            raise Exception(f"Erro inesperado ao ler corpo da fita: {str(e)}")
            
    def read_header_fita(self):
        """
        Lê o cabeçalho da fita digital.

        Returns:
            dict: Dados do cabeçalho da fita
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/caminho/para/ciclos/")
            >>> do.register_reader_fita(ReaderFitaDigitalAfr("arquivo.txt"))
            >>> header = do.read_header_fita()
            >>> print(header)
            {
                'Data:': '2-10-2024',
                'Hora:': '14:28:34', 
                'Equipamento:': 'ETO01',
                'Operador:': 'JONATHAN',
                'Cod. ciclo:': 'ETO0102102406',
                'Ciclo Selecionado:': 'CICLO 01'
            }
        """
        self.header_fita = self.reader_fita.read_header()
        return self.header_fita

    def read_all_fita(self):
        """
        Lê o cabeçalho e corpo da fita digital.

        Returns:
            tuple: (header_fita, body_fita) contendo os dados completos da fita
            
        Exemplo:
            >>> do = DataObjectFitaDigital("/caminho/para/ciclos/")
            >>> do.register_reader_fita(ReaderFitaDigitalAfr("arquivo.txt"))
            >>> header, body = do.read_all_fita()
            >>> print(header)
            {
                'Data:': '2-10-2024',
                'Hora:': '14:28:34',
                'Equipamento:': 'ETO01',
                'Operador:': 'JONATHAN',
                'Cod. ciclo:': 'ETO0102102406',
                'Ciclo Selecionado:': 'CICLO 01'
            }
            >>> print(body)
            {
                'header_columns': ['Hora', 'PCI(Bar)', 'TCI(Celsius)', 'UR(%)', 'ETO(Kg)'],
                'data': [
                    ['14:28:34', 0.000, 49.80, 50, 0.0],
                    ['14:28:36', -0.120, 49.90, 51, 0.0]
                ],
                'fase': [
                    ['14:28:36', 'LEAK-TEST'],
                    ['14:41:03', 'ACONDICIONAMENTO']
                ]
            }
        """
        header = self.read_header_fita()
       
        body = self.read_body_fita()
        
       

        return self.header_fita, self.body_fita
    
    def make_graph(self):
        """
        Gera um gráfico do ciclo de esterilização/termodesinfecção.

        Este método é responsável por criar uma representação visual dos dados
        coletados durante o ciclo, utilizando os dados do cabeçalho e do corpo
        da fita digital.

        Returns:
            object: Um objeto gráfico contendo a visualização do ciclo,
                   que pode incluir:
                   - Curvas de temperatura
                   - Curvas de pressão
                   - Marcadores de fases do ciclo
                   - Legenda e informações do ciclo

        Exemplo:
            >>> data_object = DataObjectFitaDigital()
            >>> grafico = data_object.make_graph()
            >>> # O gráfico pode ser exibido ou salvo em um arquivo
        """
        if not self.header_fita or not self.body_fita:
            self.read_all_fita()
       
       
        
        # Chama o método make_graph do reader_fita passando os dados
        # do cabeçalho e do corpo da fita digital
        graph = self.reader_fita.make_graph(self.header_fita, self.body_fita)
        return graph
    
    def _converter_horario_para_minutos(self, horario):
        """
        Converte um horário no formato HH:MM:SS para minutos totais.
        
        Args:
            horario (str): Horário no formato HH:MM:SS
            
        Returns:
            float: Total de minutos
        """
        h, m, s = map(int, horario.split(':'))
        return h * 60 + m + s/60

    def _formatar_tempo(self, minutos_totais):
        """
        Formata minutos totais para o formato HH:MM:SS.
        
        Args:
            minutos_totais (float): Total de minutos
            
        Returns:
            str: Tempo formatado como HH:MM:SS
        """
        horas = int(minutos_totais // 60)
        minutos = int(minutos_totais % 60)
        segundos = int((minutos_totais * 60) % 60)
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    def calcular_tempo_entre_fases(self, indice_inicial, indice_final):
        """
        Calcula o tempo decorrido entre duas fases do ciclo.

        Args:
            indice_inicial (int): Índice da fase inicial
            indice_final (int): Índice da fase final

        Returns:
            str: Tempo decorrido no formato "HH:MM:SS" entre as fases

        Raises:
            IndexError: Se os índices estiverem fora do intervalo válido
            ValueError: Se não for possível converter os horários ou se indice_inicial > indice_final
        """
        
        try:
            fases = self.body_fita['fase']
            data = self.body_fita['data']
            if not self.body_fita or 'fase' not in self.body_fita:
                raise ValueError("Dados da fita não foram carregados")
            
            #se não for fornecido o indice final, calcula o tempo entre o último registro de data e o índice inicial da fase
            if indice_inicial and indice_final == None:
                tempo_diferenca = data[-1][0] - fases[indice_inicial][0]
                return self._converter_tempo_diferenca_str(tempo_diferenca)

            if indice_inicial > indice_final:
                raise ValueError("O índice inicial deve ser menor que o índice final")

            print(f"fases: {fases}")
            if not (0 <= indice_inicial < len(fases) and 0 <= indice_final < len(fases)):
                raise IndexError("Índices fora do intervalo válido")

            # Calcula a diferença direta entre os objetos datetime
            tempo_diferenca = fases[indice_final][0] - fases[indice_inicial][0]
            
            return self._converter_tempo_diferenca_str(tempo_diferenca)
           
           

        except (IndexError, ValueError) as e:
            raise e
        except Exception as e:
            raise Exception(f"Erro ao calcular tempo entre fases: {str(e)}")
    
    def _converter_tempo_diferenca_str(self,tempo_diferenca):
        """
        Converte a diferença de tempo para o formato HH:MM:SS
        """
        horas = int(tempo_diferenca.total_seconds() // 3600)
        minutos = int((tempo_diferenca.total_seconds() % 3600) // 60)
        segundos = int(tempo_diferenca.total_seconds() % 60)
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    def calcular_tempo_total_ciclo(self):
        """
        Calcula o tempo total do ciclo usando a diferença entre o último e primeiro registro.

        Returns:
            str: Tempo total no formato "HH:mm:ss"

        Raises:
            ValueError: Se os dados da fita não foram carregados
            Exception: Para outros erros durante o cálculo
        """
        try:
            if not self.body_fita or 'data' not in self.body_fita:
                raise ValueError("Dados da fita não foram carregados")

            dados = self.body_fita['data']
            if not dados:
                raise ValueError("Não há dados de medição disponíveis")

            # Como os tempos já são datetime, basta subtrair o último do primeiro
            tempo_total = dados[-1][0] - dados[0][0]
            _logger.debug(f"tempo_total: {tempo_total}")
            # Converte a diferença de tempo para o formato HH:MM:SS
            return self._converter_tempo_diferenca_str(tempo_total)

        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Erro ao calcular tempo total do ciclo: {str(e)}")
    
    def time_to_datetime(self,times,start_date):
        """
        Converte uma lista de strings de horários para objetos datetime, 
        adicionando a data de início fornecida.

        Args:
            times (list): Lista de strings no formato "HH:MM:SS" representando horários
            start_date (datetime): Data inicial a ser combinada com os horários

        Returns:
            list: Lista de objetos datetime com a data e horários combinados

        Exemplo:
            >>> times = ["10:30:00", "11:45:00"]
            >>> start_date = datetime(2024,1,1)
            >>> time_to_datetime(times, start_date)
            [datetime(2024,1,1,10,30,0), datetime(2024,1,1,11,45,0)]
        """
        time_objects = [datetime.strptime(t, "%H:%M:%S") for t in times]
        time_objects = self.replace_date_in_times(time_objects, start_date.strftime("%Y-%m-%d"))
        return time_objects

    def replace_date_in_times(self,time_objects, specific_date):
            """
            Substitui o ano, mês e dia em uma lista de objetos datetime por uma data específica.

            Args:
                time_objects (list): Lista de objetos datetime contendo apenas horas, minutos e segundos.
                specific_date (str): String representando a data no formato "%Y-%m-%d".

            Returns:
                list: Lista de objetos datetime com a data especificada e as horas originais.
            """
            # Converte a data específica para um objeto datetime
            date_object = datetime.strptime(specific_date, "%Y-%m-%d")

            # Substitui ano, mês e dia em cada objeto de tempo
            updated_datetimes = [
                t.replace(year=date_object.year, month=date_object.month, day=date_object.day)
                for t in time_objects
            ]
            total_time = timedelta()
            days_elapsed = 0
            for i in range(1, len(updated_datetimes)):
                updated_datetimes[i] += timedelta(days=days_elapsed) 
                if updated_datetimes[i]  < updated_datetimes[i - 1]:
                    days_elapsed +=1
                    print(days_elapsed)
                    updated_datetimes[i] += timedelta(days=1)

            return updated_datetimes
    def compute_statistics(self, phases=None):
        """
        Calcula as estatísticas do ciclo (máximo, mínimo, média e moda) para cada variável.
        """
        if not self.body_fita or 'data' not in self.body_fita:
            self.read_all_fita()
        statistics, error_msg = self.reader_fita.compute_statistics(phases,self.header_fita,self.body_fita)
        return statistics
    def calcular_estatisticas_ciclo(self, fases=None):
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
        
        if not self.body_fita or 'data' not in self.body_fita:
            raise ValueError("Dados da fita não foram carregados")

        if not fases:
            raise ValueError("Lista de fases não fornecida")
        #filtrando as fases de interesse no body_fita
        body_fases_filtradas = [x for x in self.body_fita['fase'] if x[1] in fases]
        
        estatisticas = {}
        # Para cada fase na lista
        for i in range(len(fases)-1):
            fase_atual = fases[i]
            fase_proxima = None
    
            # Calcula a duração entre as fases usando os índices
            try:
                idx_fase_atual = [f[1] for f in self.body_fita['fase'] ].index(fase_atual)
                print(f"idx_fase_atual: {idx_fase_atual}, fase_atual: {fase_atual}")
                if idx_fase_atual is None:
                    error_msg[i] = f"Não foi possível encontrar a fase {fase_atual}"
                    continue
                print(f"idx_fase_atual: {idx_fase_atual}")
                idx_fase_proxima = None
                
                for fproxima in fases[i+1:]:
                    try:
                        idx_fase_proxima =  [f[1] for f in self.body_fita['fase']].index(fproxima)
                        fase_proxima = fproxima
                        break
                    except ValueError as e:
                        error_msg.append( f"Não foi possível encontrar a próxima fase {fproxima} para {fase_atual}: {str(e)}"  )  
                        continue
               
                    
                    
                print(f"idx_fase_proxima: {idx_fase_proxima}")
                duration = self.calcular_tempo_entre_fases(idx_fase_atual, idx_fase_proxima)
                print(f"duration: {duration}")
           
            except ValueError as e:
                error_msg.append( f"A fase {fase_atual} não foi encontrada: {str(e)}")
                continue
            except Exception as e:
                error_msg.append( f"Erro ao calcular estatísticas do ciclo {fase_atual}: {str(e)}")
                
            # Calcula as estatísticas entre as fases
            if fase_proxima is None:
                error_msg.append( f"Não foi possível encontrar a próxima fase para {fase_atual}. Calculando até o final do ciclo")

                
            stats = self.calcular_estatisticas_ciclo_entre_fases(fase_atual, fase_proxima)
            
            # Adiciona as estatísticas ao dicionário
            estatisticas[fase_atual] = {
                'Duration': duration,
                **stats
            }

        return estatisticas, error_msg

       
            
    def calcular_estatisticas_ciclo_entre_fases(self, fase_inicial=None, fase_final=None):
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
            if not self.body_fita or 'data' not in self.body_fita:
                raise ValueError("Dados da fita não foram carregados")
                
            dados = self.body_fita['data']
            if not dados:
                raise ValueError("Não há dados de medição disponíveis")

            # Se fases foram especificadas, filtra os dados entre elas
            if fase_inicial and fase_final:
                if 'fase' not in self.body_fita:
                    raise ValueError("Dados de fases não disponíveis")
                    
                # Encontra os timestamps das fases
                fases = self.body_fita['fase']
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
            colunas = self.body_fita.get('header_columns', [])[1:]
            
            # Para cada coluna numérica (índice > 0 nos dados)
            for i, coluna in enumerate(colunas, start=1):
                # Extrai valores da coluna
                valores = [linha[i] for linha in dados]
                
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
            raise Exception(f"Erro ao calcular estatísticas do ciclo: {str(e)}")

    def calcular_mortalidade_intervalos(self, N0, fase_inicial='ESTERILIZACAO', fase_final='LAVAGEM', plot=False,index_eto=4,index_temp=2):
        """
        Calcula a mortalidade microbiana acumulativa ao longo do tempo entre duas fases do ciclo usando o modelo D-value.

        Args:
            N0 (float): População inicial de microrganismos
            fase_inicial (str): Nome da fase inicial para cálculo
            fase_final (str): Nome da fase final para cálculo
            plot (bool): Se True, gera um gráfico da mortalidade ao longo do tempo em escala logarítmica

        Returns:
            list: Lista de tuplas (datetime, população) com a mortalidade acumulativa ao longo do tempo
            matplotlib.figure.Figure: Objeto figura do matplotlib se plot=True

        Raises:
            ValueError: Se as fases não forem encontradas ou dados inválidos
            Exception: Para outros erros durante o cálculo

        Notas:
            Implementa o modelo D-value para mortalidade microbiana acumulativa:
            log(N/N0) = -t/D
            onde:
            - D é o tempo necessário para reduzir a população em 90% (1 log)
            - t é o tempo de exposição acumulado
            - Volume da câmara é 15m³
        """
        try:
            # Verifica se há dados carregados
            if not self.body_fita or not self.body_fita.get('data'):
                raise ValueError("Dados da fita não foram carregados")

            # Parâmetros do modelo D-value
            D_value = 3.8 # Valor D em minutos a 54°C (exemplo)
            z_value = 50.0  # Valor Z em °C
            volume_camara = 15.0 # Volume da câmara em m³
            C_value = 0.0045 # Valor de mudança concetração para reduzir em 1 log
            C_base = 0.00045 # Concentração de referência
            temp_base = 50 # Temperatura de referência

            # Filtra dados entre as fases especificadas
            timestamp_inicial = None
            timestamp_final = None
            
            for fase in self.body_fita['fase']:
                if fase[1] == fase_inicial:
                    timestamp_inicial = fase[0]
                elif fase[1] == fase_final:
                    timestamp_final = fase[0]
                    break

            if not timestamp_inicial or not timestamp_final:
                raise ValueError(f"Fases '{fase_inicial}' e/ou '{fase_final}' não encontradas")

            # Filtra dados do período
            dados = [linha for linha in self.body_fita['data'] 
                    if timestamp_inicial <= linha[0] <= timestamp_final]

            if not dados:
                raise ValueError("Não foram encontrados dados no período especificado")

            # Inicializa população e tempo acumulado
            N = N0
            tempo_acumulado = 0
            populacao_ao_longo_do_tempo = [(dados[0][0], N)]

            # Índices das colunas
            if index_temp is None:
                index_temp = 2  # TCI(Celsius)
            if index_eto is None:
                index_eto = 4   # Quantidade de ETO em kg
            idx_temp = index_temp  # TCI(Celsius)
            idx_eto = index_eto   # Quantidade de ETO em kg

            # Calcula mortalidade acumulativa para cada intervalo
            for i in range(1, len(dados)):
                # Acumula o tempo em minutos
                tempo_acumulado += (dados[i][0] - dados[i-1][0]).total_seconds() / 60
                
                # Temperatura média no intervalo
                if index_temp:
                    temp = dados[i-1][idx_temp]
                    
                else:
                    temp = 54
                
                # Calcula concentração de ETO em kg/m³
                if index_eto:
                    eto_kg = dados[i-1][idx_eto]
                    # Elimina valores de ETO maiores que 50kg por serem considerados inválidos
                    if eto_kg > 50:
                        eto_kg = 0.1
                    C = eto_kg / (volume_camara * 1000)
                   
                else:
                    C = C_base
                
                # Ajusta D-value para temperatura atual usando z-value e concentração de ETO
                # A concentração de referência é 0.00045 kg/m³
                D_temp = D_value * 10**((temp_base - temp)/z_value) *10**((C_base - C)/C_value)
                
                # Calcula redução populacional usando D-value e tempo acumulado
                log_reducao = tempo_acumulado/D_temp
                N = N0 * (10**(-log_reducao))
                
                # Armazena resultado
                populacao_ao_longo_do_tempo.append((dados[i][0], N))

            # Gera o gráfico se solicitado
            if plot:
                import matplotlib.pyplot as plt
                from matplotlib.dates import DateFormatter

                # Separa os dados em listas de x e y
                tempos = [p[0] for p in populacao_ao_longo_do_tempo]
                populacoes = [p[1] for p in populacao_ao_longo_do_tempo]

                # Cria a figura e eixos
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Plota os dados em escala logarítmica no eixo y
                ax.semilogy(tempos, populacoes, 'b-', label='População microbiana acumulada')
                
                # Configura o eixo x para mostrar datas formatadas
                ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
                plt.xticks(rotation=45)
                
                # Adiciona rótulos e título
                ax.set_xlabel('Tempo')
                ax.set_ylabel('População Acumulada (UFC/unidade) - Escala Log')
                ax.set_title('Mortalidade Microbiana Acumulativa ao Longo do Tempo')
                ax.grid(True)
                ax.legend()
                
                # Ajusta o layout
                plt.tight_layout()
                
                return populacao_ao_longo_do_tempo, fig
            
            return populacao_ao_longo_do_tempo

        except ValueError as e:
            raise ValueError(f"Erro no cálculo de mortalidade: {str(e)}")
        except Exception as e:
            raise Exception(f"Erro inesperado no cálculo de mortalidade: {str(e)}")

