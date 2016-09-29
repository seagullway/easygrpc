import os
import re
import inspect
from types import SimpleNamespace
from importlib import import_module

import six
import grpc

from .parser import GRPCParser


# TODO: Add special search methods method (check change server config)
class GRPCClient(object):
    """gRPC client class.

        - Add one stub or many stubs;
        - Auto load all stubs from proto_modules;
        - Auto load all stubs from current app fixed path;
        - Parse proto_module method to find all add_stub_class.

    """

    GRPCParser = GRPCParser

    DEFAULT_ADDRESS = "[::]:50051"
    HANDLER_SEARCH_PATTERN = "(?P<name>.*)Stub"
    PROTO_PY_FOLDER = "proto_py"

    def __init__(self, proto_py_module=None, address=None, stub_names=()):

        # client instance
        self.stubs = {}
        self.channel = grpc.insecure_channel(target=address or self.DEFAULT_ADDRESS)

        if proto_py_module:
            self.from_module(proto_py_module, *stub_names)

        elif stub_names:
            raise grpc.RpcError("Expected proto_py_module to filter use stub_names, but got only stub_names!")

    @staticmethod
    def parse_proto_file(proto_py_module, pattern, *stub_names):
        """Parse proto module and search add Stub class.

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: import module isinstance;
            :param pattern: pattern to identify stub add class;
            :type pattern: str;
            :param stub_names: added stub names;
            :type stub_names: tuple wit str;

            :return: generator: (clear_class_name: class_object).

        """

        for name, obj in filter(lambda var: inspect.isclass(var[1]), inspect.getmembers(proto_py_module)):
            search = re.match(pattern, name)
            s_name = search and search.groupdict()["name"] or None
            if s_name and not s_name.startswith("Beta"):
                if stub_names:
                    if s_name in stub_names:
                        yield s_name, obj
                else:
                    yield s_name, obj

    def _parse_module(self, proto_py_module, *stub_names):
        """Parse proto_py_module to find Stub add class and messages.

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: import module isinstance;
            :param stub_names: added stub names;
            :type stub_names: tuple wit str.

        """

        # get stubs
        for s_name, stub_obj in self.parse_proto_file(proto_py_module, self.HANDLER_SEARCH_PATTERN, *stub_names):
            if s_name in self.stubs:
                raise grpc.RpcError("The same stub name '{}' is already exists.".format(s_name))
            self.stubs[s_name] = stub_obj

        # set messages to the stub object
        self.stubs_params = self.GRPCParser.parse_module("stub", proto_py_module=proto_py_module)
        for s_name, stub_obj in six.iteritems(self.stubs):
            stub_obj.messages = SimpleNamespace(**self.stubs_params[s_name]["messages"])

    def from_module(self, proto_py_module, *stub_names):
        """Add stubs from object [stubs name mast be equal of the proto names].

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: tuple with import module isinstance;
            :param stub_names: added stub names;
            :type stub_names: tuple wit str;

            :return: client instance.

        """

        # parse module
        old_names = set(self.stubs)
        self._parse_module(proto_py_module, *stub_names)
        new_names = set(self.stubs) - old_names

        # add new stubs
        for s_name in new_names:
            self.add_stub(self.stubs[s_name], need_check=False)

        return self

    def from_modules(self, *proto_py_modules):
        """Load stubs from proto_py_modules.

            :param proto_py_modules: python modules generate from .proto file;
            :type proto_py_modules: tuple with import modules isinstance;

            :return: client instance.

        """

        for proto_py_module in proto_py_modules:
            self.from_module(proto_py_module)

        return self

    def filter(self, *stub_names, include=True):
        """Change client active stubs.

            :param stub_names: Added or removed stub names;
            :type stub_names: tuple with string;
            :param include: flag filter direction:
                - include = True: include all stubs in stub_names;
                - include = False: exclude all stubs in stub_names;
            :type include: bool;

            :return: client instance.

        """

        if include:
            deleted_stubs = (set(self.stubs) - set(stub_names))
        else:
            deleted_stubs = (set(self.stubs) - set(stub_names))
        for s_name in deleted_stubs:
            delattr(self, s_name)

        return self

    def from_self(self):
        """Load stubs from self project use special fixed path: "/service_name/PROTO_PY_FOLDER/".

            :return: client instance.

        """

        proto_py_modules = []
        for stub_file in os.listdir(self.PROTO_PY_FOLDER or os.getcwd()):
            stub_path = os.path.join(self.PROTO_PY_FOLDER, stub_file)
            if stub_file.endswith("pb2.py") and inspect.getmodulename(stub_path):
                try:
                    proto_py_modules.append(import_module(stub_path.replace("/", ".").replace(".py", "")))
                except ImportError:
                    pass

        return self.from_modules(*proto_py_modules)

    def add_stub(self, stub, proto_name=None, need_check=True):
        """Add user define service to the server.

            Warning!!! When used add stud the parser can't add messages attribute!!!

            :param stub: user define stub class;
            :type stub: proto Stub class;
            :param proto_name: proto stub name (use when name in proto module and handler is differ);
            :type proto_name: str;
            :param need_check: flag need check stub name (is name in active client stubs);
            :type need_check: bool.

        """

        # find stub name
        if proto_name is None and not hasattr(stub, "__name__"):
            raise grpc.RpcError("Can't find proto add class name.")

        s_name = proto_name or stub.__name__.replace("Stub", "")

        # need check stub name
        if need_check and s_name in self.stubs:
            raise grpc.RpcError("The same stub name {} is already exists.".format(s_name))

        # add stub
        setattr(self, s_name, self.stubs[s_name](self.channel))

    def add_stubs(self, *stubs, **stubs_param):
        """Add user define stub to the client.

            Warning!!! When used add stud the parser can't add messages attribute!!!

            Import! Can use together stubs and stubs_param!

            :param stubs: user_define stubs classes tuple;
            :type stubs: tuple;
            :param stubs_param: stubs parameters dict like {proto_stub_name: stub_class}
            :type stubs_param: dict.

        """

        # add equal name handler
        for stub in stubs:
            self.add_stub(stub=stub)

        # add handler with user define name
        for name, stub in six.iteritems(stubs_param):
            self.add_stub(stub=stub, proto_name=name)
