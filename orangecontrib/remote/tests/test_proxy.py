from socketserver import TCPServer
import threading
import unittest
from orangecontrib.remote.remote_module import ClassDescription

from orangecontrib.remote import Proxy
from orangecontrib.remote.command_processor import CommandProcessor
from orangecontrib.remote.commands import RemoteException
from orangecontrib.remote.http_server import OrangeServer
from orangecontrib.remote.tests.dummies import DummyIterable, DummyClass


class OrangeServerTests(unittest.TestCase):
    server = server_thread = worker = worker_thread = None

    @classmethod
    def setUpClass(cls):
        cls.server = TCPServer(('localhost', 0), OrangeServer)
        cls.server_thread = threading.Thread(
            name='Orange server serving',
            target=cls.server.serve_forever,
            kwargs={'poll_interval': 0.01}
        )
        cls.server_thread.start()
        cls.worker = CommandProcessor()
        cls.worker_thread = threading.Thread(
            name='Processing thread',
            target=cls.worker.run,
            kwargs={'poll_interval': 0.01}
        )
        cls.worker_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join()
        cls.worker.shutdown()
        cls.worker_thread.join()
        cls.server.server_close()

    def setUp(self):
        self.proxy = self.create_proxy(DummyClass)

    def create_proxy(self, cls):
        return ClassDescription(cls).create_proxy(self.server.server_address)

    def test_can_instantiate_proxy(self):
        self.proxy()

    def test_calling_methods_returns_a_proxy(self):
        proxy_instance = self.proxy()

        self.assertIsInstance(proxy_instance.a(), Proxy)

    def test_accessing_members_returns_a_proxy(self):
        proxy_instance = self.proxy()

        self.assertIsInstance(proxy_instance.b, Proxy)

    def test_can_proxy_iterable(self):
        proxy = self.create_proxy(DummyIterable)

        proxy_instance = proxy(["a"])

        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(proxy_instance[0].get(), "a")
        for x in proxy_instance:
            self.assertEqual("a", x.get())

    def test_raises_exception_when_remote_execution_fails(self):
        proxy = self.create_proxy(int)

        proxy_instance = proxy("a")

        self.assertRaises(RemoteException, proxy_instance.get)

    def test_annotated_methods_return_proxies(self):
        proxy_cache = {}
        s = ClassDescription(str, proxy_cache)
        sp = s.create_proxy(self.server.server_address)
        d = ClassDescription(DummyClass, proxy_cache)
        dp = d.create_proxy(self.server.server_address)

        # method
        self.assertIsInstance(dp().annotated_method(), sp)

        # class method
        self.assertIsInstance(dp.annotated_class_method(), sp)


if __name__ == '__main__':
    unittest.main()
