import logging
import queue

from orangecontrib.remote.commands import Abort


class Executor:
    logger = logging.getLogger("Executor")

    def __init__(self):
        self._execution_queue = queue.Queue()
        self._is_running = True

    def run(self, poll_interval=1):
        self.logger.info("Executor started")
        self._on_start()

        while self._is_running:
            try:
                result_id, command = self._execution_queue.get(block=True, timeout=poll_interval)
                self.logger.info("Received command " + result_id)

                if isinstance(command, Abort):
                    self._abort_command(command.id)
                else:
                    command.resolve_promises()
                    self.logger.debug("Queueing %s for execution" % result_id)
                    self._execute_command(command, result_id)
            except queue.Empty:
                continue

        self._on_stop()

    def queue(self, command):
        self._execution_queue.put(command)

    def shutdown(self):
        self._is_running = False
        self._on_stop()
        self.logger.info("Executor terminated")

    def _on_start(self):
        pass

    def _on_stop(self):
        pass

    def _abort_command(self, command):
        raise NotImplementedError()

    def _execute_command(self, command, result_id):
        raise NotImplementedError()
