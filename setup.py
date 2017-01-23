from setuptools import setup, find_packages

setup(
    name='easygrpc',
    version='0.2',
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