import os
import pickle

from celery import Celery
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, LoggingEventHandler

from orangecontrib.remote.commands import ExecutionFailed
from orangecontrib.remote.executor import Executor
from orangecontrib.remote.results_manager import ResultsManager

app = Celery()

tmp_path = os.path.join(os.path.dirname(__file__), 'tmp')
results_path = os.path.join(os.path.dirname(__file__), 'results')


class CeleryExecutor(Executor):
    def __init__(self):
        super().__init__()
        self.id_mapping = {}
        self.observer = None

    def start(self):
        super.start()

        class ResultsHandler(FileSystemEventHandler):
            def on_created(this, event):
                _, result_id = os.path.split(event.src_path)
                self.logger.info("Received result " + result_id)

                with open(event.src_path, 'rb') as f:
                    result = pickle.load(f)

                ResultsManager.set_result(result_id, result)

        handler = ResultsHandler()

        self.observer = Observer()
        self.observer.schedule(handler, results_path)
        self.observer.schedule(LoggingEventHandler(), results_path)
        self.observer.start()

    def stop(self):
        super().stop()
        self.observer.stop()

    def join(self):
        super().join()
        self.observer.join()

    def _abort_command(self, command):
        celery_id = self.id_mapping.get(command.id, None)
        if celery_id is not None:
            result = app.AsyncResult()
            result.abort()

    def _execute_command(self, command, result_id):
        execute_command.delay(command, result_id)


@app.task
def execute_command(command, result_id):
    try:
        result = command.execute()
    except Exception as e:
        result = ExecutionFailed(command, e)
    with open(os.path.join(tmp_path, result_id), 'wb') as f:
        pickle.dump(result, f, pickle.HIGHEST_PROTOCOL)
    os.rename(os.path.join(tmp_path, result_id),
              os.path.join(results_path, result_id))
    print("Stored result " + result_id)


if __name__ == '__main__':
    app.worker_main()
