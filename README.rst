ECS Compose
----------

docker-compose like deployments for AWS Elastic Container Service

Key Features
------------
- easy to read / maintain deployment scripts
- deploy multiple services with a single command
- creates services with private (service-discovery) and internet-facing Application Load Balancers
- route53 integration when combining an ALB
- cluster specific or service customizable environment variables


TL;DR
-----
Deploy a complete ECS cluster with a single command::

    $ ecs-compose cluster deploy my-cluster -f my-services.yml


You just need to specify the services that will be deployed within the cluster in a YAML file like the following

.. code-block::

    vpc:
      id: vpc-xxx
      subnets:
        public: ["subnet-xxx", "subnet-xxx", "subnet-xxx"]
        private: ["subnet-xxx", "subnet-xxx", "subnet-xxx"]

      security_groups:
        public: ["sg-xxx"]
        private: ["sg-xxx"]

    logging:
      log_driver: gelf
      options:
        gelf-address: udp://logstash.local.dev:12201
        tag: dev1

    service_discovery:
      namespace: {internal-namespace || local.sd}


    defaults:
      memory: 1056
      environment:
        - JAVA_OPTS: -Duser.timezone="UTC" -Xms512m -Xmx768m -XX:MaxMetaspaceSize=256m
        - LOGGING_LEVEL_ROOT: INFO
        - LOGBACK_FORMAT: JSON

    services:
      - service1:
          image: xxx/service1:latest
          ports:
            - "8888:8888"
          desired_count: 1
          dns_discovery:
            name: service1.env

      - edge:
          image: xxx/edge:latest
          ports:
            - "8080:8080"
            - "8081:8081"
          environment:
            - PORT: 8080
          desired_count: 2
          elb:
            -
            type: public
            protocol: HTTPS
            ports:
              public: 443
              container: 8080
            certificates:
              - arn:aws:acm:us-east-1:xxxx:certificate/xxxx-xxxx-xxxx-xxx
            dns:
              hosted_zone_id: XXXXXX
              record_name: api.test.com
            healthcheck:
              protocol: HTTP
              port: 8081
              path: /health

      - auth-server:
          image: xxx/auth-server:latest
          desired_count: 2

      - my-service:
          image: xxx/my-service:latest
          desired_count: 1
          environment:
            - YOUR_ENVIRONMENT: your_value


Installation
------------

The project is available on PyPI. Simply run::

    $ easy_install ecs-compose


Configuration
-------------
The mechanism in which **ecs-compose** looks for credentials is to search through a list of possible locations and stop as soon as it finds credentials.

- Environment variables
- Shared credential file (~/.aws/credentials)
- AWS config file (~/.aws/config)
- Assume Role provider
- Boto2 config file (/etc/boto.cfg and ~/.boto)
- Instance metadata service on an Amazon EC2 instance that has an IAM role configured.

Please read the boto3 documentation for more details
(http://boto3.readthedocs.org/en/latest/guide/configuration.html#configuration).

Or just run::

    $ aws configure


Actions
-------
Currently the following actions are supported:

**Cluster related operations**

deploy
======
deploy / redeploys a single or multiple services at once defined in the YAML file

destroy
=====
Destroy the entire AWS ECS Cluster with all services and attached load balancers associated with it.

describe
=====
List all deployed services within the specified cluster as YAML file

**Individual service related operations**

destroy
=====
Destroy an individual service within the specified cluster with its load balancer associated with it.


Usage
-----

For detailed information about the available actions, arguments and options, run::

    $ ecs-compose --help
    $ ecs-compose cluster --help
    $ ecs-compose service --help
