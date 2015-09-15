from contextlib import contextmanager
import builtins
import os

from orangecontrib.remote.proxy import Proxy, \
    wrapped_function, wrapped_member, AnonymousProxy
from orangecontrib.remote.remote_module import ModuleDescription, RemoteModule
from orangecontrib.remote.state_manager import StateManager


@contextmanager
def server(address):
    if address is None:
        yield
    else:
        remote_orange = RemoteModule.from_server(address)
        old_import = builtins.__import__

        def new_import(name, globals=None, locals=None, fromlist=(), level=0):
            try:
                return remote_orange.__import__(name)
            except ImportError:
                return old_import(name, globals, locals, fromlist, level)

        builtins.__import__ = new_import
        yield
        builtins.__import__ = old_import


def save_state(state):
    return StateManager.save_state(state)


def aborted():
    return os.path.exists(os.path.join(CommandProcessor.aborted_commands_path, StateManager.__id__))
