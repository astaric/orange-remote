import logging
import multiprocessing
import os
import queue
from orangecontrib.remote.commands import execute_command, Abort
from orangecontrib.remote.results_manager import ResultsManager
from orangecontrib.remote.state_manager import StateManager


class MultiprocessingExecutor:
    logger = logging.getLogger("worker")
    aborted_commands_path = \
        os.path.join(os.path.dirname(__file__), 'aborted_commands')
    if not os.path.exists(aborted_commands_path):
        os.mkdir(aborted_commands_path)

    _execution_queue = queue.Queue()

    def __init__(self):
        self._is_running = True
        self.executing_commands = set()

    def run(self, poll_interval=1):
        self.logger.info("Worker started")
        execution_pool = multiprocessing.Pool()

        while self._is_running:
            try:
                result_id, command = self._execution_queue.get(block=True, timeout=poll_interval)
                self.logger.info("Received command " + result_id)

                if isinstance(command, Abort):
                    self.abort_command(command.id)
                else:
                    command.resolve_promises()
                    self.logger.debug("Queueing %s for execution" % result_id)
                    self.set_executing(result_id)
                    execution_pool.apply_async(execute_command, [result_id, command], callback=self.on_completed)

            except queue.Empty:
                continue

        self.logger.debug("Terminating execution pool")
        execution_pool.terminate()
        self.logger.debug("Joining execution pool")
        execution_pool.join()
        self.logger.info("Worker terminated")

    def on_completed(self, result):
        id, result = result
        self.logger.debug("Received result: " + id)
        ResultsManager.set_result(id, result)
        StateManager.delete_state(id)
        self.set_done(id)

    def set_executing(self, id):
        self.executing_commands.add(id)

    def set_done(self, id):
        self.executing_commands.remove(id)
        abort_path = os.path.join(self.aborted_commands_path, id)
        if os.path.exists(abort_path):
            os.remove(abort_path)

    def abort_command(self, id):
        with open(os.path.join(self.aborted_commands_path, id), 'w'):
            pass

    @classmethod
    def queue(cls, command):
        cls._execution_queue.put(command)

    def shutdown(self):
        self.logger.info("Received a shutdown request")
        if self.executing_commands:
            self.logger.debug("Active tasks: " + str(self.executing_commands))
            for command in self.executing_commands:
                self.abort_command(command)
        self._is_running = False
