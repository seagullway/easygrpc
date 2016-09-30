import sys
import inspect
import importlib

import os
from grpc.tools import protoc
from easygrpc.parser import GRPCParser
from grpcadmin.service_template import ServiceTemplate

ENCODING = 'utf-8'
PROTO_BUF_DIR = 'proto_buf'
PROTO_PY_DIR = 'proto_py'
SERVICES_DIR = 'services'
INIT_FILE = '__init__.py'
PROTO_FORMAT = '.proto'
PROTO_TEMPLATE = 'syntax="proto2";\n'
SERVICE_HEADER = """"""


def create_service(name):
    """Creating stub dirs service

    :param name: services name
    :type name: str
    """

    # create common dir for service
    os.makedirs(name, exist_ok=False)

    # create proto_buf dir with proto file
    os.makedirs(os.path.join(name, PROTO_BUF_DIR))
    with open(os.path.join(name, PROTO_BUF_DIR, name + PROTO_FORMAT), 'w', encoding=ENCODING) as f:
        f.write(PROTO_TEMPLATE)

    # create package proto_py
    os.makedirs(os.path.join(name, PROTO_PY_DIR))
    open(os.path.join(name, PROTO_PY_DIR, INIT_FILE), 'w').close()

    # create package services
    os.makedirs(os.path.join(name, SERVICES_DIR))
    open(os.path.join(name, SERVICES_DIR, INIT_FILE), 'w').close()


def run_code_generator(services):
    """Compile services to python from proto files

    :param services: names of the services
    :type services: list of str
    :return:
    """
    for name in services:
        protoc.main((
            '',
            '-I./proto_buf',
            '--python_out=./proto_py',
            '--grpc_python_out=./proto_py',
            './proto_buf/{}.proto'.format(name),
        ))


def check_where_am_i():
    if not os.path.isdir(PROTO_BUF_DIR):
        raise FileNotFoundError("Directory {} not found".format(PROTO_BUF_DIR))
    if not os.path.isdir(PROTO_PY_DIR):
        raise FileNotFoundError("Directory {} not found".format(PROTO_PY_DIR))
    if not os.path.isdir(SERVICES_DIR):
        raise FileNotFoundError("Directory {} not found".format(SERVICES_DIR))


def get_all_services():
    """ Get all names of the services from proto_buf directory

    :return: list of service names
    """
    # get all proto files from proto_buf dir
    proto_files = [f for f in os.listdir(PROTO_BUF_DIR)
                   if os.path.isfile(os.path.join(PROTO_BUF_DIR, f)) and f.endswith('.proto')]
    all_services = [os.path.splitext(f)[0] for f in proto_files]
    if not all_services:
        raise FileNotFoundError("Directory {} hasn't got any proto files".format(PROTO_BUF_DIR))
    return all_services


def get_necessary_service_names(include, exclude, all_services):
    """Get necessary service names from all_services

    :param include: names of the services which will be included
    :type include: tuple
    :param exclude: names of the services which will be excluded
    :type exclude: tuple
    :param all_services: list of service names
    :return: list if necessary service names
    """
    services = []
    for include_service in include:
        if include_service not in all_services:
            raise FileNotFoundError("Service can't be included because file {}.proto is already "
                                    "missing in {} directory".format(include_service, PROTO_BUF_DIR))
        services.append(include_service)
    services = services or all_services

    for exclude_service in exclude:
        try:
            services.remove(exclude_service)
        except ValueError:
            print("Service {} can't be excluded".format(exclude_service))
    if not services:
        raise NameError('List of services is empty')
    return services


def compile_services(include, exclude):
    """Compile proto files to python.
    If "include" argument is empty all services will be compiled

    :param include: names of the services will be included
    :type include: tuple
    :param exclude: names of the services won't be included
    :type exclude: tuple
    """

    # check where am I
    check_where_am_i()

    all_services = get_all_services()

    # get necessary service names
    services = get_necessary_service_names(include, exclude, all_services)

    # compile
    run_code_generator(services)


def get_reflection_info(module):
    """ Get info about classes and methods in module

    :param module: module
    :type module: import module instance;
    :return: dict with key pb2, value - dict with classes name: set of methods
    """
    classes = dict()
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            classes[obj.__name__] = {func for func in dir(obj) if
                                     callable(getattr(obj, func)) and not func.startswith('_')}
    return classes


def create_or_update_service(services, service_py_file, name_service_dir):
    # prepare
    # # TODO: remove this insert sys path
    sys.path.insert(1, os.getcwd())

    actual_service_info = {}
    for service in services:
        service_pb2 = importlib.import_module("proto_py." + service + "_pb2")
        pb2_info = GRPCParser.parse_module('service', service_pb2)
        service_methods_dict = {}
        for service_name, info in pb2_info.items():
            service_methods_dict[service_name] = info['methods']
        actual_service_info[service] = service_methods_dict

    # print(actual_service_info)
    service_exist = os.path.isfile(service_py_file)
    if service_exist:
        service_module = importlib.import_module("services." + name_service_dir)
        before_service = get_reflection_info(service_module)
        print(before_service)
        return
    with open(service_py_file, 'w') as f:
        f.write(ServiceTemplate.generate(actual_service_info))


def add_service_stub(include, exclude):
    """@TODO

    :param include: names of the services which stubs will be created
    :type include: tuple
    :param exclude: names of the services which stubs won't be created
    :type exclude: tuple
    """
    # check where am I
    check_where_am_i()

    current_dir = os.getcwd()
    service_name = os.path.split(current_dir)[1]
    service_py_file = os.path.join(current_dir, SERVICES_DIR, service_name + '.py')


    # get necessary service names
    all_services = get_all_services()
    services = get_necessary_service_names(include, exclude, all_services)

    # # create or update service
    create_or_update_service(services, service_py_file, service_name)


    # sys.path.insert(1, os.getcwd())
    #
    # sw_test1_pb2 = importlib.import_module("proto_py.sw_test1_pb2")
    # d = GRPCParser.parse_module('service', sw_test1_pb2)
    # print(d)
    #
    # sw_test2_pb2 = importlib.import_module("proto_py.sw_test_a_pb2")
    # t = GRPCParser.parse_module('service', sw_test2_pb2)
    # print(t)
    #
    # print(services)

    # if not service_exist:
    #     open(service_py_file, 'w').close()


if __name__ == '__main__':
    add_service_stub((), ())
    # print(dir())