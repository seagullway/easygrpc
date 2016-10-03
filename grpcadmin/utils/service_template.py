HEADER_TEMPLATE = 'import importlib\n\nfrom easygrpc.environment import GRPCEnvironment\n\n\n'


class ServiceTemplate(object):
    @staticmethod
    def get_header():
        return 'import importlib\n\nfrom easygrpc.environment import GRPCEnvironment\n\n\n'

    @staticmethod
    def get_start_service(pb2_name):
        result = '{0} = importlib.import_module("proto_py.{0}")\n'.format(pb2_name)
        result += 'services = GRPCEnvironment.create_services({})\n\n\n'.format(pb2_name)
        return result

    @staticmethod
    def get_class(service_name):
        return 'class {0}(services.{0}):\n\n'.format(service_name)

    @staticmethod
    def get_method(method_name):
        result = '    def {}(self, request, context):\n'.format(method_name)
        result += '        raise NotImplementedError()\n\n'
        return result

    @staticmethod
    def generate(service_info):

        result = ServiceTemplate.get_header()
        result += ServiceTemplate.get_start_service(service_info.pb2_name)
        result += ServiceTemplate.get_class(service_info.service_name)
        for method_name in service_info.methods:
            result += ServiceTemplate.get_method(method_name)
        return result
