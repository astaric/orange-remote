from http.client import HTTPConnection
import logging
import pickle
from socketserver import TCPServer
import threading
import unittest

from orangecontrib.remote.commands import ExecutionFailed
from orangecontrib.remote.http_server import OrangeServer
from orangecontrib.remote.results_manager import ResultsManager
from orangecontrib.remote.executor.multiprocessing import MultiprocessingExecutor


class OrangeServerTests(unittest.TestCase):
    server = server_thread = None

    @classmethod
    def setUpClass(cls):
        cls.worker = MultiprocessingExecutor()
        cls.server = TCPServer(('localhost', 0),
                               OrangeServer.inject(cls.worker))
        cls.server_thread = threading.Thread(
            name='Orange server serving',
            target=cls.server.serve_forever,
            kwargs={'poll_interval': 0.01}
        )
        cls.server_thread.start()
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.worker.stop()
        cls.server_thread.join()
        cls.worker.join()
        cls.server.server_close()

    def setUp(self):
        FORMAT = '%(asctime)-15s %(message)s'
        logging.basicConfig(format=FORMAT, level=logging.DEBUG)
        self.server_connection = HTTPConnection(*self.server.server_address)

    def test_returns_resource(self):
        ResultsManager.set_result("123","456")

        self.server_connection.request("GET", "object/123")
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 200)
        self.assertEqual(self.read_data(response), "456")

    def test_returns_error_404_on_unknown_resource(self):
        self.server_connection.request("GET", "object/123")
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 404)

    def test_create_adds_objects_to_cache(self):
        self.server_connection.request(
            "POST", "create",
            """{"create": {"module": "builtins",
                           "class_": "str",
                           "args": ["456"]}}""",
            {"Content-Type": "application/json"})
        response = self.server_connection.getresponse()
        self.assertEqual(response.status, 200)
        object_id = self.read_data(response)
        self.assertEqual(ResultsManager.get_result(object_id), "456")

    def test_create_accepts_uploaded_objects(self):
        self.server_connection.request(
            "POST", "create",
            pickle.dumps("456"),
            {"Content-Type": "application/octet-stream"})
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 200)
        object_id = self.read_data(response)
        self.assertEqual(ResultsManager.get_result(object_id), "456")

    def test_create_returns_400_on_invalid_json_in_request(self):
        self.server_connection.request(
            "POST", "create",
            """Invalid json""",
            {"Content-Type": "application/json"})

        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 400)

    def test_create_stores_exception_if_execution_fails(self):
        self.server_connection.request(
            "POST", "/create",
            """{"create": {"module": "builtins",
                           "class_": "int",
                           "args": ["4a"]}}""",
            {"Content-Type": "application/json"})
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 200)
        object_id = self.read_data(response)
        self.assertIsInstance(ResultsManager.get_result(object_id), ExecutionFailed)

    @staticmethod
    def read_data(response):
        response_len = int(response.getheader("Content-Length", 0))
        response_data = response.read(response_len)
        if response.getheader("Content-Type", "") == "application/octet-stream":
            return pickle.loads(response_data)
        else:
            return response_data.decode('utf-8')


if __name__ == '__main__':
    unittest.main()
