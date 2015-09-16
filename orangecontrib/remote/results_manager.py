import threading


class ResultsManager:
    def __init__(self):
        self.results = {}
        self.events = {}

    def set_result(self, id, result):
        self.results[id] = result
        if id in self.events:
            self.events[id].set()

    def get_result(self, id):
        if id in self.events:
            self.events[id].wait()
        return self.results[id]

    def register_result(self, id):
        self.events[id] = threading.Event()

    def has_result(self, resource_id):
        return resource_id in self.results

    def awaiting_result(self, resource_id):
        return resource_id in self.events

ResultsManager = ResultsManager()
