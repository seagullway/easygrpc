from itertools import chain
from collections import defaultdict
from inspect import getmembers, isclass, isfunction

import six


# TODO: Add parse special type
# TODO: Add special search methods method (check change server config)
class GRPCParser(object):

    @staticmethod
    def parse_module(type_instance, proto_py_module):
        """Parse gRPCio generate py module.

            :param type_instance: type app: service or stub;
            :type type_instance: str;
            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;

            :return: services default dict parameters with service: object, messages and method names.

        """

        # mappers
        mapper_services = defaultdict(dict)
        mapper_methods = defaultdict(set)
        mapper_messages = defaultdict(set)

        # patched proto_py_module
        GRPCParser._patch_proto_py_module(type_instance=type_instance,
                                          proto_py_module=proto_py_module,
                                          mapper_methods=mapper_methods,
                                          mapper_messages=mapper_messages)

        # service parameters
        services = {}
        messages = {}
        creators = {}

        # analysis
        for name, service_class in getmembers(proto_py_module):

            # service classes
            if GRPCParser._check_service(service_class, type_instance=type_instance):
                services[name.replace(type_instance == "service" and "Servicer" or "Stub", "")] = service_class

            # change messages methods FromString and SerializeToString
            elif GRPCParser._check_message(service_class):
                messages[name] = service_class
                service_class.FromString_ = service_class.FromString
                service_class.SerializeToString_ = service_class.SerializeToString
                service_class.FromString = lambda name_=name, *args, **kwargs: name_
                service_class.SerializeToString = lambda name_=name, *args, **kwargs: name_

            # creator functions
            elif GRPCParser._check_creator(service_class):
                service_postfix = {"service": "server", "stub": "stub"}[type_instance]
                if name.endswith(service_postfix):
                    new_name = name.replace("beta_create_", "").replace("_{}".format(service_postfix), "")
                    creators[new_name] = service_class

        # messages and methods for services
        service_mock = type("MockServer", (object,), {"__getattr__": lambda self, val: None})()
        for creator_name, creator_obj in six.iteritems(creators):
            creator_obj(service_mock, pool=type_instance)

        # create final mapper
        for name_service, service_class in six.iteritems(services):
            mapper_services[name_service] = {
                "{}_class".format(type_instance): service_class,
                "messages": {name: messages[name] for name in mapper_messages.get(name_service, set())},
                "methods": mapper_methods.get(name_service, set())
            }

        # override messages methods FromString and SerializeToString
        for message in six.itervalues(messages):
            message.FromString = message.FromString_
            message.SerializeToString = message.SerializeToString_
            delattr(message, "FromString_")
            delattr(message, "SerializeToString_")

        # override patch
        GRPCParser._patch_proto_py_module(type_instance=type_instance, proto_py_module=proto_py_module)

        return mapper_services

    @staticmethod
    def _patch_proto_py_module(type_instance, proto_py_module, mapper_methods=None, mapper_messages=None):
        """Patch proto py module to get information about service(s) or stub(s).

            :param type_instance: type app: server or client;
            :type type_instance: str;
            :param proto_py_module: proto .py module generated by gRPCio;
            :type proto_py_module: import module instance;
            :param mapper_methods: mapper methods default dict;
            :type mapper_methods: default dict with set;
            :param mapper_messages: mapper methods default dict;
            :type mapper_messages: default dict with set.

        """

        if not hasattr(proto_py_module, "patched"):

            # save old beta_implementations
            real_beta_implementations = proto_py_module.beta_implementations

            # patch proto_py_module
            def check_use_messages(cls, **kwargs):
                """Check user messages (and methods) and save it to mappers."""

                response, request = kwargs.get("response_deserializers", {}), kwargs.get("request_serializers", {})
                if type_instance == "service":
                    response, request = kwargs.get("response_serializers", {}), kwargs.get("request_deserializers", {})
                for (service_name, method_name), serializer in chain(six.iteritems(response), six.iteritems(request)):
                    service_name = service_name.split('.')[-1]
                    mapper_methods[service_name].add(method_name)
                    mapper_messages[service_name].add(serializer())

            # patch proto_py_module with new new beta_implementation
            names = ("server_options", "server") if type_instance == "service" else ("stub_options", "dynamic_stub")
            methods = classmethod(check_use_messages), lambda *args, **kwargs: None
            proto_py_module.beta_implementations = type("MockChannel", (object,), dict(zip(names, methods)))

            # change beta_implementation
            setattr(proto_py_module, "patched", True)
            setattr(proto_py_module, "real_beta_implementations", real_beta_implementations)

        else:

            # override beta_implementation
            delattr(proto_py_module, "patched")
            proto_py_module.beta_implementations = getattr(proto_py_module, "real_beta_implementations")
            delattr(proto_py_module, "real_beta_implementations")

    @staticmethod
    def _check_service(obj, type_instance):
        """Check: object is service.

            :param obj: check object for service type;
            :type obj: any python object from module namespace;
            :param type_instance: type app: server or client;
            :type type_instance: str;

            :return: bool (True: obj is service, False: obj is not service).

        """

        ends = type_instance == "service" and "Servicer" or "Stub"

        return isclass(obj) and not obj.__name__.startswith("Beta") and obj.__name__.endswith(ends)

    @staticmethod
    def _check_message(obj):
        """Check message: object is message.

            :param obj: check object for service type;
            :type obj: any python object from module namespace;

            :return: bool (True: obj is message, False: obj is not message).

        """

        return isclass(obj) and hasattr(obj, "IsInitialized") and hasattr(obj, "SerializeToString")

    @staticmethod
    def _check_creator(obj):
        """Check creator function: object is creator function.

            :param obj: check object for service type;
            :type obj: any python object from module namespace;

            :return: bool (True: obj is creator function, False: obj is not creator function).

        """

        return isfunction(obj) and obj.__name__.startswith("beta_create_")
