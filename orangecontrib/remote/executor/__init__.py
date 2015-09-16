import logging
import queue
import threading

from orangecontrib.remote.commands import Abort


class Executor:
    logger = logging.getLogger("Executor")

    def __init__(self):
        self._execution_queue = queue.Queue()
        self._is_running = False
        self.thread = None

    def start(self):
        self._is_running = True
        self.thread = threading.Thread(
            name='Processing queue',
            target=self._run,
            kwargs={'poll_interval': 1}
        )
        self.thread.start()

    def _run(self, poll_interval=1):
        self.logger.info("Executor started")

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

        self.logger.info("Executor stopped")

    def _abort_command(self, command):
        raise NotImplementedError()

    def _execute_command(self, command, result_id):
        raise NotImplementedError()

    def stop(self):
        self._is_running = False

    def join(self):
        if self.thread is not None:
            self.thread.join()

    def queue(self, command):
        self._execution_queue.put(command)
