from queue import PriorityQueue as PQ

# one event is related to one job


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


class Simulator:
    def __init__(self, ti, tf, file_name):
        self.ti = ti
        self.tf = tf
        self.event_queue = PQ()
        self.__initial_events(file_name)

    def __initial_events(self, file_name):
        # todo adicionar leitura de CSV
        try:
            file = open(file_name, 'r', )

            file.close()
        except:
            print("arquivo de eventos iniciais não encontrado")

    def run(self):
        while not self.event_queue.empty():
            event = self.event_queue.get()
            self.treat_event(event)

    def treat_event(self, event):
        if event.name == 'espera_memoria':
            print("TODO aloca memoria")


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