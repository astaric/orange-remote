import os
import threading

from celery import Celery
from celery.exceptions import TimeoutError

from orangecontrib.remote.commands import ExecutionFailed
from orangecontrib.remote.executor import Executor
from orangecontrib.remote.results_manager import ResultsManager

app = Celery(backend='amqp://', broker='amqp://')

tmp_path = os.path.join(os.path.dirname(__file__), 'tmp')
results_path = os.path.join(os.path.dirname(__file__), 'results')


class CeleryExecutor(Executor):
    def __init__(self):
        super().__init__()
        self.id_mapping = {}
        self.waiters = []

    def join(self):
        super().join()
        for t in self.waiters:
            self.logger.info("Joining %s" % t)
            t.join()

    def _abort_command(self, command):
        celery_id = self.id_mapping.get(command.id, None)
        if celery_id is not None:
            result = app.AsyncResult()
            result.abort()

    def _execute_command(self, command, result_id):
        promise = execute_command.delay(command)
        self._await_result(result_id, promise)

    def _await_result(self, result_id, promise):
        t = threading.Thread(
            name='Result getter',
            target=self._wait_on_promise,
            kwargs=dict(result_id=result_id, promise=promise)
        )
        t.start()
        self.waiters.append(t)

    def _wait_on_promise(self, result_id, promise):
        while self._is_running:
            try:
                result = promise.get(timeout=1)
                ResultsManager.set_result(result_id, result)
                return
            except TimeoutError:
                pass

@app.task
def execute_command(command):
    try:
        return command.execute()
    except Exception as e:
        return ExecutionFailed(command, e)

if __name__ == '__main__':
    app.worker_main()
