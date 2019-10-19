from queue import PriorityQueue
from queue import Queue
import numpy as np
import csv

# debug variables
debug = True
''' one event is related to one job
 only dumps event and job information
'''
def dump_event(event, simulator):
    print("Event Info")
    print("<%d> <%s> <%s> " % (simulator.t_current, event.name, event.job.name))


class Event:
    def __init__(self, name, time, job):
        self.name = name
        self.time = time
        self.job = job

    def __eq__(self, other):
        if not isinstance(other, Event):
            return False
        return self.time == other.time

    def __cmp__(self, other):
        if not isinstance(other, Event):
            return 0
        return self.time - other.time


class Job:
    def __init__(self, name, memory_needed, input_needed, output_needed, input_interval, output_interval, initial_time,
                 input_time, output_time, disk_needed, disk_interval, disk_time):
        self.name = name
        self.memory_needed = int(memory_needed)
        self.input_needed = int(input_needed)
        self.output_needed = int(output_needed)
        self.input_interval = int(input_interval)
        self.output_interval = int(output_interval)
        self.input_time = int(input_time)
        self.output_time = int(output_time)
        self.disk_interval = int(disk_interval)
        self.disk_time = int(disk_time)
        self.disk_needed = disk_needed
        self.state = ['esperando_submissao']
        self.initial_time = int(initial_time)


class Simulator:
    def __init__(self, ti, tf, file_name):
        self.ti = ti
        self.tf = tf
        self.t_current = 0
        self.event_queue = PriorityQueue()
        self.__initial_events(file_name)
        # recursos
        self.memory_queue = Queue()
        self.memory_avaliable = 1024
        # array with occupied blocks
        self.memory_blocks = np.zeros(1024)
        self.cpu_queue = Queue()
        self.disk_queue = Queue()
        self.input_queue = Queue()
        self.input_avaliable = 2
        self.output_queue = Queue()
        self.output_avaliable = 2
        print("Dump no formato")
        print("<Instante> <Tipo de Evento> <Programa> <Ação> <Resultado>")

    def __initial_events(self, file_name):
        # todo adicionar leitura de CSV
        try:
            with open(file_name) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=';')
                line_count = 0
                for row in csv_reader:
                    # primeira linha é o cabeçalho
                    if line_count > 0:
                        new_job = Job(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
                                      row[8], row[9], row[10], row[11])
                        new_event = Event('entrada', new_job.initial_time, new_job)
                        self.event_queue.put(new_event)
                        if debug:
                            print("Evento enfileirado: <%s> <%s>" %(new_job.name, new_event.name))
            csv_file.close()
        except:
            print("arquivo de eventos iniciais não encontrado")

    def run(self):
        while not self.event_queue.empty():
            event = self.event_queue.get()
            dump_event(event)
            result = self.treat_event(event)
            print("Resultado da alteracao")
            print(result)

    def treat_event(self, event):
        if debug:
            if event.name == 'entrada':
                if self.malloc(event):
                    if debug:
                        print("Há memoria para o programa")
                else:
                    if debug:
                        print("Não há memória")

                return "<Coloca job na fila> <Fila atualizada>"


def main():
    # coleta dados dos usuários
    ti = input("Tempo inicial de relógio")
    tf = input("Tempo final da simulação")
    fila_name = input("Nome dos arquivos")
    simulator = Simulator(ti, tf, file_name=fila_name)
    simulator.run()
    print("simulação chegou ao fim")


if __name__ == '__main__':
    main()
