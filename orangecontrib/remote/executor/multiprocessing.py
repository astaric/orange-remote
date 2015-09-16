import logging
import multiprocessing
import os
from orangecontrib.remote.results_manager import ResultsManager
from orangecontrib.remote.state_manager import StateManager
from orangecontrib.remote.commands import ExecutionFailed
from orangecontrib.remote.executor import Executor


class MultiprocessingExecutor(Executor):
    aborted_commands_path = \
        os.path.join(os.path.dirname(__file__), 'aborted_commands')
    if not os.path.exists(aborted_commands_path):
        os.mkdir(aborted_commands_path)

    def __init__(self):
        super().__init__()
        self.executing_commands = set()
        self.execution_pool = None

    def start(self):
        super().start()
        self.execution_pool = multiprocessing.Pool()

    def stop(self):
        super().stop()
        self.execution_pool.terminate()
        self.logger.debug("Execution pool terminated")
        self.execution_pool.join()
        self.logger.debug("Execution pool joined")

    def _abort_command(self, command):
        with open(os.path.join(self.aborted_commands_path, id), 'w'):
            pass

    def _execute_command(self, command, result_id):
        self.executing_commands.add(id)

        def on_completed(result):
            id, result = result
            self.logger.debug("Received result: " + id)
            ResultsManager.set_result(id, result)
            StateManager.delete_state(id)

            self.executing_commands.remove(id)
            abort_path = os.path.join(self.aborted_commands_path, id)
            if os.path.exists(abort_path):
                os.remove(abort_path)

        self.execution_pool.apply_async(
            execute_command, [result_id, command],
            callback=on_completed)

logger = logging.getLogger("worker")


def execute_command(id, command):
    try:
        logger.debug('Execution started: ' + id)
        StateManager.set_id(id)
        value = command.execute()
        logger.debug('Execution completed: ' + id)
        return id, value
    except Exception as err:
        logger.debug("Execution failed: " + id)
        logger.debug("Error was: " + str(err))

        return id, ExecutionFailed(command, err)
