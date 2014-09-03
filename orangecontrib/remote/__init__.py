from contextlib import contextmanager
import inspect
import pkgutil
import importlib
import sys
import imp

import Orange
from orangecontrib.remote.proxy import Proxy, get_server_address, wrapped_function, wrapped_member, create_proxy


class ModuleDescription:
    def __init__(self, module, known_classes):
        self.members = {}

        for name, class_ in inspect.getmembers(module, inspect.isclass):
            if not class_.__module__.startswith("Orange"):
                continue

            self.members[name] = known_classes.setdefault(
                class_, ClassDescription(class_))


class ClassDescription:
    def __init__(self, class_):
        self.member = create_proxy(class_.__name__, class_)


class RemoteModule:
    excluded_modules = ["Orange.test", "Orange.canvas", "Orange.widgets"]
    _old_sys_modules = None

    def __init__(self, module=Orange):
        proxies = self.create_proxies(module)
        self.modules = self.create_module(proxies)

    def create_proxies(self, module):
        cache = {}
        modules = {module.__name__: ModuleDescription(module, cache)}

        for modname in self.list_submodules(module):
            try:
                submodule = importlib.import_module(modname)
            except ImportError as err:
                sys.stderr.write("Failed to load module %s: %s\n" %
                                 (modname, err))
                continue

            modules[submodule.__name__] = ModuleDescription(submodule, cache)

        return modules

    def list_submodules(self, module):
        prefix = module.__name__ + '.'
        for importer, modname, ispkg in pkgutil.walk_packages(
                path=module.__path__, prefix=prefix, onerror=lambda x: None):
            if any(modname.startswith(excluded_module)
                   for excluded_module in self.excluded_modules):
                continue
            yield modname

    def create_proxy(self, name, class_):
        return create_proxy(name, class_)

    def create_module(self, proxies):
        proxies_module = imp.new_module('proxies')
        sys.modules['proxies'] = proxies_module

        roots = []
        modules = {}
        for modname in sorted(proxies, key=lambda x: len(x)):
            for root in roots:
                if modname.startswith(root):
                    break
            else:
                root = modname
                roots.append(root)
                modules[root] = self.create_submodule(None, modname)

            current_module = modules[root]
            for submodule in modname[len(root)+1:].split('.'):
                if not submodule:
                    break
                if not hasattr(current_module, submodule):
                    setattr(current_module, submodule, self.create_submodule(current_module, submodule))
                current_module = getattr(current_module, submodule)
            modules[modname] = current_module

            for name, class_ in proxies[modname].members.items():
                setattr(current_module, name, class_.member)

        return modules

    @staticmethod
    def create_submodule(parent, name):
        module = imp.new_module(name)
        if parent is not None:
            setattr(parent, name, module)
            name = '.'.join((parent.__name__, name))
        module.__name__ = name
        return module

    def install(self):
        self._old_sys_modules = sys.modules
        sys.modules.update(self.modules)

    def uninstall(self):
        sys.modules = self._old_sys_modules


remote_orange = RemoteModule()

@contextmanager
def server(address):
    if address is None:
        yield
    else:
        remote_orange.install()
        yield
        remote_orange.uninstall()

print("Using Orange Server %s:%s" % get_server_address())
