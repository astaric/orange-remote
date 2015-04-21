import threading


class ResultsManager:
    results = {}
    events = {}

    @classmethod
    def set_result(cls, id, result):
        cls.results[id] = result
        if id in cls.events:
            cls.events[id].set()

    @classmethod
    def get_result(cls, id):
        if id in cls.events:
            cls.events[id].wait()
        return cls.results[id]

    @classmethod
    def register_result(cls, id):
        cls.events[id] = threading.Event()

    @classmethod
    def has_result(cls, resource_id):
        return resource_id in cls.results
