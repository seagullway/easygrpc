class ServiceTemplate(object):
    """ServiceTemplate presents builder for python module one grpc-service."""

    @staticmethod
    def get_header():
        """Generate python's code for import modules.

            :return: str presentation of code.

        """

        return 'import importlib\n\nfrom easygrpc.environment import GRPCEnvironment\n\n\n'

    @staticmethod
    def get_start_service(pb2_name):
        """Generate python's code for importlib

            :param pb2_name: class name;
            :type pb2_name: str;

            :return: str presentation of code.

        """

        return ('{0} = importlib.import_module("proto_py.{0}")\n'
                'services = GRPCEnvironment.create_services({0})\n\n\n').format(pb2_name)

    @staticmethod
    def get_class(service_name):
        """Generate python's code class.

            :param service_name: class name;
            :type service_name: str;

            :return: str presentation of class.

        """

        return ('class {0}(services.{0}):\n'
                '    \"\"\"\"\"\"\n\n').format(service_name)

    @staticmethod
    def get_method(method_name):
        """Generate python's code method.

            :param method_name: method name;
            :type method_name: str;

            :return: str presentation of method.

        """

        return ('    def {}(self, request, context):\n'
                '        \"\"\"\"\"\"\n\n'
                '        raise NotImplementedError()\n\n').format(method_name)

    @staticmethod
    def generate(service_info):
        """Generate python's code module.

            :param service_info: information about generated service;
            :type service_info: instance of ServiceInfo;

            :return: str presentation of module.

        """

        result = ServiceTemplate.get_header()
        result += ServiceTemplate.get_start_service(service_info.pb2_name)
        result += ServiceTemplate.get_class(service_info.service_name)
        for method_name in service_info.methods:
            result += ServiceTemplate.get_method(method_name)

        return result
