import importlib
import inspect
import pkgutil
import sys
import types
from orangecontrib.remote import wrapped_function, wrapped_member, Proxy
from orangecontrib.remote.proxy import fetch_from_server


class ModuleDescription:
    def __init__(self, module, known_classes):
        self.members = {}

        for name, class_ in inspect.getmembers(module, inspect.isclass):
            if not class_.__module__.startswith("Orange"):
                continue

            self.members[name] = known_classes.setdefault(
                class_, ClassDescription(class_))


class ClassDescription:
    _proxy = None

    def __init__(self, class_):
        self.module = class_.__module__
        self.name = class_.__name__
        self.functions = []
        self.members = []

        for n, f in inspect.getmembers(class_, inspect.isfunction):
            if n.startswith("__") and n not in ("__getitem__", "__call__",
                                                "__len__", "__str__"):
                continue
            self.functions.append(n)
        for n, p in inspect.getmembers(class_, inspect.isdatadescriptor):
            if n.startswith("__"):
                continue
            self.members.append(n)

    def create_proxy(self, server):
        if self._proxy is None or self._proxy.__server__ != server:
            members = {"__module__": "proxies",
                       "__originalclass__": self.name,
                       "__originalmodule__": self.module}
            for n in self.functions:
                synchronous = n in ("__len__", "__str__")
                members[n] = wrapped_function(n, synchronous)

            for n in self.members:
                members[n] = wrapped_member(n)

            new_name = '%s_%s' % (self.module.replace(".", "_"), self.name)
            self._proxy = type(new_name, (Proxy,), members)
            self._proxy.__server__ = server
        return self._proxy

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('_proxy')
        return state


class RemoteModule:
    def __init__(self, module, exclude=()):
        self.excluded_modules = exclude

        self.descriptions = self.create_descriptions(module)
        self.modules = self.create_modules()

    @classmethod
    def from_server(cls, address):
        """
        :param address: hostname:port
        :return:
        :rtype: orangecontrib.remote.remote_module.RemoteModule
        """
        address = address.split(':')
        if len(address) > 1:
            address[1] = int(address[1])

        remote_module = fetch_from_server(address, 'object/contract')
        remote_module.set_server(address)
        return remote_module

    def create_descriptions(self, module):
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

    def create_modules(self, server=('localhost', 9465)):
        proxies = self.descriptions
        proxies_module = types.ModuleType('proxies')
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
            for submodule in modname[len(root) + 1:].split('.'):
                if not submodule:
                    break
                if not hasattr(current_module, submodule):
                    setattr(current_module, submodule,
                            self.create_submodule(current_module, submodule))
                current_module = getattr(current_module, submodule)
            modules[modname] = current_module

            for name, class_ in proxies[modname].members.items():
                setattr(current_module, name, class_.create_proxy(server))

        return modules

    @staticmethod
    def create_submodule(parent, name):
        module = types.ModuleType(name)
        if parent is not None:
            setattr(parent, name, module)
            name = '.'.join((parent.__name__, name))
        module.__name__ = name
        return module

    def set_server(self, address):
        self.modules = self.create_modules(address)

    def __import__(self, name):
        if name in self.modules:
            return self.modules[name]
        raise ImportError

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('modules')
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.modules = self.create_modules()
