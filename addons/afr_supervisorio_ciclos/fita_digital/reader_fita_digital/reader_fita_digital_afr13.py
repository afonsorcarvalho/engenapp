from .reader_fita_digital import ReaderFitaDigitalInterface
import re
from datetime import datetime,timedelta
import logging
_logger = logging.getLogger(__name__)



class ReaderFitaDigitalAfr13(ReaderFitaDigitalInterface):
    """
    Classe para leitura de fitas digitais do equipamento AFR.
    
    Esta classe implementa a interface ReaderFitaDigitalInterface para processar arquivos
    de fita digital específicos do equipamento AFR, extraindo informações do cabeçalho
    e dados das medições realizadas durante o ciclo.

    Attributes:
        size_header (int): Tamanho do cabeçalho em linhas
    """

    def __init__(self, full_path_file):
        """
        Inicializa o leitor de fita AFR.

        Args:
            full_path_file (str): Caminho completo do arquivo a ser lido
        """
        super().__init__(full_path_file)
        self.size_header = 24

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
        header_line = lines_body[0].strip()
        body_dict['header_columns'] = header_line.split()
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
            # Regex para validar linha com hora e valores numéricos
            # Aceita hora seguida de um ou mais valores numéricos separados por espaços
            padrao = r'^(\d{2}:\d{2}:\d{2})(?:\s+(-?\d+\.?\d*))+$'
            match = re.match(padrao, line.strip())
            
            if not match:
                return body_dict
                
            valores = line.split()
            medicao = [
                float(valor) if i > 0 else valor
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
            # Regex para encontrar hora (HH:MM:SS) seguida de texto
            padrao = r'^(\d{2}:\d{2}:\d{2})\s+([A-Za-z0-9\s-]+)$'
            match = re.match(padrao, line.strip())
            
            if match:
                hora = match.group(1)  # Captura a hora
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
        header = super().read_header()
        _logger.debug(f"header: {header}")
        header[self.header_fields.date_key] = datetime.strptime(header[self.header_fields.date_key], '%d-%m-%Y')
        
        return header

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
        lines_body = self.read_body_lines_raw()
       
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

    def read_body_lines_raw(self):
        """
        Lê as linhas brutas do corpo do arquivo.

        Returns:
            list: Lista contendo as linhas do corpo do arquivo
        """
        if self.lines_file == []:
            self.read_file()

        self.lines_body_raw = self.lines_file[self.size_header:]

        return self.lines_body_raw

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
            umidity = []
            
            for row in body.get('data', []):
                if len(row) >= 3:
                    times.append(row[0])
                    pressures.append(float(row[1]))  # PCI(Bar)
                    temperatures.append(float(row[2]))  # TCI(Celsius)
                    try:
                        umidity.append(float(row[3]))  # Umidade(%)
                    except:
                        continue


            # Configura o formato do eixo X para mostrar HH:mm:ss
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax1.xaxis.set_major_locator(plt.MaxNLocator(50))
            ax1.yaxis.set_major_locator(plt.MaxNLocator(20))
            ax2.yaxis.set_major_locator(plt.MaxNLocator(20))
            # Configura os limites dos eixos Y conforme solicitado:
            # Temperatura e Umidade: 0 a 100
            # Pressão: -0.600 a 0.100
            ax1.set_ylim(0, 100)      # Temperatura (°C) e Umidade (%) de 0 a 100
            ax2.set_ylim(-1, 0.100)  # Pressão (bar) de -0.600 a 0.100
            # Rotaciona os rótulos do eixo X
            plt.setp(ax1.get_xticklabels(), rotation=90, ha='right', fontsize=10)
            
            # Plota temperatura no eixo Y esquerdo
            color1 = '#1f77b4'  # Azul
            ax1.plot(times, temperatures, color=color1, label='Temperatura (°C)')
            
            # Plota umidade no mesmo eixo Y esquerdo, com cor diferente
            color3 = '#2ca02c'  # Verde
            if umidity:  # Só plota se houver dados de umidade
                ax1.plot(times, umidity, color=color3, label='Umidade (%)')
            
            ax1.set_xlabel('Tempo (HH:mm:ss)')
            ax1.set_ylabel('Temperatura (°C) / Umidade (%)', color=color1)
            ax1.tick_params(axis='y', labelcolor=color1)
           
            
            # Plota pressão no eixo Y direito
            color2 = '#d62728'  # Vermelho
            ax2.plot(times, pressures, color=color2, label='Pressão (bar)')
            ax2.set_ylabel('Pressão (bar)', color=color2)
            ax2.tick_params(axis='y', labelcolor=color2)
            #ax2.set_ylim(0, 2.5)  # Escala de pressão
            
            # Adiciona as fases como linhas verticais
            fases_permitidas = [
                'LEAK-TEST',
                'ACONDICIONAMENTO',
                'PRE-VACUO',
                'INJETANDO ETO',
                'ESTERILIZANDO',
                'LAVAGEM',
                'AERACAO',
                'HIPERVENTILACAO',
                'CICLO ABORTADO',
                'CICLO FINALIZADO'
               
               
            ]
            
            fases_validas = []
            for fase in body.get('fase', []):
                if len(fase) >= 2 and fase[1] in fases_permitidas:
                    fases_validas.append(fase)
            
            # Adiciona as fases e calcula o tempo entre elas
            for i, fase in enumerate(fases_validas):
                tempo_fase = fase[0].strftime('%H:%M:%S')
                ax1.axvline(x=fase[0], color='grey', linestyle='--', alpha=0.5,linewidth=2)
                
                # Calcula o tempo até a próxima fase
                if i < len(fases_validas) - 1:
                    tempo_entre_fases = fases_validas[i+1][0] - fase[0]
                    segundos_totais = tempo_entre_fases.total_seconds()
                    minutos = int(segundos_totais // 60)
                    segundos = int(segundos_totais % 60)
                    texto_fase = f"{tempo_fase} - {fase[1]} --- {minutos:02d} min {segundos:02d} seg"
                else:
                    texto_fase = f"{tempo_fase} - {fase[1]}"
                
               
                    
                ax1.text(fase[0]+timedelta(seconds=15), ax1.get_ylim()[0] + 2,
                        texto_fase,
                        rotation=90,
                        verticalalignment='bottom',
                        fontsize=9)
           
            
            # if fases:
            #     esterilizando = fases.get('ESTERILIZANDO')
            #     if esterilizando:
            #         texto_fase = f"{esterilizando[0].strftime('%H:%M:%S')}"
            #         ax1.text(esterilizando[0]+timedelta(seconds=15), ax1.get_ylim()[0] + 2,
            #                 texto_fase,
            #                 verticalalignment='bottom',
            #                 fontsize=8)
           
            # Adiciona grade
            ax1.grid(True, alpha=0.5,linewidth=1)

            #Adiciona set-point
           
            #ax1.axhline(y=header.get('SETPOINT', 0), color='black', linestyle='--', label=f'Set-Point: {header.get("SETPOINT", 0)}')
            
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
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
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
    
       

