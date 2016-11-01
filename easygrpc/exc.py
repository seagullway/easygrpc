class GRPCError(BaseException):
    """gRPC global error class."""


class GRPCRequestError(GRPCError):
    """gRPC request error: unexpected request (signature or data type)."""


class GRPCServiceError(GRPCError):
    """gRPC service error: global service error."""


class GRPCClientError(GRPCError):
    """gRPC client error: client global error."""
