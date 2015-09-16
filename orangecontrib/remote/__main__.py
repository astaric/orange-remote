import logging
import socketserver
import threading
import signal

import Orange

from orangecontrib.remote.remote_module import RemoteModule

from orangecontrib.remote.http_server import OrangeServer
from orangecontrib.remote.results_manager import ResultsManager


logger = logging.getLogger("orange_server")


def run_server():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port", default="9465", help="Port number")
    parser.add_option("--host", dest="hostname", default="", help="Host name")
    parser.add_option("--executor", dest="executor",
                      default="orangecontrib.remote.executor.multiprocessing.MultiprocessingExecutor",
                      help="Class for executing received commands.")
    parser.add_option("-l", "--log-level", dest="log_level", default="ERROR", help="Log level")
    options, args = parser.parse_args()

    logging.basicConfig(
        level=options.log_level,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S')

    port = int(options.port)
    hostname = options.hostname

    ExecutorCls = import_class(options.executor)
    executor = ExecutorCls()

    httpd = socketserver.TCPServer((hostname, port),
                                   OrangeServer.inject(executor))
    httpd_thread = threading.Thread(
        name='HTTP Server',
        target=httpd.serve_forever,
        kwargs={'poll_interval': 1}
    )

    def shutdown(signal, frame):
        if threading.current_thread().name != 'MainThread':
            return
        logging.info("Received a shutdown request")

        httpd.shutdown()
        httpd_thread.join()
        executor.stop()
        executor.join()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    ResultsManager.set_result('contract', RemoteModule(
        Orange, exclude=["Orange.test", "Orange.canvas", "Orange.widgets"]))

    httpd_thread.start()
    executor.start()

    print("Starting Orange Server")
    print("Listening on port", port)


def import_class(cl):
    module, classname = cl.rsplit('.', 1)
    m = __import__(module, globals(), locals(), [classname])
    return getattr(m, classname)

if __name__ == "__main__":
    run_server()
