import click
from grpcadmin.utils.service_builder import ServiceBuilder


@click.group()
def cli():
    """Helper for creation grpc services"""
    pass


@cli.command()
@click.argument('name')
def create(name):
    """Service for creating stub dirs service.

    \b
    Example:
        $grpc-admin create example.
        This command create dirs for service "example" with stub proto file for future filling"""
    builder = ServiceBuilder(name)
    builder.create_service()


@cli.command()
@click.option('--include', '-i', multiple=True, type=click.STRING,
              help="Name of service will be compiled. It's multiple option. "
                   "If the option is missed all services will be compiled.")
@click.option('--exclude', '-e', multiple=True, type=click.STRING,
              help="Name of service won't be compiled. It's multiple option.")
def compile(include, exclude):
    """Compile proto files to python.
    The command compiles *.py files by proto files from directory: /proto_buf/<service_name>.proto
    You can explicitly include necessary files for compilation,
    otherwise grpc-admin will compile all proto files from proto_buf directory.

    \b
    Example1:
        $grpc-admin compile
        This command will compile all proto file from proto_buf directory

    \b
    Example2:
        $grpc-admin compile -e service1
        This command will compile all proto file from proto_buf directory except for service1

    \b
    Example3:
        $grpc-admin compile -i service1 -i service2
        This command will compile only two services: service1 and service2"""

    builder = ServiceBuilder.create_builder()
    builder.compile_proto_files(include, exclude)


# TODO: Change server environment
# @cli.command()
# @click.option('--address', '-a', default='', type=click.STRING, help='address')
# @click.option('--max_workers', '-m', default=1, type=click.IntRange(min=1, max=128), help='number of workers')
# @click.option('--protofile', '-p', multiple=True,
#               type=click.STRING, help="Proto file. It's multiple option.")
# def server(address, max_workers, protofile):
#     """comment"""
#     click.echo(address)
#     click.echo(max_workers)
#     click.echo(protofile)


@cli.command()
def routes():
    """Add stub services into routes directory

    \b
    Example1:
        $grpc-admin routes
        This command  will create stubs for all services in proto_py directory."""
    builder = ServiceBuilder.create_builder()
    builder.create_or_update_routes()

