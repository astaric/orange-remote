from contextlib import contextmanager
import inspect
import pkgutil
import importlib
import sys
import imp

import Orange
from orangecontrib.remote.proxy import Proxy, get_server_address, wrapped_function, wrapped_member, create_proxy

proxies = imp.new_module('proxies')
sys.modules['proxies'] = proxies

old_to_new = {}
remote_orange_modules = {}


def create_remote_orange_module():
    excluded_modules = ["Orange.test", "Orange.canvas", "Orange.widgets"]

    remote_orange = create_submodule(None, 'Orange')
    for importer, modname, ispkg in pkgutil.walk_packages(path=Orange.__path__, prefix="Orange.",
                                                          onerror=lambda x: None):
        if any(modname.startswith(excluded_module) for excluded_module in excluded_modules):
            continue
        try:
            module = importlib.import_module(modname)

            current_module = remote_orange
            for submodule in modname.lstrip("Orange.").split("."):
                if not hasattr(current_module, submodule):
                    create_submodule(current_module, submodule)
                current_module = getattr(current_module, submodule)

            for name, class_ in inspect.getmembers(module, inspect.isclass):
                if not class_.__module__.startswith("Orange"):
                    continue

                if class_ in old_to_new:
                    new_class = old_to_new[class_]
                else:
                    new_name, new_class = create_proxy(name, class_)
                    old_to_new[class_] = new_class
                    setattr(proxies, new_name, new_class)

                setattr(current_module, name, new_class)

        except ImportError as err:
            sys.stderr.write("Failed to load module %s: %s\n" % (modname, err))
    return remote_orange


def create_submodule(parent, name):
    module = imp.new_module(name)
    if parent is not None:
        setattr(parent, name, module)
        name = '.'.join((parent.__name__, name))
    module.__name__ = name
    remote_orange_modules[name] = module
    return module

@contextmanager
def server(address):
    if address is None:
        yield
    else:
        old_modules = sys.modules.copy()
        sys.modules.update(remote_orange_modules)
        yield
        sys.modules = old_modules

create_remote_orange_module()

print("Using Orange Server %s:%s" % get_server_address())
