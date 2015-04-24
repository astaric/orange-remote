import base64
from http.server import BaseHTTPRequestHandler
import io
import json
import logging
import pickle
import shutil
import uuid
from orangecontrib.remote.command_processor import CommandProcessor
from orangecontrib.remote.commands import Command, Create, Call, Get, Promise, \
    Abort
from orangecontrib.remote.results_manager import ResultsManager
from orangecontrib.remote.state_manager import StateManager


class OrangeServer(BaseHTTPRequestHandler):
    logger = logging.getLogger("http")

    def __init__(self, request, client_address, server):
        super(OrangeServer, self).__init__(request, client_address, server)

    def do_GET(self):
        f = None
        try:
            self.logger.debug("GET " + self.path)
            resource = self.path.strip("/")
            result_type, resource_id = resource.split("/")

            if result_type == 'object':
                try:
                    buf = pickle.dumps(ResultsManager.get_result(resource_id))
                except KeyError as err:
                    self.logger.exception(err)
                    return self.send_error(404, "Resource {} not found".format(resource_id))

            elif result_type == 'state':
                if ResultsManager.has_result(resource_id):
                    buf = pickle.dumps(ResultsManager.get_result(resource_id))
                else:
                    buf = pickle.dumps(StateManager.get_state(resource_id))

            elif result_type == 'status':
                if ResultsManager.has_result(resource_id):
                    buf = pickle.dumps('ready')
                else:
                    buf = pickle.dumps('not ready')

            else:
                return self.send_error(400, "Unknown resource type")
            f = io.BytesIO(buf)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment;filename={}.pickle"
                                                    .format(resource_id))
            self.send_header("Content-Length", str(len(buf)))
            self.end_headers()

            shutil.copyfileobj(f, self.wfile)
        except Exception as ex:
            self.logger.exception(ex)
        finally:
            if f is not None:
                f.close()

    def do_POST(self):
        result_id = str(uuid.uuid1())
        try:
            data = self.parse_post_data()
            if isinstance(data, Command):
                ResultsManager.register_result(result_id)
                CommandProcessor.queue((result_id, data))
            else:
                ResultsManager.set_result(result_id, data)
        except Exception as err:
            self.logger.exception(err)
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

        if 'abort' in pairs:
            return Abort(**pairs['abort'])

        if '__jsonclass__' in pairs:
            constructor, param = pairs['__jsonclass__']
            if constructor == "Promise":
                try:
                    if ResultsManager.has_result(param):
                        return ResultsManager.get_result(param)
                    elif ResultsManager.awaiting_result(param):
                        return Promise(param)
                except:
                    raise ValueError("Unknown promise '%s'" % param)
            elif constructor == "slice":
                return slice(*param)
            elif constructor == "PyObject":
                return pickle.loads(base64.b64decode(param))

        return pairs
