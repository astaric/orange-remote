import logging
import socketserver
import threading
import signal

import Orange

from orangecontrib.remote import RemoteModule

from orangecontrib.remote.command_processor import CommandProcessor
from orangecontrib.remote.http_server import OrangeServer
from orangecontrib.remote.results_manager import ResultsManager


logger = logging.getLogger("orange_server")


def run_server():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S')

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port", default="9465", help="Port number")
    parser.add_option("--host", dest="hostname", default="", help="Host name")
    options, args = parser.parse_args()

    port = int(options.port)
    hostname = options.hostname

    httpd = socketserver.TCPServer((hostname, port), OrangeServer)
    worker = CommandProcessor()
    worker_thread = threading.Thread(
        name='Processing queue',
        target=worker.run,
        kwargs={'poll_interval': 1}
    )
    server_thread = threading.Thread(
        name='HTTP Server',
        target=httpd.serve_forever,
        kwargs={'poll_interval': 1}
    )

    def shutdown(signal, frame):
        if threading.current_thread().name != 'MainThread':
            return
        logging.info("Received a shutdown request")
        worker.shutdown()
        httpd.shutdown()
        server_thread.join()
        worker_thread.join()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    ResultsManager.set_result('contract', RemoteModule(
        Orange, exclude=["Orange.test", "Orange.canvas", "Orange.widgets"]))

    server_thread.start()
    worker_thread.start()

    print("Starting Orange Server")
    print("Listening on port", port)


if __name__ == "__main__":
    run_server()
