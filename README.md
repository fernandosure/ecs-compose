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
Deploy a complete ECS cluster with a single command:

    $ ecs-compose cluster deploy my-cluster -f my-services.yml


You just need to specify the services that will be deployed within the cluster in a YAML file like the following


YAML Configuration
-----------

You can form as well a YAML configuration file for use it when creating or updating a cluster definition (eg. POST / PUT /api/clusters).
Basically the YAML stackfile is similar in form to a docker-compose yaml file with the following structure

```
vpc:
  id: vpc-xxx
  subnets:
    public: ["subnet-xxx", "subnet-xxx"]
    private: ["subnet-xxx", "subnet-xxx"]

  security_groups:
    public: ["sg-xxx"]
    private: ["sg-xxx"]

logging:
  log_driver: awslogs
  options:
    awslogs-group: /ecs/staging
    awslogs-region: us-east-1
    awslogs-stream-prefix: svc

service_discovery:
  namespace: example.sd

defaults:
  memory: 930
  environment:
    - JAVA_OPTS: -Duser.timezone="UTC" -Xms256m -Xmx640m -XX:MaxMetaspaceSize=256m
    - SPRING_PROFILES_ACTIVE: staging
    - LOGGING_LEVEL_ROOT: INFO
    - SERVER_PORT: 80

services:

  - edge-service:
      image: xxx.dkr.ecr.us-east-1.amazonaws.com/edge-service:latest
      ports:
        - "8080:8080"
      environment:
        - SERVER_PORT: 8080
      desired_count: 1
      elb:
        type: public
        protocol: HTTPS
        ports:
          public: 443
          container: 8080
        certificates:
          - arn:aws:acm:us-east-1:xxx:certificate/xxx-xxx-xxx-xxx-xxx
        dns:
          hosted_zone_id: xxxx
          record_name: staging.example.com
        healthcheck:
          protocol: HTTP
          port: 8080
          path: /health
      deployment_configuration:
        maximum_percent: 100
        minimum_healthy_percent: 0
      placement_constraints:
        - expression: "attribute:ecs.instance-type =~ p3.*"
          type: "memberOf"
        - expression: "attribute:ecs.availability-zone == us-east-1a"
          type: "memberOf"

  - user-service:
      image: xxx.dkr.ecr.us-east-1.amazonaws.com/user-service:latest
      ports:
        - "80:80"
      desired_count: 1
      dns_discovery:
        name: user.staging

  - deeplearning:
      image: xxx.dkr.ecr.us-east-1.amazonaws.com/deep-learning:latest
      ports:
        - "8080:8080"
      desired_count: 1
      gpus: 1
      dns_discovery:
        name: deeplearning.staging
        
 # WORKERS NO PORTS EXPOSED
  - email-worker:
      image: xxx.dkr.ecr.us-east-1.amazonaws.com/email-worker:xxx

```


# VPC Section
```
vpc:
  id: vpc-xxx
  subnets:
    public: ["subnet-xxx", "subnet-xxx"]
    private: ["subnet-xxx", "subnet-xxx"]

  security_groups:
    public: ["sg-xxx"]
    private: ["sg-xxx"]
```
vpc
- id: the VPC id where the ECS cluster is located

vpc.subnets
- public: subnet-id where the public load balancers (if any) will be placed on
- private: subnet.id where the private load balancers (if any) will be placed on

vpc.security_groups
- public: the security group that will be attached to a public load balancer
- private: the security group that will be attached to private load balancer o service discovery service


# Logging Section
```
logging:
  log_driver: awslogs
  options:
    awslogs-group: /ecs/staging
    awslogs-region: us-east-1
    awslogs-stream-prefix: svc
```
In this section you specify the logging driver and (optional) the parameters to that specific driver. You can use gelf, awslogs, syslog, etc.


# Service Discovery Section
```
service_discovery:
  namespace: example.sd
```

In this section you specify the desired private namespace that will be used for registering the services using DNS based Service Discovery. You can't assign multilevel domains here, only top level domains are allowed e.g. example.local

# Defaults Section
```
defaults:
  memory: 930
  environment:
    - JAVA_OPTS: -Duser.timezone="UTC" -Xms256m -Xmx640m -XX:MaxMetaspaceSize=256m
    - SPRING_PROFILES_ACTIVE: staging
    - LOGGING_LEVEL_ROOT: INFO
    - SERVER_PORT: 80
```
In this section you need to specify the hard limit (in MiB) of memory to present to the container and the default environment variables that will be applied to all services within the stackfile. The reason behind the global environment section is preventing from copy and paste all over the place instead, if you need to overwrite a specific envvar you can declare that within the service definition and that envvar will have greater precedence over the global one.



# Service Section
## When a service needs to be publicly exposed in a public subnet.
```
services:
  - edge-service:
      image: xxx.dkr.ecr.us-east-1.amazonaws.com/edge-service:latest
      ports:
        - "8080:8080"
      environment:
        - SERVER_PORT: 8080
      desired_count: 1
      elb:
        type: public
        protocol: HTTPS
        ports:
          public: 443
          container: 8080
        certificates:
          - arn:aws:acm:us-east-1:xxx:certificate/xxx-xxx-xxx-xxx-xxx
        dns:
          hosted_zone_id: xxxx
          record_name: staging.example.com
        healthcheck:
          protocol: HTTP
          port: 8080
          path: /health

```
In this section you define an array of services that will be deployed in the cluster.
Each array item corresponds to a different service and you will need to specify the name of the service and then its properties.

- image: Specify the image to start the container from
- ports: if the service will expose ports to the outside then you need to specify those in short syntax (HOST:CONTAINER).
- environment: the environment variable declared in this section have greater precedence over the global definition and will overwrite the global one.
- desired_count: the number of desired instances for the service
- gpus: the number of gpu's assigned (when using gpu instances)
- placement_constraints: rules that are considered during task placement.
  - expression: A cluster query language expression to apply to the constraint. You cannot specify an expression if the constraint type is distinctInstance.
  - type: The type of constraint. Use distinctInstance to ensure that each task in a particular group is running on a different container instance. Use memberOf to restrict the selection to a group of valid candidates.
- deployment_configuration:
  - maximum_percent: represents an upper limit on the number of your service's tasks that are allowed in the RUNNING or PENDING state during a deployment, as a percentage of the desired number of tasks (rounded down to the nearest integer).
  - minimum_healthy_percent: represents a lower limit on the number of your service's tasks that must remain in the RUNNING state during a deployment, as a percentage of the desired number of tasks (rounded up to the nearest integer).
- elb: the application load balancer definition.
  - type: whether if the load balancer will be public (will be placed in the public subnet and a public security group assigned) or private (will be place in the private subnet and a private security group assigned)
  - protocol: The protocol for connections from clients to the load balancer (HTTP/HTTPS)
  - ports:
    - public: The port on which the load balancer is listening
    - container: The port on which the target container will receive traffic (this will need to match the public exposed port of the container)
  - certificates: a single item array of the AWS ACM (certificate manager) arn of the certificate to be applied to the ALB
  - dns:
    - hosted_zone_id: route53 hosted_zone_id for updating the CNAME record that the load balancer will listen requests from.
    - record_name: the route53 recordset of from which the ALB will listen requests from (if isnt already created it will create it automatically otherwise will update the recordset)
  - healthcheck: the configurations the load balancer uses when performing health checks on targets.
    - protocol: The protocol the load balancer uses when performing health checks on the container target.
    - port: The port the load balancer uses when performing health checks on the container target.
    - path: The ping path that is the destination on the targets for health checks. The default is /.

## When a service only needs to be reachable by other services that are part of the same cluster.
```
services:
  - user-service:
      image: xxx.dkr.ecr.us-east-1.amazonaws.com/user-service:latest
      ports:
        - "80:80"
      desired_count: 1
      dns_discovery:
        name: user.staging
```


- dns_discovery: When using this feature make sure that you already declared the service discovery namespace that will be used to register the services.
  - name: the name of the route53 recordset to be used by other services to reach this service (it will create an 'A' record) if you want to use the same namespace for different clusters make sure to split the name of the service into a multilevel domain (e.g. `<service_name>.<cluster_name/environment>.<namespace>`)

## When a service doesn't need to be exposed (worker services)
```
 - email-worker:
     image: xxx.dkr.ecr.us-east-1.amazonaws.com/email-worker:xxx
```
There aren't any exposed ports and no load balancer / service discovery configuration. Only the container image definition and if required (desired_count)



Installation
------------

The project is available on PyPI. Simply run::

    $ pip install ecs-compose


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
deploy / redeploys a single or multiple services at once defined in the YAML stackfile

destroy
=====
Destroy the entire AWS ECS Cluster with all services and attached load balancers associated with it.

describe
=====
List all deployed services within the specified cluster as YAML stackfile

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
