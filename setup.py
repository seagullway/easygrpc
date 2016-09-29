from setuptools import setup, find_packages

setup(
    name='easy-grpc',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'grpcio',
        'grpcio-tools'
    ],
    entry_points='''
        [console_scripts]
        grpc-admin=grpcadmin.scripts:cli
    ''',
)