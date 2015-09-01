""" Commands that can be executed on the server. """
import importlib
import logging

from orangecontrib.remote.results_manager import ResultsManager
from orangecontrib.remote.state_manager import StateManager

DEBUG = False


class Promise:
    def __init__(self, id):
        self.id = id

    def get(self):
        return ResultsManager.get_result(self.id)

    def ready(self):
        return ResultsManager.has_result(self.id)


class Command:
    result = None
    return_result = False

    def __init__(self, **params):
        for n, v in params.items():
            if not hasattr(self, n):
                raise AttributeError("{} is not a valid parameter for {}"
                                     .format(n, self.__class__.__name__))
            setattr(self, n, v)

    def execute(self):
        raise NotImplementedError()

    def resolve_promises(self, *attrs):

        def resolve_promises(obj):
            if isinstance(obj, Promise):
                obj = obj.get()
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    obj[i] = resolve_promises(obj[i])
            return obj

        for attr_name in attrs:
            value = resolve_promises(getattr(self, attr_name))
            setattr(self, attr_name, value)


class Create(Command):
    module = ""
    class_ = ""
    args   = ()
    kwargs = {}

    def execute(self):
        cls = importlib.import_module(self.module)
        for name in self.class_.split("."):
            cls = getattr(cls, name)
        return cls(*self.args, **self.kwargs)

    def __str__(self):
        args = list(map(str, self.args))
        args.extend("%s=%s" % (k, v) for k, v in self.kwargs.items())
        return "{}.{}({})".format(
            self.module, self.class_, ", ".join(args)
        )

    def resolve_promises(self, *attrs):
        super().resolve_promises("args", "kwargs")


class Call(Command):
    object = ""
    method = ""
    args   = ()
    kwargs = {}

    def execute(self):
        return getattr(self.object, self.method)(*self.args, **self.kwargs)

    def __str__(self):
        args = list(map(str, self.args))
        args.extend("%s=%s" % (k, v) for k, v in self.kwargs.items())
        return "{}.{}({})".format(
            repr(self.object), self.method, ", ".join(map(repr, args))
        )

    def resolve_promises(self, *attrs):
        super().resolve_promises("object", "args", "kwargs")


class Get(Command):
    object = ""
    member = ""

    def execute(self):
        if self.member == "":
            return self.object
        else:
            return getattr(self.object, self.member)


class Abort(Command):
    id = ""


logger = logging.getLogger("worker")


def execute_command(id, command):
    #print("Executing command %s" % command)
    try:
        logger.debug('Execution started: ' + id)
        StateManager.set_id(id)
        value = command.execute()
        logger.debug('Execution completed: ' + id)
        return id, value
    except Exception as err:
        logger.debug("Execution failed: " + id)
        logger.debug("Error was: " + str(err))

        return id, ExecutionFailed(command, err)


class ExecutionFailed:
    def __init__(self, command=None, error=None):
        if not command or not error:
            return
        self.message = "Execution of {} failed with error: {}".format(command, error)

    def raise_(self):
        raise(RemoteException(self.message))

    def __str__(self):
        return 'Execution Failed: ' + self.message

    __repr__ = __str__


class RemoteException(Exception):
    pass
