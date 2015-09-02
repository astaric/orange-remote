import importlib
import inspect
import pkgutil
import sys
import types
from orangecontrib.remote import wrapped_function, wrapped_member, Proxy
from orangecontrib.remote.proxy import fetch_from_server, AnonymousProxy, execute_on_server


class ModuleDescription:
    def __init__(self, module, known_classes):
        self.members = {}

        for name, cls in inspect.getmembers(module, inspect.isclass):
            if not cls.__module__.startswith("Orange"):
                continue

            self.members[name] = known_classes.get(
                cls, ClassDescription(cls, known_classes))


class ClassDescription:
    _proxy = None

    def __init__(self, cls, known_types=None):
        if known_types is None:
            known_types = {}
        if cls not in known_types:
            known_types[cls] = self

        self.module = cls.__module__
        self.name = cls.__name__
        self.doc = cls.__doc__
        self.init_doc = cls.__init__.__doc__
        self.functions = []
        self.members = []

        for n, f in inspect.getmembers(cls, inspect.isfunction):
            if n.startswith("__") and n not in ("__getitem__", "__call__",
                                                "__len__", "__str__"):
                continue
            self.functions.append(FunctionDescription(n, getattr(cls, n), known_types))

        for n, f in inspect.getmembers(cls, inspect.ismethod):
            if n.startswith("__") and n not in ("__getitem__", "__call__",
                                                "__len__", "__str__"):
                continue
            self.functions.append(ClassMethodDescription(n, cls, known_types))

        for n, p in inspect.getmembers(cls, inspect.isdatadescriptor):
            if n.startswith("__"):
                continue
            self.members.append(n)

    def create_proxy(self, server):
        if self._proxy is None or self._proxy.__server__ != server:
            members = {"__module__": "proxies",
                       "__originalclass__": self.name,
                       "__originalmodule__": self.module}
            for f in self.functions:
                members[f.name] = f.create_proxy(server)

            for n in self.members:
                members[n] = wrapped_member(n)

            new_name = '%s_%s' % (self.module.replace(".", "_"), self.name)
            self._proxy = type(new_name, (Proxy,), members)
            self._proxy.__server__ = server
            self._proxy.__doc__ = self.doc
            self._proxy.__init__ = lambda self, *args, **kwargs: None
            self._proxy.__init__.__doc__ = self.init_doc
        return self._proxy

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('_proxy')
        return state

    def __repr__(self):
        return "ClassDescription: '%s'" % self.name


class FunctionDescription:
    name = None
    doc = None
    _return_type = None

    def __init__(self, name, f, known_types=()):
        self.name = name
        doc = f.__doc__
        self.doc = doc
        return_type = f.__annotations__.get('return')
        if return_type in known_types:
            self.return_type = known_types[return_type]

    def create_proxy(self, server):
        name = self.name
        synchronous = self.name in ("__len__", "__str__")

        def function(this, *args, **kwargs):
            if this.name == "__init__":
                return
            __id__ = execute_on_server(
                this.__server__,
                "call/%s.%s(%s%s)" % (this.__id__, str(name), ",".join(map(str, args)), ""),
                object=this, method=str(name), args=args, kwargs=kwargs)
            if synchronous:
                return fetch_from_server(this.__server__, 'object/' + __id__)
            else:
                return self.create_result(server, id)
        function.__doc__ = self.doc

        return function

    def create_result(self, server, __id__):
        if self.return_type:
            return_type = self.return_type.create_proxy(server)
            result = return_type(__id__=__id__)
        else:
            result = AnonymousProxy(__id__=__id__)
            result.__server__ = server
        return result

    def __repr__(self):
        return "FunctionDescription: '%s'" % self.name


class ClassMethodDescription(FunctionDescription):
    def __init__(self, name, cls, known_types=()):
        super().__init__(name, getattr(cls, name), known_types)
        self.module = cls.__module__
        self.cls = cls.__name__

    def create_proxy(self, server):
        def function(*args, **kwargs):
            __id__ = execute_on_server(
                server,
                "create",
                module=self.module,
                class_=self.cls + '.' + self.name,
                args=args, kwargs=kwargs)

            return self.create_result(server, __id__)
        function.__doc__ = self.doc

        return function

    def __repr__(self):
        return "ClassMethodDescription: '%s'" % self.name


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
