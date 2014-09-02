from http.server import BaseHTTPRequestHandler
import io
import json
import multiprocessing
import pickle
import logging
import queue
import shutil
import socketserver
import threading
import traceback
import signal

from orangecontrib.remote.server.commands import Create, Call, Get, Command, execute_command, Promise
import uuid

class Cache(dict):
    events = {}

logger = logging.getLogger("orange_server")

cache = Cache()

Promise.__cache__ = cache

class Proxy:
    __id__ = None

    def __init__(self, id):
        self.__id__ = id


class OrangeServer(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super(OrangeServer, self).__init__(request, client_address, server)

    def do_GET(self):
        resource_id = self.path.strip("/")

        if resource_id in cache.events:
            cache.events[resource_id].wait()
        if resource_id not in cache:
            return self.send_error(404, "Resource {} not found".format(resource_id))

        buf = pickle.dumps(cache[resource_id])
        f = io.BytesIO(buf)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", "attachment;filename={}.pickle"
                                                .format(resource_id))
        self.send_header("Content-Length", str(len(buf)))
        self.end_headers()

        shutil.copyfileobj(f, self.wfile)
        f.close()

    def do_POST(self):
        result_id = str(uuid.uuid1())
        try:
            data = self.parse_post_data()
            if isinstance(data, Command):
                cache.events[result_id] = threading.Event()
                CommandProcessor.queue((result_id, data))
            else:
                cache[result_id] = data
        except AttributeError as err:
            return self.send_error(400, str(err))
        except ValueError as err:
            return self.send_error(400, str(err))

        encoded = result_id.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))

        self.end_headers()

        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        shutil.copyfileobj(f, self.wfile)
        f.close()

    def parse_post_data(self):
        content_len = int(self.headers['content-length'] or 0)
        content_type = self.headers.get_content_type()
        data = self.rfile.read(content_len)

        if content_type == 'application/octet-stream':
            return pickle.loads(data)
        elif content_type == 'application/json':
            return json.JSONDecoder(object_hook=self.object_hook).decode(data.decode('utf-8'))
        else:
            return data

    @staticmethod
    def object_hook(pairs):
        if 'create' in pairs:
            return Create(**pairs['create'])

        if 'call' in pairs:
            return Call(**pairs['call'])

        if 'get' in pairs:
            return Get(**pairs['get'])

        if '__jsonclass__' in pairs:
            constructor, param = pairs['__jsonclass__']
            if constructor == "Promise":
                try:
                    if param in cache:
                        return cache[param]
                    elif param in cache.events:
                        return Promise(param)
                except:
                    raise ValueError("Unknown promise '%s'" % param)
            elif constructor == "slice":
                return slice(*param)

        return pairs


class CommandProcessor:
    logger = logging.getLogger("worker")
    _execution_queue = queue.Queue()

    def __init__(self):
        self._is_running = True

    def run(self, poll_interval=1):
        self.logger.info("Worker started")
        execution_pool = multiprocessing.Pool()

        while self._is_running:
            try:
                result_id, command = self._execution_queue.get(block=True, timeout=poll_interval)
                logger.info("Received command")
                command.resolve_promises()
                cache[result_id] = execution_pool.apply(execute_command, [command])
                cache.events[result_id].set()
            except queue.Empty:
                continue

        execution_pool.close()
        self.logger.info("Worker shutdown")

    @classmethod
    def queue(cls, command):
        cls._execution_queue.put(command)

    def shutdown(self):
        self.logger.info("Received a shutdown request")
        self._is_running = False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M')

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

    server_thread.start()
    worker_thread.start()

    print("Starting Orange Server")
    print("Listening on port", port)

