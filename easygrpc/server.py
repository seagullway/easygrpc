import os
import re
import time
import inspect
import operator
from concurrent import futures
from importlib import import_module

import six
import grpc


# TODO: Add load const from config
# TODO: Add service methods map ("ops" --> "SendMessage")
# TODO: Add special route class (can change server route after config)
class GRPCServer(object):
    """gRPC server class.

        - Simple create server and start server;
        - Add one service, services;
        - Auto load all user define services class;
        - Parse proto_module method to find all add_service_function;
        - Auto load add_service_function and user define service class from project path;

    """

    DEFAULT_ADDRESS = "[::]:50051"
    DEFAULT_MAX_WORKERS = 10
    SERVICE_FOLDER = "routes"
    PROTO_PY_FOLDER = "proto_py"
    HANDLER_SEARCH_PATTERN = "add_(?P<name>.*)Servicer_to_server"
    SERVER_TIMEOUT_SLEEP = 60 * 60 * 24

    def __init__(self, proto_py_module=None, address="[::]:50051", max_workers=10, service_names=()):

        # server instance
        self._route = {}
        self._server = None
        self.address = address
        self.max_workers = max_workers

        # find service add function
        if proto_py_module:
            self._parse_proto_module(proto_py_module, *service_names)

    @property
    def route(self):
        """Actual route dict.

            :return: dict like:
                {route_name:
                    dict(
                        service=service_class,
                        add_function=add_function_from_proto_py
                    )
                }

        """

        return {name: route for name, route in six.iteritems(self._route)
                if route.get("add_function") and route.get("service")}

    @property
    def server(self):
        """Wrapped grpc server instance [from grpcio].

            :return: grpc.server instance

        """

        return self._server

    @staticmethod
    def parse_proto_file(proto_py_module, pattern, *service_names):
        """Parse proto module to find Service add function use search pattern.

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: import module isinstance;
            :param pattern: pattern to identify service add function;
            :type pattern: str;
            :param service_names: added services names;
            :type service_names: tuple wit str;

            :return: generator: (clear_function_name: function_object).

        """

        for name, obj in filter(lambda var: inspect.isfunction(var[1]), inspect.getmembers(proto_py_module)):
            search = re.match(pattern, name)
            s_name = search and search.groupdict()["name"] or None
            if s_name:
                if service_names:
                    if s_name in service_names:
                        yield s_name, obj
                else:
                    yield s_name, obj

    def _parse_proto_module(self, proto_py_module, *service_names):
        """Parse proto_py_module to find Service add functions.

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: import module isinstance;
            :param service_names: added service names;
            :type service_names: tuple wit str.

        """

        # get stubs
        for s_name, s_obj in self.parse_proto_file(proto_py_module, self.HANDLER_SEARCH_PATTERN, *service_names):
            if s_name in self.route and self.route[s_name]["add_function"]:
                raise grpc.RpcError("The same service name '{}' is already exists.".format(s_name))
            self._route.setdefault(s_name, {})["add_function"] = s_obj

    def from_proto_module(self, proto_py_module, *service_names):
        """Add service add function from proto pt module.

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: import module isinstance;
            :param service_names: added service names;
            :type service_names: tuple wit str;

            :return: server instance.

        """

        self._parse_proto_module(proto_py_module, *service_names)

        return self

    def from_proto_modules(self, *proto_py_modules):
        """Add service add function from proto pt module.

            :param proto_py_modules: python modules generate from .proto file;
            :type proto_py_modules: import module isinstance;

            :return: server instance.

        """

        for proto_py_module in proto_py_modules:
            self.from_proto_module(proto_py_module)

        return self

    @staticmethod
    def parser_service_file(service_module, *service_names):
        """Parse service module to find user define Service.

            :param service_module: module with user define service;
            :type service_module: import module isinstance;
            :param service_names: added services names;
            :type service_names: tuple wit str;

            :return: generator: (service_class_name: class_object).

        """

        for s_name, s_obj in six.iteritems(service_module.__dict__):
            if inspect.isclass(s_obj):
                if service_names:
                    if s_name in service_names:
                        yield s_name, s_obj
                else:
                    yield s_name, s_obj

    def _parse_service_module(self, service_module, *service_names):
        """Parse service module to find user define service classes.

            :param service_module: module with user define services class;
            :type service_module: import module isinstance;
            :param service_names: added service names;
            :type service_names: tuple with str.

        """

        for s_name, s_obj in self.parser_service_file(service_module, *service_names):
            self._route.setdefault(s_name, {})["service"] = s_obj

    def from_module(self, service_module, *service_names):
        """Add service class from object service module.

            :param service_module: module with user define service;
            :type service_module: import module instance;
            :param service_names: added service names;
            :type service_names: tuple wit str;

            :return: server instance.

        """

        self._parse_service_module(service_module, *service_names)

        return self

    def from_modules(self, *service_modules):
        """Load services classes from service modules.

            :param service_modules: module with user define service;
            :type service_modules: import module instance.

            :return: server instance.

        """

        for service_module in service_modules:
            self.from_module(service_module)

        return self

    def from_resources(self, proto_py_module, service_module, *service_names):
        """Add service add function from proto pt module.

            :param proto_py_module: python module generate from .proto file;
            :type proto_py_module: import module isinstance;
            :param service_module: module with user define services class;
            :type service_module: import module isinstance;
            :param service_names: added service names;
            :type service_names: tuple with str.

            :return: server instance.

        """

        self.from_proto_module(proto_py_module, *service_names)
        self.from_module(service_module, *service_names)

        return self

    def from_self(self):
        """Load services from self project environment use special fixed path:
            - for load proto_py_modules: "/service_name/PROTO_PY_FOLDER/";
            - for load user define service modules: "/service_name/SERVICES/".

            :return: service instance.

        """

        proto_py_modules, service_modules = [], []
        proto_fold, service_fold = self.PROTO_PY_FOLDER, self.SERVICE_FOLDER
        proto_fold = service_fold if proto_fold == service_fold else proto_fold

        # load proto
        for check_file in os.listdir(proto_fold):
            file_path = os.path.join(proto_fold, check_file)
            if inspect.getmodulename(file_path) and check_file.endswith("pb2.py"):
                try:
                    proto_py_modules.append(import_module(file_path.replace("/", ".").replace(".py", "")))
                except ImportError:
                    pass
        self.from_proto_modules(*proto_py_modules)

        # load service
        for check_file in os.listdir(service_fold):
            file_path = os.path.join(service_fold, check_file)
            if inspect.getmodulename(file_path) and check_file.endswith(".py"):
                try:
                    module = import_module(file_path.replace("/", ".").replace(".py", ""))
                    service_modules.append(module)
                except ImportError:
                    pass

        self.from_modules(*service_modules)

        return self

    def filter(self, *service_names, include=True):
        """Change active server services.

            :param service_names: Added or removed service names;
            :type service_names: tuple with string;
            :param include: flag filter direction:
                - include = True: include all service in service_names;
                - include = False: exclude all service in service_names;
            :type include: bool;

            :return: server instance.

        """

        for s_name in [operator.and_, operator.sub][include](set(self._route), set(service_names)):
            self._route.pop(s_name)

        return self

    def add_service(self, service, proto_name=None, need_check=True):
        """Add user define service to the server.

            :param service: user define Service add functions;
            :type service: proto Service class;
            :param proto_name: proto Service name (use when name in proto module and handler is differ);
            :type proto_name: str;
            :param need_check: flag need check Service name (is name in active service names);
            :type need_check: bool.

        """

        if proto_name is None and not hasattr(service, "__name__"):
            raise grpc.RpcError("Can't find proto add service name.")

        s_name = proto_name or service.__name__

        # check service name
        if need_check and s_name in self._route and self.route[s_name]["service"]:
            raise grpc.RpcError("The same service name {} is already exists.".format(s_name))

        self._route[s_name]["service"] = service

    def add_services(self, *services, **services_param):
        """Add user define Service to the server.

            Import! Can use together services and services_param!

            :param services: user_define Service classes tuple;
            :type services: tuple;
            :param services_param: Services parameters dict like {proto_service_name: service_class}
            :type services_param: dict.

        """

        # add equal name handler
        for s_obj in services:
            self.add_service(service=s_obj)

        # add handler with user define name
        for s_name, s_obj in six.iteritems(services_param):
            self.add_service(service=s_obj, proto_name=s_name)

    def config_server(self, address=None, max_workers=None):
        """Create server instance.

            :param address: server listen address;
            :type address: str;
            :param max_workers: workers count;
            :type max_workers: int;

            :return: configured server instance.

        """

        # address and max workers
        self.address = address or self.address or self.DEFAULT_ADDRESS
        self.max_workers = max_workers or self.max_workers or self.DEFAULT_MAX_WORKERS
        if not all((self.address, self.max_workers)):
            msg = "To start server expected address and max_workers, but get address: '{}' and max_workers: '{}'"
            raise grpc.RpcError(msg.format(self.address, self.max_workers))

        # create server instance
        if not self._server:
            self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))
            self._server.add_insecure_port(address=self.address)

        # add route
        for name, route in six.iteritems(self.route):
            route["add_function"](route["service"](), self._server)

        return self

    def start(self, address=None, max_workers=None, sleep_time=None):
        """Start server instance.

            :param sleep_time: sleep server time;
            :type sleep_time: int;
            :param address: server listen address;
            :type address: str;
            :param max_workers: workers count;
            :type max_workers: int.

        """

        self.config_server(address=address, max_workers=max_workers)
        self._server.start()

        try:
            while True:
                time.sleep(sleep_time or self.SERVER_TIMEOUT_SLEEP)  # one day in seconds
        except KeyboardInterrupt:
            self._server.stop(0)
