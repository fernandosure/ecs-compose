"""
    AWS ECS tools
"""
from setuptools import find_packages, setup
from ecs_compose import VERSION

dependencies = [
    'botocore',
    'boto3>=1.7.4',
    'jsonmerge>=1.5.0',
    'pyyaml>=3.12'
]

classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]

with open('README.rst', 'r') as f:
    long_description = f.read()


setup(
    name='ecs-compose',
    version=VERSION,
    url='https://github.com/fernandosure/ecs-compose',
    download_url='https://github.com/fernandosure/ecs-compose/archive/%s.tar.gz' % VERSION,
    license='MIT',
    author='Fernando Sure',
    author_email='fernandosure@gmail.com',
    description='Amazon ECS tools for docker-compose like deployments',
    long_description=long_description,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'ecs-compose = ecs_compose.cli:main',
        ],
    },
    keywords=['ECS', 'AWS'],
    tests_require=[
        'mock',
        'pytest',
        'pytest-flake8',
        'pytest-mock',
        'coverage'
    ],
    classifiers=classifiers
)
