import re


class ServiceInfo(object):
    """ServiceInfo class is flat presentation of grpc-service."""

    def __init__(self, pb2_name, service_name, methods):
        self.pb2_name = pb2_name
        self.service_name = service_name
        self.methods = methods

    @property
    def service_name_lower(self):
        """Convert CamelCase to snake_case."""

        return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                      re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.service_name)).lower()


