from datetime import datetime, timedelta

import holidays
"""
Classe SchedulePreventive

Descrição:
Esta classe permite gerar agendamentos de tarefas preventivas com considerações de feriados e outros compromissos.

Autor: Afonso Flávio Ribeiro de Carvalho
Versão: 1.0
"""
# Caso de Uso: Agendamento de Manutenção Preventiva de Equipamentos

# Descrição:
# Neste caso de uso, estamos criando um sistema de agendamento de manutenção preventiva para equipamentos em uma empresa.
# A empresa deseja agendar a manutenção preventiva de seus equipamentos de forma eficiente, levando em consideração a disponibilidade
# de horários, feriados e outros compromissos.

# Passos:

# 1. Configurar as variáveis iniciais:
# Criamos uma instância da classe SchedulePreventive para um equipamento específico, como uma impressora.
# Definimos a periodicidade da manutenção como a cada 15 dias, o período de agendamento de 2023-09-27 a 2023-12-31,
# a duração da manutenção como 2 horas, os horários de trabalho da manhã (8:00 às 12:00) e tarde (14:00 às 18:00),
# e uma lista de feriados específicos da empresa.

# printer_maintenance_schedule = SchedulePreventive(
#     name="Impressora da Sala A",
#     periodicity_days=15,
#     start_date="2023-09-27",
#     end_date="2023-12-31",
#     preventive_duration_hours=2,
#     morning_start=8,
#     morning_end=12,
#     afternoon_start=14,
#     afternoon_end=18,
#     holidays=["2023-10-05", "2023-11-25", "2023-12-25"],
# )

# 2. Adicionar outros compromissos:
# Adicionamos à lista de compromissos outros agendamentos que podem coincidir com a manutenção preventiva,
# como reuniões ou tarefas agendadas previamente.

# other_appointments = [
#     (datetime(2023, 10, 10, 10, 0), datetime(2023, 10, 10, 11, 0)),
#     (datetime(2023, 11, 15, 15, 0), datetime(2023, 11, 15, 16, 0)),
# ]

# printer_maintenance_schedule.set_other_appointments(other_appointments)

# 3. Gerar o cronograma de manutenção:
# Usamos o método generate_schedule() para calcular os horários disponíveis para a manutenção
# e atribuímos esses horários à lista de agendamentos.

# printer_maintenance_schedule.generate_schedule()

# 4. Exibir o cronograma de manutenção:
# Exibimos o cronograma de manutenção gerado com base nas configurações e disponibilidade de horários.

# print("Cronograma de Manutenção Preventiva para a Impressora:")
# printer_maintenance_schedule.display_schedule()

# Resultado:
# O sistema gera um cronograma de manutenção preventiva para a impressora, considerando a periodicidade, os horários
# de trabalho, feriados e outros compromissos. Os horários disponíveis para a manutenção são exibidos para a equipe
# de manutenção seguir.

# Observações:
# - O sistema pode ser configurado para várias máquinas e equipamentos, cada um com suas próprias configurações.
# - Os horários de manutenção podem ser ajustados com base em requisitos específicos.
# - O sistema ajuda a evitar conflitos de agendamento e garante que a manutenção ocorra em dias úteis e sem interferir
#   em outros compromissos.

class SchedulePreventive:
    """
    Classe para gerar agendamentos de tarefas preventivas com considerações de feriados e outros compromissos.

    Args:
        name (str): O nome da tarefa preventiva.
        periodicity_days (int): A periodicidade em dias para a programação das tarefas preventivas.
        start_date (str): A data de início no formato 'YYYY-MM-DD'.
        end_date (str): A data de término no formato 'YYYY-MM-DD'.
        preventive_duration_hours (int): A duração da tarefa preventiva em horas.
        morning_start (int): A hora de início do período da manhã.
        morning_end (int): A hora de término do período da manhã.
        afternoon_start (int): A hora de início do período da tarde.
        afternoon_end (int): A hora de término do período da tarde.
        holidays (list): Uma lista de datas no formato 'YYYY-MM-DD' que representam feriados.
        other_appointments (list): Uma lista de tuplas contendo compromissos no formato (hora_início, hora_fim).
        time_increment_minutes (int): O incremento de tempo em minutos para ajustar os agendamentos.

    Attributes:
        name (str): O nome da tarefa preventiva.
        periodicity_days (int): A periodicidade em dias para a programação das tarefas preventivas.
        start_date (datetime): A data de início como objeto datetime.
        end_date (datetime): A data de término como objeto datetime.
        preventive_duration_hours (int): A duração da tarefa preventiva em horas.
        morning_start (int): A hora de início do período da manhã.
        morning_end (int): A hora de término do período da manhã.
        afternoon_start (int): A hora de início do período da tarde.
        afternoon_end (int): A hora de término do período da tarde.
        schedule (list): Uma lista de tuplas contendo agendamentos no formato (hora_início, hora_fim).
        holidays (list): Uma lista de datas no formato 'YYYY-MM-DD' que representam feriados.
        other_appointments (list): Uma lista de tuplas contendo compromissos no formato (hora_início, hora_fim).
        time_increment_minutes (int): O incremento de tempo em minutos para ajustar os agendamentos.

    Methods:
        set_holidays(holidays): Define a lista de feriados.
        get_holidays(): Obtém a lista de feriados.
        set_schedule(schedule): Define a lista de agendamentos.
        get_schedule(): Obtém a lista de agendamentos.
        set_other_appointments(other_appointments): Define a lista de compromissos.
        get_other_appointments(): Obtém a lista de compromissos.
        set_time_increment(time_increment_minutes): Define o incremento de tempo.
        get_time_increment(): Obtém o incremento de tempo.
        generate_schedule(): Gera os agendamentos de tarefas preventivas.
        can_schedule_on_day(current_date): Verifica se é possível agendar em um determinado dia.
        can_schedule_on_range_time_day(schedule_range): Verifica se é possível agendar dentro de uma faixa de horário em um dia.
        display_schedule(): Exibe os agendamentos gerados.
        clear_schedule(): Limpa a lista de agendamentos.

    """

    def __init__(self, name, periodicity_days=7, start_date=None, end_date=None,
                 preventive_duration_hours=1, morning_start=8, morning_end=12,
                 afternoon_start=14, afternoon_end=18, holidays=None,others_day_off=None,
                 other_appointments=None, time_increment_minutes=15):
        # Inicialização dos atributos
        self.name = name
        self.periodicity_days = periodicity_days
        self.start_date = datetime.strptime(
            start_date, '%Y-%m-%d') if start_date else None
        self.end_date = datetime.strptime(
            end_date, '%Y-%m-%d') if end_date else None
        self.preventive_duration_hours = preventive_duration_hours
        self.morning_start = morning_start
        self.morning_end = morning_end
        self.afternoon_start = afternoon_start
        self.afternoon_end = afternoon_end
        self.schedule = []
        self.holidays = holidays if holidays else []
        self.others_day_off = others_day_off if others_day_off else []
        self.other_appointments = other_appointments if other_appointments else []
        self.time_increment_minutes = time_increment_minutes

    # Métodos para definir e obter feriados
    def set_holidays(self, holidays):
        """
        Define a lista de feriados.

        Args:
            holidays (list): Uma lista de datas no formato 'YYYY-MM-DD' que representam feriados.
        """
        self.holidays = holidays

    def get_holidays(self):
        """
        Obtém a lista de feriados.

        Returns:
            list: Uma lista de datas no formato 'YYYY-MM-DD' que representam feriados.
        """
        return self.holidays

    # Métodos para definir e obter a lista de agendamentos
    def set_schedule(self, schedule):
        """
        Define a lista de agendamentos.

        Args:
            schedule (list): Uma lista de tuplas contendo agendamentos no formato (hora_início, hora_fim).
        """
        self.schedule = schedule

    def get_schedule(self):
        """
        Obtém a lista de agendamentos.

        Returns:
            list: Uma lista de tuplas contendo agendamentos no formato (hora_início, hora_fim).
        """
        return self.schedule

    # Métodos para definir e obter a lista de outros compromissos
    def set_other_appointments(self, other_appointments):
        """
        Define a lista de outros compromissos.

        Args:
            other_appointments (list): Uma lista de tuplas contendo compromissos no formato (hora_início, hora_fim).
        """
        self.other_appointments = other_appointments

    def get_other_appointments(self):
        """
        Obtém a lista de outros compromissos.

        Returns:
            list: Uma lista de tuplas contendo compromissos no formato (hora_início, hora_fim).
        """
        return self.other_appointments

    # Métodos para definir e obter o incremento de tempo
    def set_time_increment(self, time_increment_minutes):
        """
        Define o incremento de tempo em minutos.

        Args:
            time_increment_minutes (int): O incremento de tempo em minutos.
        """
        self.time_increment_minutes = time_increment_minutes

    def get_time_increment(self):
        """
        Obtém o incremento de tempo em minutos.

        Returns:
            int: O incremento de tempo em minutos.
        """
        return self.time_increment_minutes

    def generate_schedule(self):
        """
        Gera os agendamentos de tarefas preventivas com base nas configurações fornecidas.
        """
        if not self.start_date or not self.end_date:
            raise ValueError("Please provide valid start_date and end_date.")

        current_date = self.start_date
        while current_date <= self.end_date:
            find_day = True
            while find_day:
                if self.can_schedule_on_day(current_date):
                    preventive_start = current_date.replace(
                        hour=self.morning_start, minute=0, second=0)
                    preventive_end = preventive_start + \
                        timedelta(hours=self.preventive_duration_hours)
                    schedule = (preventive_start, preventive_end)
                    find_range_time = True
                    while find_range_time:
                        if self.can_schedule_on_range_time_day(schedule):
                            find_range_time = False
                            find_day = False
                            self.schedule.append(schedule)
                        else:
                            if (schedule[0] + timedelta(minutes=self.get_time_increment())) > current_date.replace(hour=self.afternoon_end, minute=0, second=0):
                                find_range_time = False
                                current_date += timedelta(days=1)
                                preventive_start = current_date.replace(
                                    hour=self.morning_start, minute=0, second=0)
                                preventive_end = preventive_start + \
                                    timedelta(
                                        hours=self.preventive_duration_hours)
                                schedule = (preventive_start, preventive_end)
                            else:
                                schedule = (schedule[0] + timedelta(minutes=self.get_time_increment(
                                )), schedule[1] + timedelta(minutes=self.get_time_increment()))
                else:
                    current_date += timedelta(days=1)

            current_date += timedelta(days=self.periodicity_days)

    def can_schedule_on_day(self, current_date):
        """
        Verifica se é possível agendar em um determinado dia.

        Args:
            current_date (datetime): A data para verificação.

        Returns:
            bool: True se é possível agendar, False caso contrário.
        """
        if current_date.strftime('%Y-%m-%d') in self.holidays:
            return False
        if current_date.strftime('%Y-%m-%d') in self.others_day_off:
            return False
        return True

    def can_schedule_on_range_time_day(self, schedule_range):
        """
        Verifica se é possível agendar dentro de uma faixa de horário em um dia.

        Args:
            schedule_range (tuple): Uma tupla contendo a hora de início e a hora de fim do agendamento.

        Returns:
            bool: True se é possível agendar, False caso contrário.
        """
        schedule_range_start, schedule_range_end = schedule_range
        # atualizando os limites permitidos para o dia do agendamento
        morning_start = schedule_range_start.replace(hour=self.morning_start, minute=0, second=0)
        morning_end = schedule_range_start.replace(hour=self.morning_end, minute=0, second=0)
        afternoon_start = schedule_range_start.replace(hour=self.afternoon_start, minute=0, second=0)
        afternoon_end = schedule_range_start.replace(hour=self.afternoon_end, minute=0, second=0)

        # Verifica se o range está dentro dos horários permitidos
        if ((schedule_range_start >= morning_start and schedule_range_start <= morning_end)   \
            and (schedule_range_end >= morning_start and schedule_range_end <= morning_end)) \
            or ((schedule_range_start >= afternoon_start and schedule_range_start <= afternoon_end)   \
            and (schedule_range_end >= afternoon_start and schedule_range_end <= afternoon_end)): \
            
            # Verifica se há compromissos na faixa de horário que se está querendo agendar
            for appointment in self.other_appointments:
                appointment_start, appointment_end = appointment
                if (schedule_range_start >= appointment_start  \
                   and schedule_range_start < appointment_end) \
                   or (schedule_range_end > appointment_start  \
                   and schedule_range_end <= appointment_end):
                    print(f"{schedule_range_start} e {schedule_range_end} CONFLITA COM {appointment_start} e {appointment_end}")
                    return False
            return True
        return False
            
             
          

        

       

    def display_schedule(self):
        """
        Exibe os agendamentos gerados.
        """
        if not self.schedule:
            print(f"No schedule generated for {self.name}.")
            return

        for start, end in self.schedule:
            print(
                f"{self.name} from {start.strftime('%H:%M')} to {end.strftime('%H:%M')} on {start.strftime('%Y-%m-%d')}")

    def clear_schedule(self):
        """
        Limpa a lista de agendamentos.
        """
        self.schedule = []


def calcular_divisores(lista):
    """
    Calcula os divisores de cada número na lista que estão contidos na própria lista.

    Args:
        lista (list): Uma lista de números inteiros.

    Returns:
        list: Uma lista de listas, onde cada sublista contém os divisores do número correspondente da entrada.

    Exemplo:
        >>> input_list = [7, 15, 30, 60, 90, 180, 360]
        >>> calcular_divisores(input_list)
        [[], [15], [30, 15], [60, 30, 15], [90, 30, 15], [180, 90, 30, 15], [360, 180, 90, 30, 15]]
    """
    out_list = []

    for numero in lista:
        divisores = []
        for i in range(1, numero + 1):
            if numero % i == 0 and i in lista:  # Verifique se o divisor está na lista
                divisores.append(i)
        out_list.append(divisores)

    return out_list
