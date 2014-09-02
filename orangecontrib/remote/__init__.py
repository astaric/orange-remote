import inspect
import pkgutil
import importlib
import warnings
import sys
import imp

import Orange
from orangecontrib.remote.proxy import Proxy, get_server_address, wrapped_function, wrapped_member, create_proxy


proxies = imp.new_module('proxies')
sys.modules['proxies'] = proxies

old_to_new = {}


def replace_orange_with_proxies():
    excluded_modules = ["Orange.test", "Orange.canvas", "Orange.widgets"]
    for importer, modname, ispkg in pkgutil.walk_packages(path=Orange.__path__, prefix="Orange.",
                                                          onerror=lambda x: None):
        if any(modname.startswith(excluded_module) for excluded_module in excluded_modules):
            continue
        try:
            module = importlib.import_module(modname)

            new_module = globals()
            module_name = __name__
            for part in modname.lstrip("Orange.").split("."):
                if new_module is globals():
                    if part not in new_module:
                        new_module[part] = imp.new_module(part)
                    new_module = new_module[part]
                else:
                    if not hasattr(new_module, part):
                        setattr(new_module, part, imp.new_module(part))
                    new_module = getattr(new_module, part)
                module_name = '.'.join((module_name, part))
                sys.modules[module_name] = new_module

            for name, class_ in inspect.getmembers(module, inspect.isclass):
                if not class_.__module__.startswith("Orange"):
                    continue

                if class_ in old_to_new:
                    new_class = old_to_new[class_]
                else:
                    new_name, new_class = create_proxy(name, class_)
                    old_to_new[class_] = new_class
                    setattr(proxies, new_name, new_class)

                if new_module is globals():
                    new_module[name] = new_class
                else:
                    setattr(new_module, name, new_class)

        except ImportError as err:
            sys.stderr.write("Failed to load module %s: %s\n" % (modname, err))


replace_orange_with_proxies()

del Orange

print("Using Orange Server %s:%s" % get_server_address())
