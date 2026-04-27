from .reader_fita_digital import ReaderFitaDigitalInterface
import re
from datetime import datetime,timedelta
import os
import logging
_logger = logging.getLogger(__name__)


# Pré-compilados em escopo de módulo: evita lookup no re._cache a cada linha.
_BODY_LINE_RE = re.compile(
    r'^\s*(\d{2}:\d{2}:\d{2})\s+([-+]?\d+(?:[.,]\d+)?)\s+([-+]?\d+(?:[.,]\d+)?)\s+([-+]?\d+(?:[.,]\d+)?)\s*$'
)
_PHASE_OPERACAO_RE = re.compile(r'^(\d{2}:\d{2}:\d{2})\s+OPERACAO\s+(\d+):\s+(.+)$')
_PHASE_TEXT_RE = re.compile(r'^([A-Z\s]+)$')
_PHASE_TEXT_HORA_RE = re.compile(r'^([A-Z\s]+)(\d{2}:\d{2}:\d{2})$')
_FIM_CICLO_RE = re.compile(r'^FIM DE CICLO\s+\d{2}:\d{2}:\d{2}$')
_CICLO_CANCELADO_RE = re.compile(r'^CICLO CANCELADO\s+\d{2}:\d{2}:\d{2}$')


class ReaderFitaDigitalBaumerHivac2(ReaderFitaDigitalInterface):
    """
    Classe para leitura de fitas digitais do equipamento Baumer Hivac 2.
    
    Esta classe implementa a interface ReaderFitaDigitalInterface para processar arquivos
    de fita digital específicos do equipamento Baumer Hivac 2, extraindo informações do cabeçalho
    e dados das medições realizadas durante o ciclo de autoclave.
    """
    
    def __init__(self, full_path_file):
        """
        Inicializa o leitor de fita Baumer Hivac 2.
        
        Args:
            full_path_file (str): Caminho completo do arquivo a ser lido
        """
        super().__init__(full_path_file)
        self.size_header = 17
        self.state_finalized_keys = ["FIM DE CICLO"]
        self.header_fields.date_key = "DATA:"
        self.header_fields.time_key = "HORA:"
        self.format_date = "%d-%m-%Y HH:mm:SS"
        self.header_fields.temperature_key = "TEMPERATURA:"
        self.header_fields.pulsos_vacuo_key = "PULSOS DE VACUO:"
        self.header_fields.cycle_code_key = "CODIGO DE CARGA:"
        self.header_fields.selected_cycle_key = "PROGRAMA"
        self.header_fields.num_cycles_key = "NUMERO DE CICLOS:"
        
        self.state_aborted_keys = ["CICLO CANCELADO"]

    def _process_header_line(self, lines_body, body_dict):
       
        """
        Processa a linha de cabeçalho e cria um dicionário com as colunas.
        """
        # Retorna body_dict original se não houver linhas no corpo
      
        if not lines_body:
            return body_dict
        # Processa o cabeçalho se houver linhas
        header_line = ''
        # Percorre as linhas do corpo para encontrar os cabeçalhos e as grandezas
        header_line = ''
        header_line_grandezas = ''
        for line in lines_body:
            if line.strip().startswith('HORA'):
                header_line = line
            if line.strip().startswith('barA'):
                header_line_grandezas = line
                break  # Encontrou ambos, pode sair do loop

        # Processa os cabeçalhos e as grandezas, concatenando conforme solicitado
        header_line = header_line.strip()
        header_line_grandezas = header_line_grandezas.strip()
     
        # Divide as linhas em listas de colunas
        header_cols = header_line.split()
        grandezas_cols = header_line_grandezas.split()
        # Concatena os nomes das colunas com as grandezas, exceto o primeiro item (HORA)
        header_columns = []
        if header_cols and grandezas_cols:
            # O primeiro item é 'HORA', que não tem grandeza
            header_columns.append(header_cols[0])
            # Os demais são concatenados com as grandezas
            for i in range(1, len(header_cols)):
               # if i < len(grandezas_cols):
                header_columns.append(f"{header_cols[i]}({grandezas_cols[i-1]})")
               
        else:
            header_columns = header_cols  # fallback se não encontrar as grandezas

        body_dict['header_columns'] = header_columns
        header_line = header_line.strip()
      
        
        body_dict['header_columns'] = header_columns
        return body_dict
    
    def _process_body_line(self, line, body_dict):
        """
        Processa a linha de corpo e cria um dicionário com as colunas.
        """
        try:
            match = _BODY_LINE_RE.match(line)
            if not match:
                return body_dict

            hora, v1, v2, v3 = match.groups()
            body_dict['data'].append([
                hora,
                float(v1.replace(',', '.')),
                float(v2.replace(',', '.')),
                float(v3.replace(',', '.')),
            ])
        except Exception as e:
            _logger.debug("Erro ao processar linha de medição: %s", e)

        return body_dict
    def _process_phase_line(self, line, body_dict, index, lines_body):
        """
        Processa uma linha de fase do ciclo e adiciona ao dicionário de dados.

        Args:
            line (str): Linha a ser processada
            body_dict (dict): Dicionário para armazenar os dados processados

        Returns:
            tuple: (bool, dict) - Indica se é uma linha de fase e o dicionário atualizado
        """
        
        try:
            stripped = line.strip()
            if not stripped:
                return False, body_dict

            # Filtro barato: linhas de fase começam com dígito (HH:MM:SS) ou letra maiúscula.
            first = stripped[0]
            if not (first.isdigit() or first.isupper()):
                return False, body_dict

            match = _PHASE_OPERACAO_RE.match(stripped)
            if match:
                hora, num, nome = match.group(1), match.group(2), match.group(3)
                body_dict['fase'].append([hora, f"{num.strip()} {nome.strip()}"])
                return True, body_dict

            match2 = _PHASE_TEXT_RE.match(stripped)
            if match2:
                fase = match2.group(1).strip()
                hora = lines_body[index + 2].split()[0]
                body_dict['fase'].append([hora, fase])
                return True, body_dict

            match3 = _PHASE_TEXT_HORA_RE.match(stripped)
            if match3:
                body_dict['fase'].append([match3.group(2).strip(), match3.group(1).strip()])
                return True, body_dict

            return False, body_dict

        except Exception as e:
            _logger.debug("Erro ao processar linha de fase: %s", e)
            return False, body_dict
            
    def read_header(self):
        """
        Lê e processa o cabeçalho do arquivo de fita digital.

        Returns:
            dict: Dicionário contendo as informações do cabeçalho
        """
        
        # Obtém informações do arquivo
        
        header_values = super().read_header()

        # Evita KeyError quando o arquivo de fita não contém a linha "DATA:".
        from datetime import datetime
        data_bruta = header_values.get('DATA:')
        if not data_bruta:
            _logger.warning(
                "Campo 'DATA:' não encontrado no cabeçalho do arquivo %s; "
                "mantendo valor vazio.",
                getattr(self, 'full_path_file', '<arquivo desconhecido>'),
            )
            header_values['DATA:'] = ''
            return header_values

        data_original = data_bruta.split(' ')[0]
        try:
            data_convertida = datetime.strptime(data_original, "%d/%m/%Y")
        except Exception:
            # Formato inesperado; preserva valor original para não quebrar fluxo.
            data_convertida = data_original
        header_values['DATA:'] = data_convertida
      
        
        
        return header_values

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

        body_dict = {'data': [], 'fase': []}
        body_dict = self._process_header_line(lines_body, body_dict)

        for index, line in enumerate(lines_body[1:]):
            line = line.strip()
            if not line:
                continue

            is_phase, body_dict = self._process_phase_line(line, body_dict, index, lines_body)
            if is_phase:
                continue

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
        Determina o estado atual do ciclo da fita digital (Baumer Hivac 2).

        O método verifica as linhas brutas do corpo da fita para identificar finalização ou cancelamento do ciclo:
        - Se encontrar uma linha no formato 'FIM DE CICLO [hora]', retorna 'concluido'.
        - Se encontrar uma linha no formato 'CICLO CANCELADO [hora]', retorna 'abortado'.
        - Se nenhuma dessas condições for satisfeita, assume que o ciclo está 'incompleto'.
        - Em caso de erro durante o processamento, retorna 'erro'.

        Returns:
            str: Estado do ciclo, que pode ser:
                - 'concluido': Ao localizar "FIM DE CICLO [hora]" no corpo da fita
                - 'abortado': Ao localizar "CICLO CANCELADO [hora]" no corpo da fita
                - 'incompleto': Caso nenhuma das linhas acima seja encontrada
                - 'erro': Se ocorrer alguma exceção no processo
        """
        try:
            if not hasattr(self, 'lines_body_raw') or not self.lines_body_raw:
                self.read_body_lines_raw()
            for line in self.lines_body_raw:
                stripped = line.strip()
                if not stripped:
                    continue
                # Filtro barato antes do regex.
                if stripped.startswith('FIM DE CICLO') and _FIM_CICLO_RE.match(stripped):
                    return 'concluido'
                if stripped.startswith('CICLO CANCELADO') and _CICLO_CANCELADO_RE.match(stripped):
                    return 'abortado'
            return 'incompleto'
        except Exception as e:
            _logger.error(f"Erro ao determinar estado do ciclo: {str(e)}")
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
        fig = None
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import io
            import base64

            # Validação barata antes de criar figura (custosa ~100ms): fases/data
            # devem ter datetime no índice 0 — DataObjectFitaDigital normaliza isso.
            fases_raw = body.get('fase') or []
            data_raw = body.get('data') or []
            if not data_raw:
                _logger.warning("make_graph: body['data'] vazio")
                return False
            if fases_raw and not hasattr(fases_raw[0][0], 'strftime'):
                _logger.warning(
                    "make_graph: fase[0] não é datetime — chame via DataObjectFitaDigital"
                )
                return False
            if not hasattr(data_raw[0][0], 'strftime'):
                _logger.warning(
                    "make_graph: data[0][0] não é datetime — chame via DataObjectFitaDigital"
                )
                return False

            # Cria uma figura e dois eixos com escalas diferentes
            fig, ax1 = plt.subplots(figsize=(16, 9))
            ax2 = ax1.twinx()  # Cria um segundo eixo Y compartilhando o mesmo eixo X
            
            # Extrai os dados do body
            times = []
            measures = [[],[],[]]
           
            
            for row in body.get('data', []):
                
                if len(row) >= 3:
                    times.append(row[0])
                    measures[0].append(float(row[1]))
                    measures[1].append(float(row[2]))
                    measures[2].append(float(row[3]))
                                       
            
                   


            # Configura o formato do eixo X para mostrar HH:mm:ss
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax1.xaxis.set_major_locator(plt.MaxNLocator(50))
            ax1.yaxis.set_major_locator(plt.MaxNLocator(20))
            ax2.yaxis.set_major_locator(plt.MaxNLocator(20))
            # Configura os limites dos eixos Y conforme solicitado:
            # Temperatura e Umidade: 0 a 100
            # Pressão: -0.600 a 0.100
            ax1.set_ylim(0, 160)      # Temperatura (°C) e Umidade (%) de 0 a 100
            ax2.set_ylim(-1, 4)  # Pressão (bar) de -0.600 a 0.100
            # Rotaciona os rótulos do eixo X
            plt.setp(ax1.get_xticklabels(), rotation=90, ha='right', fontsize=10)
            
            # Plota temperatura no eixo Y esquerdo
            color1 = '#1f77b4'  # Azul
            ax1.plot(times, measures[1], color=color1, label='Temperatura T1 (°C)')
            
            # Plota umidade no mesmo eixo Y esquerdo, com cor diferente
            color3 = '#2ca02c'  # Verde
            ax1.plot(times, measures[2], color=color3, label='Temperatura T2 (°C)')
            
            ax1.set_xlabel('Tempo (HH:mm:ss)')
            ax1.set_ylabel('Temperatura (°C)', color=color1)
            ax1.tick_params(axis='y', labelcolor=color1)
           
            
            # Plota pressão no eixo Y direito
            color2 = '#d62728'  # Vermelho
            ax2.plot(times, measures[0], color=color2, label='Pressão (bar)')
            ax2.set_ylabel('Pressão (bar)', color=color2)
            ax2.tick_params(axis='y', labelcolor=color2)
            #ax2.set_ylim(0, 2.5)  # Escala de pressão
            
            # Adiciona as fases como linhas verticais
            fases_permitidas = [
                '1 PULSOS DE VACUO',
                'PULSO DE VACUO',
                '2 ESTERILIZACAO',
                'INICIO TEMPO DE ESTERILIZACAO',
                '3 SECAGEM',
                '4 AERACAO',
                'FIM DE CICLO',
                
               
               
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
            setpoint = float(header.get("TEMPERATURA:", 0).replace("oC", "").strip())
            ax1.axhline(y=setpoint, color='black', linestyle='--', label=f'Set-Point: {setpoint} °C',linewidth=1)
            
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
            return cycle_graph

        except Exception as e:
            _logger.error(f"Erro ao gerar gráfico: {str(e)}")
            return False
        finally:
            # Sempre libera a figura — mesmo em exceção — pra evitar leak no matplotlib.
            if fig is not None:
                try:
                    import matplotlib.pyplot as plt
                    plt.close(fig)
                except Exception:
                    pass
    
       

