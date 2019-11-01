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
    print("-------------------------------------------------------------------")
    # print("Event Info")
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
    def __init__(self, job_name):
        self.segment_list = []
        self.segment_queue = PriorityQueue()
        # list of truples with (segment_id, (start_address, end_address))
        self.memory_partitions = []
        self.name = job_name
        self.internal_time = 0

    def schedule_next_event(self, simulator):
        print("Tempo do evento {} Tempo atual {}".format(self.segment_queue.queue[0].time, self.internal_time))
        try:
            while self.segment_queue.queue[0].time <= self.internal_time:
                print("Disparando evento")
                request = self.segment_queue.get()
                print(request.name)
                # determina tipo de evento
                if request.name == 'referencia':
                    # cria evento de requisicao de memoria
                    request.job.is_sleeping = False
                    simulator.event_queue.put(Event('entrada', simulator.t_current, request.job))
                elif request.name == 'adormece':
                    request.job.is_sleeping = True
                else:
                    request.job.is_sleeping = False
                    if request.job.wakeup_event is not None:
                       simulator.event_queue.put(request.job.wakeup_event)
                       request.job.wakeup_event = None
                try: 
                    print("Próximo evento {}".format(self.segment_queue.queue[0].time))
                except:
                    print("Fila vazia")
        except:
            print("Sem evento na fila")

class JobSegment:
    def __init__(self, name, memory_needed, input_needed, output_needed, input_interval, output_interval, initial_time,
                 input_time, output_time, disk_needed, disk_interval, disk_time, cpu_time=0, father_job=None):
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
        self.IsActive = False
        self.father_job = father_job
        self.is_sleeping = False
        self.wakeup_event = None


class Simulator:
    def __init__(self, ti, tf, file_name, round_roubin_interval=5):
        self.ti = int(ti)
        self.tf = int(tf)
        self.t_current = 0
        self.event_queue = PriorityQueue()
        # adiciona lista de Jobs
        self.job_list = []
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
        self.is_sleeping = False
        self.round_robin_queue = Queue()
        self.round_roubin_interval = round_roubin_interval
        self.cpu_ocuppied = False
        print("Dump no formato")
        print("<Instante> <Tipo de Evento> <Programa> <Acao> <Resultado>")

    def __initial_events(self, file_name):
        try:
            with open(file_name) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                line_count = 0
                old_job = ""
                job = None
                for row in csv_reader:
                    # primeira linha é o cabecalho
                    if line_count > 0:
                        if debug:
                            print(
                                "Line name{} memory_needed {} input_needed {} output_needed{} input_interval{} output_interval{} initial_time{} input_time{} output_time{} disk_needed{} disk_interval {} disk_time {} cpu_time{} ".format(
                                    row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                                    row[7], row[8], row[9], row[10], row[11], row[12]));
                        # verifica se é um novo job
                        if old_job != row[0]:
                            old_job = row[0]
                            #coloca primeiro evento de solicitacao de segmento na fila de eventos globais
                            if job is not None:
                                self.first_segment(job)
                            # novo Job foi criado
                            job = Job(row[0])
                            # adiciona Job a lista de Jobs do sistema
                            self.job_list.append(job)
                            # cria segmento
                            new_job = JobSegment(row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                                                 row[7], row[8], row[9], row[10], row[11], row[12], job)
                            job.segment_list.append(new_job)
                        else:
                            # continue preenchendo lista de segmentos
                            new_job = JobSegment(row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                                                 row[7], row[8], row[9], row[10], row[11], row[12], job)
                            job.segment_list.append(new_job)
                    else:
                        line_count = 1
            csv_file.close()
        except:
            print("erro ao ler csv :(")

    def first_segment(self, job):
        # tenta ler csv
        try:
            with open(job.name+".csv") as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                line_count = 0
                for row in csv_reader:
                    # primeira linha é o cabecalho
                    if line_count > 0:
                        # adiciona evento na fila do Job
                        job.segment_queue.put(Event(row[0], int(row[1]), job.segment_list[int(row[2])]))
                    else:
                    # pula cabeçalho
                        line_count = 1

                csv_file.close()
                # coloca primeira solicitação na fila global
                first_request = job.segment_queue.get()
                self.event_queue.put(Event('entrada', first_request.time, first_request.job))
        except:
            print("Erro lendo fila de inicializacao do job {}").format(job.name)

    def run(self):
        while not self.event_queue.empty() and self.t_current < self.tf:
            event = self.event_queue.get()
            if self.t_current < event.time:
                self.t_current = event.time
            else:
                # nao processa mais de um evento por vez
                self.t_current += 1
            dump_event(event, self)
            result = self.treat_event(event)
            # print("Resultado da alteracao")
            print(result)

    def treat_event(self, event):
        if event.name == 'entrada':
            # verifica se o Job está dormindo
            if event.job.is_sleeping:
                event.job.wakeup_event = event
                return "<Job {} dormindo><Removido da lista de entrada>".format(event.job.name)
            # aloca memoria
            if self.malloc(event):
                if debug:
                    print("Ha memoria para o programa")
                self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
                # adiciona proximo evento

                return "<Job {} adicionado como evento de requisicao de CPU><Requisicao de CPU em {}>".format(
                    event.name, event.time)
            else:
                self.memory_queue.put(event)
                if debug:
                    print("Nao ha memoria")
            # atualiza horario da simulacao
            if self.t_current < event.time:
                # nao retrocede o relogio
                self.t_current = event.time
            return "<Coloca job {} na fila de memoria> <Fila atualizada>".format(event.job.name)

        elif event.name == 'requisita_cpu':
            #if self.cpu_avaliable > 0:
            if self.t_current < event.time:
                # nao retrocede o relogio
                self.t_current = event.time
            # verifica se o Job está dormindo
            if event.job.is_sleeping:
                event.job.wakeup_event = event
                return "<Job {} dormindo><Removido da lista de entrada>".format(event.job.name)
            # atualiza tempo corrente
            event.job.cpu_gained = self.t_current
            # atualiza requisicoes de recursos
            event.job.next_input = self.t_current + event.job.input_interval
            event.job.next_output = self.t_current + event.job.output_interval
            event.job.next_disk = self.t_current + event.job.disk_interval
            if debug:
                print("CPU gained at {}".format(event.job.cpu_gained))
            # determina qual o primeiro evento de entrada e saida sera realizado
            next_event = self.return_next_event(event)
            # coloca na fila da CPU
            if not self.cpu_ocuppied:
                self.event_queue.put(next_event)
                self.cpu_ocuppied = True
            else:
                self.cpu_queue.put(next_event)
                #self.event_queue.put(self.cpu_queue.get())
            # diminui o número de cpus
            #self.cpu_avaliable -= 1
            next_event.job.IsActive = True
            return "<Evento {} na fila em {}s><CPU alocada para o JOB {}>".format(next_event.name, next_event.time,
                                                                                  event.job.name)
#            else:
#                if self.t_current < event.time:
                    # nao retrocede o relogio
#                    self.t_current = event.time
                # verifica se o Job está dormindo
#                if event.job.is_sleeping:
#                    event.job.wakeup_event = event
#                    return "<Job {} dormindo><Removido da lista de entrada>".format(event.job.name)
                    
                # coloca job na ready list
 #               self.cpu_queue.put(event)
 #               event.job.IsActive = False
 #               return "<Nao ha CPU disponivel para a execucao de {}> <JOB colocado na fila de cpu>".format(
 #                   event.job.name)

        elif event.name == 'requisita_disco':
            # libera CPU
            # verifica se o Job está dormindo
            if event.job.is_sleeping:
                event.job.wakeup_event = event
                return "<Job {} dormindo><Removido da lista de entrada>".format(event.job.name)
            if event.job.IsActive:
                self.cpu_avaliable += 1
                if not self.cpu_queue.empty():
                    if debug:
                        print("Job recolocado na fila")
                    self.event_queue.put(self.cpu_queue.get())
            # atualiza tempo da simulacao
            if self.t_current < event.time:
                # nao retrocede o relogio
                self.t_current = event.time
            # atualiza tempo de cpu do job
            if event.job.IsActive:
                event.job.IsActive = False
                cpu_time_old = event.job.cpu_time
                event.job.cpu_time -= self.t_current - event.job.cpu_gained

                if debug:
                    print("Job gained {} cpu time".format(self.t_current - event.job.cpu_gained))
                if event.job.cpu_time < 0:
                    event.job.cpu_time = 0
                # atualiza estado do Job pai
                event.job.father_job.internal_time += cpu_time_old - event.job.cpu_time
                event.job.father_job.schedule_next_event(self)

            if self.disk_avaliable > 0:
                if debug:
                    print("Disco disponivel")
                self.disk_avaliable -= 1
                self.event_queue.put(Event('libera_disco', self.t_current + event.job.disk_time, event.job))
                return "<Job {} ganhou acesso ao disco ate {}> <CPU liberada, disco alocado>".format(event.job.name,
                                                                                                     self.t_current + event.job.disk_time)
            else:
                self.disk_queue.put(event)
                return "<Job {} nao pode acessar disco><Job adicionado a fila de disco>".format(event.job.name)

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
            # verifica se o Job está dormindo
            if event.job.is_sleeping:
                event.job.wakeup_event = event
                return "<Job {} dormindo><Removido da lista de entrada>".format(event.job.name)
            # libera CPU
            if event.job.IsActive:
                self.cpu_avaliable += 1
                if not self.cpu_queue.empty():
                    if debug:
                        print("Job recolocado na fila")
                    self.event_queue.put(self.cpu_queue.get())
            # atualiza tempo da simulacao
            if self.t_current < event.time:
                # nao retrocede o relogio
                self.t_current = event.time
            if event.job.IsActive:
                # atualiza tempo de cpu do job
                cpu_time_old = event.job.cpu_time
                event.job.cpu_time -= self.t_current - event.job.cpu_gained
                event.job.IsActive = False
                if event.job.cpu_time < 0:
                    event.job.cpu_time = 0

                event.job.father_job.internal_time += cpu_time_old - event.job.cpu_time
                event.job.father_job.schedule_next_event(self)

                if debug:
                    print("Job gained {} cpu time.\r\nMissing {} cpu time".format(self.t_current - event.job.cpu_gained,
                                                                                  event.job.cpu_time))

            if self.input_avaliable > 0:
                if debug:
                    print("Entrada disponivel disponivel")
                self.input_avaliable -= 1
                next_event = Event('libera_entrada', self.t_current + event.job.input_time, event.job)
                self.event_queue.put(next_event)
                return "<Job {} ganhou acesso a entrada {} ate {}><CPU liberada, entrada alocada>".format(
                    event.job.name, self.input_avaliable, next_event.time)
            else:
                self.input_queue.put(event)
                return "<Job {0} nao pode acessar entrada><Job adicionado a fila de entrada>".format(event.job.name)

        elif event.name == 'libera_entrada':
            self.input_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            # verifica fila de disco
            if not self.input_queue.empty():
                self.event_queue.put(self.input_queue.get())
            # recoloca job na readylist
            self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
            return "<JOB {} devolveu entrada> <JOB recolocado na readylist>".format(event.job.name)
        elif event.name == 'requisita_saida':
            # libera CPU
            if event.job.IsActive:
                self.cpu_avaliable += 1
                if not self.cpu_queue.empty():
                    if debug:
                        print("Job recolocado na fila")
                    self.event_queue.put(self.cpu_queue.get())

            # atualiza tempo da simulacao
            if self.t_current < event.time:
                # nao retrocede o relogio
                self.t_current = event.time
            # atualiza tempo de cpu do job
            if event.job.IsActive:
                event.job.IsActive = False
                cpu_time_old = event.job.cpu_time
                event.job.cpu_time -= self.t_current - event.job.cpu_gained
                if event.job.cpu_time < 0:
                    event.job.cpu_time = 0

                event.job.father_job.internal_time += cpu_time_old - event.job.cpu_time
                event.job.father_job.schedule_next_event(self)

            if self.output_avaliable > 0:
                if debug:
                    print("Saida disponivel disponivel")
                self.output_avaliable -= 1
                self.event_queue.put(Event('libera_saida', self.t_current + event.job.output_time, event.job))
                return "<Job {} ganhou acesso a saida por {} s><CPU liberada, saida alocada>".format(event.job.name,
                                                                                                     event.job.output_time)
            else:
                self.output_queue.put(event)
                return "<Job {} nao pode acessar entrada><Job adicionado a fila de entrada>".format(event.job.name)

        elif event.name == 'libera_saida':
            self.output_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            # verifica fila de disco
            if not self.output_queue.empty():
                self.event_queue.put(self.output_queue.get())
            # recoloca job na readylist
            self.event_queue.put(Event('requisita_cpu', self.t_current, event.job))
            return "<JOB {} devolveu saida> <JOB recolocado na readylist>".format(event.job.name)

        elif event.name == 'finaliza_processamento':
            # devolve CPU
            # self.cpu_avaliable += 1
            if self.t_current < event.time:
                self.t_current = event.time
            if not self.cpu_queue.empty():
                self.event_queue.put(self.cpu_queue.get())
            else:
                # não tem mais processos utilizando a CPU
                self.cpu_ocuppied = False
            self.free(event)
            # atualiza estado do Job pai
            event.job.father_job.internal_time += event.job.cpu_time
            event.job.father_job.schedule_next_event(self)
            event.job.cpu_time = 0
            return "<Job {} finalizado!><CPU liberada! {} blocos de memoria liberados>".format(event.job.name,
                                                                                               event.job.memory_needed)
        elif event.name == 'mudanca_contexto':
            # atualiza instante da simulacao
            if self.t_current < event.time:
                self.t_current = event.time
            # atualiza tempo de processamento 
            cpu_time_old = event.job.cpu_time
            event.job.cpu_time -= self.t_current - event.job.cpu_gained
            event.job.father_job.internal_time += cpu_time_old - event.job.cpu_time
            event.job.father_job.schedule_next_event(self)
            # adiciona proximo evento solicitado pelo Job na fila 
            self.cpu_queue.put(self.return_next_event(event))
            # adiciona proximo evento da fila na fila global
            self.event_queue.put(self.cpu_queue.get())

    '''
        Returns next event for job and update job's status
    '''

    def return_next_event(self, event):
        if event.job.disk_needed > 0 and event.job.input_needed > 0 and event.job.output_needed > 0:
            if event.job.next_input < event.job.next_output:
                if event.job.next_input < event.job.next_disk:
                    new_event = 'requisita_entrada'
                    event_time = event.job.next_input
                    event.job.input_needed -= 1
                    if event.job.input_needed > 0:
                        event.job.next_input = self.t_current + event.job.input_interval
                else:
                    new_event = 'requisita_disco'
                    event_time = event.job.next_disk
                    event.job.disk_needed -= 1
                    if event.job.disk_needed > 0:
                        event.job.next_disk = self.t_current + event.job.disk_interval
            else:
                if event.job.next_output < event.job.next_disk:
                    new_event = 'requisita_saida'
                    event_time = event.job.next_output
                    event.job.output_needed -= 1
                    if event.job.output_needed > 0:
                        event.job.next_output = self.t_current + event.job.output_interval
                else:
                    new_event = 'requisita_disco'
                    event_time = event.job.next_disk
                    event.job.disk_needed -= 1
                    if event.job.disk_needed > 0:
                        event.job.next_disk = self.t_current + event.job.disk_interval
        elif event.job.input_needed > 0 and event.job.output_needed > 0:

            if event.job.next_input < event.job.next_output:
                new_event = 'requisita_entrada'
                event_time = event.job.next_input
                event.job.input_needed -= 1
                if event.job.input_needed > 0:
                    event.job.next_input = self.t_current + event.job.input_interval
            else:
                new_event = 'requisita_saida'
                event_time = event.job.next_output
                event.job.output_needed -= 1
                if event.job.output_needed > 0:
                    event.job.next_output = self.t_current + event.job.output_interval

        elif event.job.input_needed > 0 and event.job.disk_needed > 0:
            if event.job.next_input < event.job.next_disk:
                new_event = 'requisita_entrada'
                event_time = event.job.next_input
                event.job.input_needed -= 1
                if event.job.input_needed > 0:
                    event.job.next_input = self.t_current + event.job.input_interval
            else:
                new_event = 'requisita_disco'
                event_time = event.job.next_disk
                event.job.disk_needed -= 1
                if event.job.disk_needed > 0:
                    event.job.next_disk = self.t_current + event.job.disk_interval

        elif event.job.disk_needed > 0 and event.job.output_needed > 0:
            if event.job.next_disk < event.job.next_output:
                new_event = 'requisita_disco'
                event_time = event.job.next_disk
                event.job.disk_needed -= 1
                if event.job.disk_needed > 0:
                    event.job.next_disk = self.t_current + event.job.disk_interval
            else:
                new_event = 'requisita_saida'
                event_time = event.job.next_output
                event.job.output_needed -= 1
                if event.job.output_needed > 0:
                    event.job.next_output = self.t_current + event.job.output_interval

        elif event.job.input_needed > 0:
            new_event = 'requisita_entrada'
            event_time = event.job.next_input
            event.job.input_needed -= 1
            if event.job.input_needed > 0:
                event.job.next_input = self.t_current + event.job.input_interval

        elif event.job.output_needed > 0:
            new_event = 'requisita_saida'
            event_time = event.job.next_output
            event.job.output_needed -= 1
            if event.job.output_needed > 0:
                event.job.next_output = self.t_current + event.job.output_interval

        elif event.job.disk_needed > 0:
            new_event = 'requisita_disco'
            event_time = event.job.next_disk
            event.job.disk_needed -= 1
            if event.job.disk_needed > 0:
                event.job.next_disk = self.t_current + event.job.disk_interval
        else:  # fim da execucao
            new_event = 'finaliza_processamento'
            event_time = self.t_current + event.job.cpu_time
        # verifica o que retorna primeiro, proximo evento ou troca de contexto
        if event_time < self.t_current + self.round_roubin_interval:
            return Event(new_event, event_time, event.job)
        else:
            print("Agendado mudanca de contexto")
            return Event('mudanca_contexto', self.t_current + self.round_roubin_interval, event.job)
            
    def free(self, event):
        for i in range(event.job.start_memory, event.job.memory_needed):
            self.memory_blocks[i] = 0
        self.memory_avaliable += event.job.memory_needed
        if not self.memory_queue.empty():
            self.event_queue.put(self.memory_queue.get())

    def malloc(self, event):
        # verifica se existe memoria disponivel
        # politica de alocacao de first fit (busca gulosa)
        if self.memory_avaliable > event.job.memory_needed:
            # verifica se existe uma regiao contigua de memoria para o processo
            iaux_2 = 0
            iaux = 0
            memory_space = 0
            while iaux < len(self.memory_blocks):
                if self.memory_blocks[iaux] == 0:
                    memory_space += 1
                    if memory_space >= event.job.memory_needed:
                        # encontrou memoria
                        if debug:
                            print("Encontrou bloco de memoria iniciando em %d" % iaux_2)
                        event.job.start_memory = iaux_2
                        # marca bloco como ocupado
                        for i in range(iaux_2, iaux_2 + event.job.memory_needed):
                            self.memory_blocks[i] = 1
                        self.memory_avaliable -= event.job.memory_needed
                        return True
                else:
                    # Avanca iAux até proxima posicao livre
                    while iaux < len(self.memory_blocks) and self.memory_blocks[iaux] == 1:
                        iaux += 1
                    if iaux == len(self.memory_blocks):
                        if debug:
                            print("Nao ha memoria disponivel")
                        return False
                    iaux -= 1
                    iaux_2 = iaux
                    pass
                iaux += 1


def main():
    # coleta dados dos usuarios
    ti = input("Tempo inicial de relogio: ")
    tf = input("Tempo final da simulacao: ")
    fila_name = input("Nome do arquivo: ")
    simulator = Simulator(ti, tf, file_name=fila_name)
    simulator.run()
    print("simulacao chegou ao fim")


if __name__ == '__main__':
    main()
