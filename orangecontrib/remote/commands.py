""" Commands that can be executed on the server. """
import importlib
import logging
import traceback

DEBUG = False


class Promise:
    __cache__ = None

    def __init__(self, id):
        self.id = id

    def get(self):
        self.__cache__.events[self.id].wait()
        return self.__cache__[self.id]

    def ready(self):
        return self.id in self.__cache__


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

    def resolve_promises(self):
        pass


class Create(Command):
    module = ""
    class_ = ""
    args   = ()
    kwargs = {}

    def execute(self):
        module = importlib.import_module(self.module)
        cls = getattr(module, self.class_)
        return cls(*self.args, **self.kwargs)

    def __str__(self):
        args = list(map(str, self.args))
        args.extend("%s=%s" % (k, v) for k, v in self.kwargs.items())
        return "{}.{}({})".format(
            self.module, self.class_, ", ".join(args)
        )


class Call(Command):
    object = ""
    method = ""
    args   = ()
    kwargs = {}

    def execute(self):
        self.resolve_promises("object", "args", "kwargs")
        return getattr(self.object, self.method)(*self.args, **self.kwargs)

    def __str__(self):
        args = list(map(str, self.args))
        args.extend("%s=%s" % (k, v) for k, v in self.kwargs.items())
        return "{}.{}({})".format(
            self.object, self.method, ", ".join(args)
        )

    def resolve_promises(self, *args):
        for attr_name in ("object", "args"):
            attr = getattr(self, attr_name)
            if isinstance(attr, Promise):
                setattr(self, attr_name, attr.get())
            elif isinstance(attr, list):
                for i, value in enumerate(attr):
                    if isinstance(attr, Promise):
                        attr[i] = value.get()


class Get(Command):
    object = ""
    member = ""

    def execute(self):
        if self.member == "":
            return self.object
        else:
            return getattr(self.object, self.member)


logger = logging.getLogger("worker")


def execute_command(command):
    print("Executing command %s" % command)
    try:
        return command.execute()
    except Exception as err:
        print("Execution failed with error: %s" % err)
        if DEBUG:
            raise

        return ExecutionFailedError(command, err)


class ExecutionFailedError(Exception):
    def __init__(self, command=None, error=None):
        if not command or not error:
            return
        self.message = "Execution of {} failed with error: {}".format(command, error)
        self.traceback = traceback.format_exc()
        super().__init__(self.message)
