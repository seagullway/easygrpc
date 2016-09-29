import os
from grpc.tools import protoc

ENCODING = 'utf-8'
PROTO_BUF_DIR = 'proto_buf'
PROTO_PY_DIR = 'proto_py'
SERVICES_DIR = 'services'
INIT_FILE = '__init__.py'
PROTO_FORMAT = '.proto'
PROTO_TEMPLATE = 'syntax="proto2";\n'


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

    # get all proto files from proto_buf dir
    proto_files = [f for f in os.listdir(PROTO_BUF_DIR)
                   if os.path.isfile(os.path.join(PROTO_BUF_DIR, f)) and f.endswith('.proto')]
    all_services = [os.path.splitext(f)[0] for f in proto_files]
    if not all_services:
        raise FileNotFoundError("Directory {} hasn't got any proto files".format(PROTO_BUF_DIR))

    # get necessary service names
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

    # compile
    run_code_generator(services)


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
    service_py_file = os.path.join(current_dir, SERVICES_DIR, service_name+'.py')
    service_exist = os.path.isfile(service_py_file)
    print(include)
    print(exclude)
    print(service_exist)
    if not service_exist:
        open(service_py_file, 'w').close()
