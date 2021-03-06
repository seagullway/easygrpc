import os
import sys
import inspect
import importlib

from easygrpc.parser import GRPCParser
from grpc.tools import protoc
from grpcadmin.utils.service_info import ServiceInfo
from grpcadmin.utils.service_template import ServiceTemplate

ENCODING = 'utf-8'
PROTO_BUF_DIR = 'proto_buf'
PROTO_PY_DIR = 'proto_py'
ROUTES_DIR = 'routes'
INIT_FILE = '__init__.py'
PROTO_FORMAT = '.proto'
PROTO_TEMPLATE = 'syntax="proto3";\n\npackage {};\n'
SERVICE_HEADER = """"""


class ServiceBuilder(object):
    """Service builder class.

        - Simple crete instance ServiceBuilder;
        - Create instance ServiceBuilder and check current dir;
        - Create hierarchy of service;
        - Compile proto files to python;
        - Create or update services in routes directory.

    """

    def __init__(self, name, proto_buf_dir=None, proto_py_dir=None, routes_dir=None):
        self.name = name  # service name
        self.proto_buf_dir = proto_buf_dir or os.path.join(name, PROTO_BUF_DIR)
        self.proto_py_dir = proto_py_dir or os.path.join(name, PROTO_PY_DIR)
        self.routes_dir = routes_dir or os.path.join(name, ROUTES_DIR)

    @classmethod
    def create_builder(cls):
        """Create instance ServiceBuilder and check current dir.

            :return: instance of ServiceBuilder.

        """

        current_dir = os.getcwd()
        name = os.path.split(current_dir)[1]
        if os.path.isdir(PROTO_BUF_DIR):
            proto_buf_dir = PROTO_BUF_DIR
            proto_py_dir = PROTO_PY_DIR
            routes_dir = ROUTES_DIR
        else:
            raise FileNotFoundError('You should be in directory where {}, {} and '
                                    '{} directories are located'.format(PROTO_BUF_DIR, PROTO_PY_DIR, ROUTES_DIR))
        return cls(name, proto_buf_dir, proto_py_dir, routes_dir)

    def create_service(self):
        """Create stub dirs service."""

        if os.path.isdir(self.name):
            raise FileNotFoundError("Directory {} already exist".format(self.name))

        name_path = os.path.join(self.name, self.name)

        # create common dir for service
        os.makedirs(name_path)

        # create proto_buf dir with proto file
        os.makedirs(os.path.join(name_path, PROTO_BUF_DIR))
        with open(os.path.join(name_path, PROTO_BUF_DIR, self.name + PROTO_FORMAT), 'w', encoding=ENCODING) as f:
            f.write(PROTO_TEMPLATE.format(self.name))

        # create package proto_py
        os.makedirs(os.path.join(name_path, PROTO_PY_DIR))
        open(os.path.join(name_path, PROTO_PY_DIR, INIT_FILE), 'w').close()

        # create package services
        os.makedirs(os.path.join(name_path, ROUTES_DIR))
        open(os.path.join(name_path, ROUTES_DIR, INIT_FILE), 'w').close()

    def compile_proto_files(self, include, exclude):
        """Compile proto files to python.
            If "include" and "exclude" arguments are empty all services will be compiled.

            :param include: proto files will be included;
            :type include: tuple;
            :param exclude: proto files will be excluded;
            :type exclude: tuple.

        """

        self._run_code_generator(self._get_necessary_proto_files(include, exclude, self._get_all_proto_files()))

    def create_or_update_routes(self):
        """Create or update services in routes directory."""

        # find pb_2 names
        pb2_names = [os.path.splitext(f)[0] for f in os.listdir(self.proto_py_dir) if
                     os.path.isfile(os.path.join(self.proto_py_dir, f)) and not f.endswith('__.py')]

        # Parse current pb2 modules and Fill ListServiceInfo
        sys.path.insert(1, os.getcwd())
        list_service_info = []
        for pb2_name in pb2_names:
            pb2_module = importlib.import_module("{}.{}".format(self.proto_py_dir.replace('/', '.'), str(pb2_name)))
            pb2_info = GRPCParser.parse_module('service', pb2_module)
            list_service_info.extend(
                [ServiceInfo(pb2_name, s_name, info['methods']) for s_name, info in pb2_info.items()])

        # create or update files
        for service_info in list_service_info:
            service_py_file = os.path.join(self.routes_dir, "{}.py".format(service_info.service_name_lower))
            if os.path.isfile(service_py_file):
                service_module = importlib.import_module("{}.{}".format(self.routes_dir.replace('/', '.'),
                                                                        service_info.service_name_lower))

                # find service class object by name
                for _, member in inspect.getmembers(
                        service_module, lambda obj: inspect.isclass(obj) and obj.__name__ == service_info.service_name):
                    service_class = member
                    break
                else:
                    # class is not presented in module - so do nothing for current service
                    print('WARNING. Service {1} has not created. '
                          'Module {0} exists but class {1} is not presented. Remove file "routes/{0}.py" and try again'.
                          format(service_info.service_name_lower, service_info.service_name))
                    continue

                # class is presented - so append methods if necessary
                # find set of methods name in service class
                presented_methods = {name for name, func in service_class.__dict__.items()
                                     if inspect.isfunction(func) and not name.startswith('_')}
                should_append_methods = [m for m in service_info.methods if m not in presented_methods]
                if not should_append_methods:
                    continue
                with open(service_py_file, 'a') as f:
                    for method in should_append_methods:
                        f.write(ServiceTemplate.get_method(method))
                continue

            with open(service_py_file, 'w') as f:
                f.write(ServiceTemplate.generate(service_info))

    def _get_all_proto_files(self):
        """ Get all names of the services from proto_buf directory.

            :return: list of service names.

        """

        # get all proto files from proto_buf dir
        all_proto_files = [os.path.splitext(f)[0] for f in os.listdir(self.proto_buf_dir)
                           if os.path.isfile(os.path.join(self.proto_buf_dir, f)) and f.endswith('.proto')]
        if not all_proto_files:
            raise FileNotFoundError("Directory {} hasn't got any proto files".format(self.proto_buf_dir))

        return all_proto_files

    @staticmethod
    def _get_necessary_proto_files(include, exclude, all_proto_files):
        """Get necessary proto files from all_proto_files.

            :param include: proto files will be included;
            :type include: tuple;
            :param exclude: proto files will be excluded;
            :type exclude: tuple;
            :param all_proto_files: list of proto_files;
            :type all_proto_files: list of str;

            :return: list of str, list of necessary proto files.

        """

        services = []
        for include_service in include:
            if include_service not in all_proto_files:
                raise FileNotFoundError("Service can't be included because file {}.proto is already "
                                        "missing in {} directory".format(include_service, PROTO_BUF_DIR))
            services.append(include_service)
        services = services or all_proto_files

        for exclude_service in exclude:
            try:
                services.remove(exclude_service)
            except ValueError:
                print("Service {} can't be excluded".format(exclude_service))
        if not services:
            raise NameError('List of services is empty')

        return services

    def _run_code_generator(self, proto_files):
        """Compile proto files to python.

            :param proto_files: proto files;
            :type proto_files: list of str.

        """

        for name in proto_files:
            protoc.main((
                '',
                '-I./{}'.format(self.proto_buf_dir),
                '--python_out=./{}'.format(self.proto_py_dir),
                '--grpc_python_out=./{}'.format(self.proto_py_dir),
                './{}/{}.proto'.format(self.proto_buf_dir, name),
            ))
