from http.client import HTTPConnection
import pickle
from socketserver import TCPServer
import threading
import unittest

from orangecontrib.remote import __main__ as orange_server
from orangecontrib.remote.commands import ExecutionFailedError
from orangecontrib.remote.http_server import OrangeServer


class OrangeServerTests(unittest.TestCase):
    server = server_thread = None

    @classmethod
    def setUpClass(cls):
        cls.server = TCPServer(('localhost', 0), OrangeServer)
        cls.server_thread = threading.Thread(
            name='Orange server serving',
            target=cls.server.serve_forever,
            kwargs={'poll_interval': 0.01}
        )
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join()
        cls.server.server_close()

    def setUp(self):
        self.server_connection = HTTPConnection(*self.server.server_address)

    def test_returns_resource(self):
        orange_server.cache["123"] = "456"

        self.server_connection.request("GET", "/123")
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 200)
        self.assertEqual(self.read_data(response), "456")

    def test_returns_error_404_on_empty_get_request(self):
        self.server_connection.request("GET", "/")
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 404)

    def test_returns_error_404_on_unknown_resource(self):
        self.server_connection.request("GET", "/123")
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
        self.assertEqual(orange_server.cache[object_id], "456")

    def test_create_accepts_uploaded_objects(self):
        self.server_connection.request(
            "POST", "create",
            pickle.dumps("456"),
            {"Content-Type": "application/octet-stream"})
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 200)
        object_id = self.read_data(response)
        self.assertEqual(orange_server.cache[object_id], "456")

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
        self.assertIsInstance(orange_server.cache[object_id], ExecutionFailedError)
        print(orange_server.cache[object_id].traceback)

    def test_call_adds_objects_to_cache(self):
        orange_server.cache["x"] = []
        self.server_connection.request(
            "POST", "call",
            """{"call": {"object": {"__jsonclass__": ["Promise", "x"]},
                           "method": "append",
                           "args": ["x"]}}""",
            {"Content-Type": "application/json"})
        response = self.server_connection.getresponse()

        self.assertEqual(response.status, 200)
        object_id = self.read_data(response)
        self.assertEqual(orange_server.cache.get(object_id), None)
        self.assertEqual(orange_server.cache['x'], ['x'])


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
