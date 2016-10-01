import six
from argparse import Namespace
from abc import ABCMeta, abstractmethod

from .server import GRPCServer
from .client import GRPCClient
from .parser import GRPCParser


# TODO: Create empty env and env from
# TODO: Add parse messages into messages
class GRPCEnvironment:
    """gRPC environment class.

        - Simple crete service(s) class;
        - Simple create stub(s) class;
        - Add abstract methods to service class flag;
        - Add messages class as attribute service class.

    """

    add_abstract = True
    server_class = GRPCServer
    client_class = GRPCClient
    parser_class = GRPCParser

    def __init__(self, proto_py_module, *names):
        self.proto_py_module = proto_py_module
        self.names = names  # can be services ot
        self._stubs = None
        self._services = None
        self._messages = None

    @classmethod
    def create_services(cls, proto_py_module, *service_names):
        """Create services use service_names.

            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param service_names: create service names;
            :type service_names: tuple with str (service name);

            :return; object with services classes.

        """

        return cls(proto_py_module, *service_names).services

    @classmethod
    def create_service(cls, proto_py_module, service_name):
        """Create service use service name.

            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param service_name: create service name;
            :type service_name: str;

            :return; service class.

        """

        return cls.create_services(proto_py_module, service_name)

    @classmethod
    def create_server(cls, proto_py_module=None, address=None, max_workers=10, service_names=()):
        """Create server instance.

            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param address: ip address and port;
            :type address: str;
            :param max_workers: maximum worker instance in concurrent futures;
            :type max_workers: int;
            :param service_names: add service names;
            :type service_names: tuple with str;

            :return: server instance.

        """

        return cls.server_class(proto_py_module=proto_py_module,
                                address=address,
                                max_workers=max_workers,
                                service_names=service_names)

    @classmethod
    def create_stubs(cls, proto_py_module, *stub_names):
        """Create stubs use stub_names.

            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param stub_names: create stub names;
            :type stub_names: str;

            :return: object with client class.

        """

        return cls(proto_py_module, *stub_names).stubs

    @classmethod
    def create_stub(cls, proto_py_module, stub_name):
        """Create stub use stub_name.

            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param stub_name: create stub name;
            :type stub_name: str;

            :return: object with client class.

        """

        return cls.create_stubs(proto_py_module, stub_name)

    @classmethod
    def create_client(cls, proto_py_module=None, address=None, stub_names=()):
        """Create client instance.

            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param address: ip address and port;
            :type address: str;
            :param stub_names: add stub names;
            :type stub_names: tuple with str;

            :return: client instance.

        """

        return cls.client_class(proto_py_module, address, stub_names)

    @property
    def services(self):
        """Service class creator.

            :return: service or services class.

        """

        if not self._services:

            # create services
            self._services = Namespace()
            services = self.parser_class.parse_module("service", self.proto_py_module)
            actual_names = self.names or services.keys()
            for service_name, params in filter(lambda srv: srv[0] in actual_names, six.iteritems(services)):

                # create server: add messages class and abstract methods
                methods = dict(messages=Namespace(**params["messages"]))
                if self.add_abstract:
                    methods.update({method_name: abstractmethod(lambda *args, **kwargs: NotImplemented())
                                    for method_name in params["methods"]})
                    service = six.add_metaclass(ABCMeta)(type(service_name, (params["service_class"],), methods))

                # create server: without abstract methods
                else:
                    service = type(service_name, (params["service_class"],), methods)

                # add new service class
                setattr(self._services, service_name, service)

        return self._services

    @property
    def stubs(self):
        """Stub class creator.

            :return: stub or stubs class.

        """

        if not self._stubs:

            # create stubs
            self._stubs = Namespace()
            stubs = self.parser_class.parse_module("stub", self.proto_py_module)
            actual_names = self.names or stubs.keys()
            for stub_name, params in filter(lambda stb: stb[0] in actual_names, six.iteritems(stubs)):
                # create stub
                stub = type(stub_name, (params["stub_class"],), dict(message=Namespace(**params["messages"])))
                setattr(self.stubs, stub_name, stub)

        return self._stubs
