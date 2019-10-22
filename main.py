from queue import PriorityQueue
from queue import Queue
import numpy as np
import csv

# debug variables
debug = False
''' one event is related to one job
 only dumps event and job information
'''
def dump_event(event, simulator):
    print("-------------------------------------------------------------------")
    print("Event Info")
    print("<%d> <%s> <%s> " % (simulator.t_current, event.name, event.job.name))


class Event:
    '''
    (name, time, job)
    '''
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
        if self.time > other.time:
            return -1
        elif self.time < other.time:
            return 1
        else:
            return 0

    def __lt__(self, other):
        return self.time < other.time


class Job:
    def __init__(self, name, memory_needed, input_needed, output_needed, input_interval, output_interval, initial_time,
                 input_time, output_time, disk_needed, disk_interval, disk_time, cpu_time=0):
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
        self.disk_needed = int(disk_needed)
        self.state = ['esperando_submissao']
        self.initial_time = int(initial_time)
        self.next_input = 0
        self.next_output = 0
        self.next_disk = 0
        self.cpu_time = int(cpu_time)
        self.cpu_gained = 0
        self.start_memory = 0


class Simulator:
    def __init__(self, ti, tf, file_name):
        self.ti = int(ti)
        self.tf = int(tf)
        self.t_current = 0
        self.event_queue = PriorityQueue()
        self.__initial_events(file_name)
        # recursos
        self.memory_queue = Queue()
        self.memory_avaliable = 1024
        # array with occupied blocks
        self.memory_blocks = np.zeros(1024)
        self.cpu_queue = Queue()
        self.cpu_avaliable = 1
        self.disk_queue = Queue()
        self.input_queue = Queue()
        self.input_avaliable = 2
        self.output_queue = Queue()
        self.output_avaliable = 2
        self.disk_avaliable = 1
        print("Dump no formato")
        print("<Instante> <Tipo de Evento> <Programa> <Ação> <Resultado>")

    def __initial_events(self, file_name):
        # todo adicionar leitura de CSV
        try:
            with open(file_name) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                line_count = 0
                for row in csv_reader:
                    # primeira linha é o cabeçalho
                    if line_count > 0:
                        new_job = Job(row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                                      row[7], row[8], row[9], row[10], row[11], row[12])
                        new_event = Event('entrada', new_job.initial_time, new_job)
                        self.event_queue.put(new_event)
                        if debug:
                            print("Evento enfileirado: <%s> <%s>" % (new_job.name, new_event.name))
                    else:
                        line_count = 1
            csv_file.close()
        except:
            print("erro ao ler csv :(")

    def run(self):
        while not self.event_queue.empty() and self.t_current < self.tf:
            event = self.event_queue.get()
            if self.t_current < event.time:
                self.t_current = event.time
            else:
                # não processa mais de um evento por vez
                self.t_current += 1
            dump_event(event, self)
            result = self.treat_event(event)
            print("Resultado da alteracao")
            print(result)

    def treat_event(self, event):
        if event.name == 'entrada':
            if self.malloc(event):
                if debug:
                    print("Há memoria para o programa")
                self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
                # adiciona proximo evento

                return "<Job {} adicionado como evento de requisicao de CPU>".format(event.name)
            else:
                self.memory_queue.put(event)
                if debug:
                    print("Não há memória")
            # atualiza horario da simulacao
            if self.t_current < event.time:
                # não retrocede o relogio
                self.t_current = event.time
            return "<Coloca job {} na fila de memoria> <Fila atualizada>".format(event.job.name)

        elif event.name == 'requisita_cpu':
            if self.cpu_avaliable > 0:
                # determina qual o primeiro evento de entrada e saida sera realizado
                next_event = self.return_next_event(event)
                self.event_queue.put(next_event)
                # atualiza tempo corrente 
                event.job.cpu_gained = self.t_current
                # diminui o número de cpus
                self.cpu_avaliable -= 1
                if self.t_current < event.time:
                    # não retrocede o relogio
                    self.t_current = event.time
                return "<Evento {} na fila><CPU alocada para o JOB {}>".format(event.name, event.job.name)
            else:
                # coloca job na ready list
                self.cpu_queue.put(event)
                if self.t_current < event.time:
                    # não retrocede o relogio
                    self.t_current = event.time
                return "<Não há CPU disponível para a execução de {}> <JOB colocado na fila de cpu>".format(event.job.name)

        elif event.name == 'requisita_disco':
            # libera CPU
            self.cpu_avaliable += 1
            if not self.cpu_queue.empty():
                if debug:
                    print("Job recolocado na fila")
                self.event_queue.put(self.cpu_queue.get())
            # atualiza tempo da simulação
            if self.t_current < event.time:
                # não retrocede o relogio
                self.t_current = event.time
            # atualiza tempo de cpu do job
            event.job.cpu_time -= self.t_current - event.job.cpu_gained
            if event.job.cpu_time < 0:
                event.job.cpu_time = 0

            if self.disk_avaliable > 0:
                if debug:
                    print("Disco disponivel")
                self.disk_avaliable -= 1
                self.event_queue.put(Event('libera_disco', self.t_current + event.job.disk_interval, event.job))
                return "<Job {} ganhou acesso ao disco> <CPU liberada, disco alocado>".format(event.job.name)
            else:
                self.disk_queue.put(event)
                return "<Job {} não pode acessar disco><Job adicionado a fila de disco>".format(event.job.name)

        elif event.name == 'libera_disco':
            self.disk_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            # verifica fila de disco
            if not self.disk_queue.empty():
                self.event_queue.put(self.disk_queue.get())
            # recoloca job na readylist
            self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
            return "<JOB {} devolveu disco> <JOB recolocado na readylist>".format(event.name)

        elif event.name == 'requisita_entrada':
            # libera CPU
            self.cpu_avaliable += 1
            if not self.cpu_queue.empty():
                if debug:
                    print("Job recolocado na fila")
                self.event_queue.put(self.cpu_queue.get())
            # atualiza tempo da simulação
            if self.t_current < event.time:
                # não retrocede o relogio
                self.t_current = event.time
            # atualiza tempo de cpu do job
            event.job.cpu_time -= self.t_current - event.job.cpu_gained
            if event.job.cpu_time < 0:
                event.job.cpu_time = 0

            if self.input_avaliable > 0:
                if debug:
                    print("Entrada disponível disponivel")
                self.input_avaliable -= 1
                self.event_queue.put(Event('libera_entrada', self.t_current + event.job.input_interval, event.job))
                return "<Job {} ganhou acesso a entrada><CPU liberada, entrada alocada>".format(event.job.name)
            else:
                self.input_queue.put(event)
                return "<Job {0} não pode acessar entrada><Job adicionado a fila de entrada>".format(event.job.name)

        elif event.name == 'libera_entrada':
            self.input_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            # verifica fila de disco
            if not self.input_queue.empty():
                self.event_queue.put(self.input_queue.get())
            # recoloca job na readylist
            self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
            return "<JOB {} devolveu disco> <JOB recolocado na readylist>"
        elif event.name == 'requisita_saida':
            # libera CPU
            self.cpu_avaliable += 1
            if not self.cpu_queue.empty():
                if debug:
                    print("Job recolocado na fila")
                self.event_queue.put(self.cpu_queue.get())
            # atualiza tempo da simulação
            if self.t_current < event.time:
                # não retrocede o relogio
                self.t_current = event.time
            # atualiza tempo de cpu do job
            event.job.cpu_time -= self.t_current - event.job.cpu_gained
            if event.job.cpu_time < 0:
                event.job.cpu_time = 0

            if self.output_avaliable > 0:
                if debug:
                    print("Saida disponível disponivel")
                self.output_avaliable -= 1
                self.event_queue.put(Event('libera_saida', self.t_current + event.job.input_interval, event.job))
                return "<Job {} ganhou acesso a saida><CPU liberada, saida alocada>".format(event.job.name)
            else:
                self.output_queue.put(event)
                return "<Job {} não pode acessar entrada><Job adicionado a fila de entrada>".format(event.job.name)

        elif event.name == 'libera_saida':
            self.output_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            # verifica fila de disco
            if not self.output_queue.empty():
                self.event_queue.put(self.output_queue.get())
            # recoloca job na readylist
            self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
            return "<JOB {} devolveu saida> <JOB recolocado na readylist>"

        elif event.name == 'finaliza_processamento':
            # devolve CPU
            self.cpu_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            if not self.cpu_queue.empty():
                self.event_queue.put(self.cpu_queue.get())
            self.free(event)
            return "<Job {} finalizado!><CPU liberada! {} blocos de memória liberados>".format(event.job.name,
                                                                                               event.job.memory_needed)
    '''
        Returns next event for job and update job's status
    '''
    @staticmethod
    def return_next_event(event):
        if event.job.disk_needed > 0 and event.job.input_needed > 0 and event.job.output_needed > 0:
            if event.job.next_input < event.job.next_output:
                if event.job.next_input < event.job.next_disk:
                    new_event = 'requisita_entrada'
                    event_time = event.job.next_input
                    event.job.input_needed -= 1
                    if event.job.input_needed > 0:
                        event.job.next_input = event.time + event.job.input_interval
                else:
                    new_event = 'requisita_disco'
                    event_time = event.job.next_disk
                    event.job.disk_needed -= 1
                    if event.job.disk_needed > 0:
                        event.job.next_disk = event.time + event.job.disk_interval
            else:
                if event.job.next_output < event.job.next_disk:
                    new_event = 'requisita_saida'
                    event_time = event.job.next_output
                    event.job.output_needed -= 1
                    if event.job.output_needed > 0:
                        event.job.next_output = event.time + event.job.output_interval
                else:
                    new_event = 'requisita_disco'
                    event_time = event.job.next_disk
                    event.job.disk_needed -= 1
                    if event.job.disk_needed > 0:
                        event.job.next_disk = event.time + event.job.disk_interval
        elif event.job.input_needed > 0 and event.job.output_needed > 0:

            if event.job.next_input < event.job.next_output:
                new_event = 'requisita_entrada'
                event_time = event.job.next_input
                event.job.input_needed -= 1
                if event.job.input_needed > 0:
                    event.job.next_input = event.time + event.job.input_interval
            else:
                new_event = 'requisita_saida'
                event_time = event.job.next_output
                event.job.output_needed -= 1
                if event.job.output_needed > 0:
                    event.job.next_output = event.time + event.job.output_interval

        elif event.job.input_needed > 0 and event.job.disk_needed > 0:
            if event.job.next_input < event.job.next_disk:
                new_event = 'requisita_entrada'
                event_time = event.job.next_input
                event.job.input_needed -= 1
                if event.job.input_needed > 0:
                    event.job.next_input = event.time + event.job.input_interval
            else:
                new_event = 'requisita_disco'
                event_time = event.job.next_disk
                event.job.disk_needed -= 1
                if event.job.disk_needed > 0:
                    event.job.next_disk = event.time + event.job.disk_interval

        elif event.job.disk_needed > 0 and event.job.output_needed > 0:
            if event.job.next_disk < event.job.next_output:
                new_event = 'requisita_disco'
                event_time = event.job.next_disk
                event.job.disk_needed -= 1
                if event.job.disk_needed > 0:
                    event.job.next_disk = event.time + event.job.disk_interval
            else:
                new_event = 'requisita_saida'
                event_time = event.job.next_output
                event.job.output_needed -= 1
                if event.job.output_needed > 0:
                    event.job.next_output = event.time + event.job.output_interval

        elif event.job.input_needed > 0:
            new_event = 'requisita_entrada'
            event_time = event.job.next_input
            event.job.input_needed -= 1
            if event.job.input_needed > 0:
                event.job.next_input = event.time + event.job.input_interval

        elif event.job.output_needed > 0:
            new_event = 'requisita_saida'
            event_time = event.job.next_output
            event.job.output_needed -= 1
            if event.job.output_needed > 0:
                event.job.next_output = event.time + event.job.output_interval

        elif event.job.disk_needed > 0:
            new_event = 'requisita_disco'
            event_time = event.job.next_disk
            event.job.disk_needed -= 1
            if event.job.disk_needed > 0:
                event.job.next_disk = event.time + event.job.disk_interval
        else: # fim da execucao
            new_event = 'finaliza_processamento'
            event_time = event.time + event.job.cpu_time

        return Event(new_event, event_time, event.job)

    def free (self, event):
        for i in range(event.job.start_memory, event.job.memory_needed):
            self.memory_blocks[i] = 1
        self.memory_avaliable += event.job.memory_needed

    def malloc(self, event):
        # verifica se existe memoria disponivel
        # politica de alocacao de first fit (busca gulosa)
        if self.memory_avaliable > event.job.memory_needed:
            # verifica se existe uma região contigua de memoria para o processo
            iaux_2 = 0
            iaux = 0
            memory_space = 0
            while iaux < len(self.memory_blocks):
                iaux += 1
                if self.memory_blocks[iaux] == 0:
                    memory_space += 1
                    if memory_space >= event.job.memory_needed:
                        # encontrou memoria
                        if debug:
                            print("Encontrou bloco de memoria iniciando em %d" % iaux_2)
                        event.job.start_memory = iaux_2
                        # marca bloco como ocupado
                        for i in range(iaux_2, iaux_2+event.job.memory_needed):
                            self.memory_blocks[i] = 1
                        self.memory_avaliable -= event.job.memory_needed
                        return True
                else:
                    # Avança iAux até proxima posicao livre
                    while iaux < len(self.memory_blocks) and self.memory_blocks[iaux] == 1:
                        iaux += 1
                    if iaux == len(self.memory_blocks):
                        if debug:
                            print("Não há memória disponível")
                        return False
                    iaux -= 1
                    iaux_2 = iaux


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