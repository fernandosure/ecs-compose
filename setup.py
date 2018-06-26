"""
    AWS ECS tools
"""
import os
import sys
from setuptools import find_packages, setup
from ecs_compose import VERSION
from setuptools.command.install import install

dependencies = [
    'botocore>=1.10.9',
    'boto3>=1.7.9',
    'jsonmerge>=1.5.0',
    'pyyaml>=3.12',
    'Click>=6.7',
    'jsondiff>=1.1.2'
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

with open('README.md', 'r') as f:
    long_description = f.read()


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version"""
    description = 'verify that the git tag matches our version'

    def run(self):
        tag = os.getenv('CIRCLE_TAG')

        if tag != VERSION:
            info = "Git tag: {0} does not match the version of this app: {1}".format(
                tag, VERSION
            )
            sys.exit(info)


setup(
    name='ecs-compose',
    version=VERSION,
    url='https://github.com/fernandosure/ecs-compose',
    download_url='https://github.com/fernandosure/ecs-compose/archive/%s.tar.gz' % VERSION,
    license='MIT',
    author='Fernando Sure',
    author_email='fernandosure@gmail.com',
    description='Amazon ECS cli for docker-compose like deployments',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'ecs-compose = ecs_compose.cli:cli',
        ],
    },
    cmdclass={
        'verify': VerifyVersionCommand,
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
