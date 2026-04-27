

from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

from .reader_fita_digital_afr13 import ReaderFitaDigitalAfr13


class ReaderFitaDigitalAfr14Medplast(ReaderFitaDigitalAfr13):
    """
    Classe para leitura de fitas digitais do equipamento AFR14 MedPlast.

    Herda toda a lógica da ReaderFitaDigitalAfr13.
    O make_graph replica o da classe pai e acrescenta pontos de medida na curva de umidade.
    """

    def __init__(self, full_path_file):
        super().__init__(full_path_file)

    def make_graph(self, header, body, fases_permitidas=None):
        """
        Igual a ReaderFitaDigitalAfr13.make_graph, com pontos de medida na umidade
        aos 15, 90 e 175 minutos após o início da fase ESTERILIZANDO (bolinhas roxas no eixo da umidade).
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
            if not fases_permitidas:
                fases_permitidas = self._get_fases_permitidas()

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

            # Adiciona grade
            ax1.grid(True, alpha=0.5,linewidth=1)

            # AFR14 MedPlast: pontos de medida na umidade (15, 90, 175 min após início de ESTERILIZANDO)
            if umidity and len(umidity) == len(times):
                esterilizando_start = None
                for fase in body.get('fase', []):
                    if len(fase) < 2:
                        continue
                    if 'ESTERILIZANDO' in str(fase[1]).strip().upper():
                        esterilizando_start = fase[0]
                        break
                if esterilizando_start is not None:
                    for offset_min in (15, 90, 175):
                        target_dt = esterilizando_start + timedelta(minutes=offset_min)
                        idx = min(range(len(times)), key=lambda i: abs((times[i] - target_dt).total_seconds()))
                        if abs((times[idx] - target_dt).total_seconds()) > 120:
                            continue
                        uval = umidity[idx]
                        ax1.scatter(times[idx], uval, color='green', zorder=10, s=70, marker='o')
                        ax1.annotate(
                            f"{int(offset_min)}min: {int(uval)}%",
                            (times[idx], uval),
                            textcoords="offset points",
                            xytext=(-10, 10),
                            ha='right',
                            color="green",
                            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.5),
                        )

            #Adiciona set-point
            #TODO:

            #ax1.axhline(y=header.get('Massa ETO:', 0), xmin=0, color='black', linestyle='--', label=f"Set-Point: {header.get('Massa ETO:', 0)}")

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
            _logger.error(f"Erro ao gerar gráfico AFR14 MedPlast: {str(e)}")
            cycle_graph = False
            return cycle_graph
