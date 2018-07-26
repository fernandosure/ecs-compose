import re
import os
from utils import merger
from ecs import EcsTaskDefinition


class StackDefinitionException(Exception):
    pass


class LogConfigurationException(Exception):
    pass


class StackDefinition(object):
    def __init__(self, json_stack):

        if json_stack.get("vpc") is not None:
            self.vpc = VPCDefinition(json_stack.get("vpc"))

        if json_stack.get("defaults") is None:
            raise StackDefinitionException("Stack Definition: defaults section is required")
        else:
            self.defaults = DefaultsDefinition(json_stack.get("defaults"))

        if json_stack.get("services") is None:
            raise StackDefinitionException("Stack Definition: services section is required")
        else:
            self.services = [ServiceDefinition(x, json_stack) for x in json_stack.get("services", [])]

        self.service_discovery = ServiceDiscoveryDefaults(json_stack.get("service_discovery")) if json_stack.get("service_discovery") else None


class ServiceDiscoveryDefaults(object):
    def __init__(self, json_spec):

        self.namespace = json_spec.get("namespace", None)


class LogConfiguration(object):
    def __init__(self, json_spec):

        self.log_driver = json_spec.get("log_driver", None)
        self.options = json_spec.get("options", None)

        if self.options is not None and self.log_driver is None:
            raise LogConfigurationException("Log Configuration: Log Driver Required")

    def to_aws_json(self):

        if self.log_driver is None and self.options is None:
            return {}
        else:
            ret = {}
            if self.log_driver:
                ret["logDriver"] = self.log_driver

            if self.options:
                ret["options"] = self.options

            return ret


class VPCDefinition(object):
    def __init__(self, json_spec):
        self.id = json_spec.get("id")
        self.subnets = SubnetsDefinition(json_spec.get("subnets", {}))
        self.security_groups = SecurityGroupsDefinition(json_spec.get("security_groups", {}))


class SubnetsDefinition(object):
    def __init__(self, json_spec):
        self.public = json_spec.get("public", [])
        self.private = json_spec.get("private", [])


class SecurityGroupsDefinition(object):
    def __init__(self, json_spec):
        self.public = json_spec.get("public",[])
        self.private = json_spec.get("private",[])


class DefaultsDefinition(object):
    def __init__(self, json_spec):
        self.memory = json_spec.get("memory", 1024)
        self.environment = [{"name": y.keys()[0], "value": str(y[y.keys()[0]])} for y in json_spec.get("environment", [])]
        self.healthcheck = HealthCheckDefinition(json_spec.get("healthcheck")) if json_spec.get("healthcheck") else None


class ServiceDefinition(object):
    def __init__(self, json_spec, json_stack):
        self.defaults = DefaultsDefinition(json_stack.get("defaults"))
        self.name = json_spec.keys()[0]
        self.json = json_spec[self.name]

        self.type = self.json.get("type", "service")
        self.memory = self.json.get("memory", self.defaults.memory)
        self.desired_count = self.json.get("desired_count", 1)
        self.image = self.json.get("image")

        # ENVIRONMENTS
        environment = [{"name": y.keys()[0], "value": str(y[y.keys()[0]])} for y in self.json.get("environment", [])]
        environment.extend([g for g in self.defaults.environment if len([v for v in environment if v["name"] == g["name"]]) == 0])

        self.environment = environment
        self.privileged = self.json.get("privileged", False)
        self.elb = ElbDefinition(self.json.get("elb")) if self.json.get("elb") else None
        self.dns_discovery = DNSServiceDiscovery(self.json.get("dns_discovery")) if self.json.get("dns_discovery") else None

        regex = re.compile("([0-9]{4}):([0-9]{4})")
        self.ports = [{"hostPort": int(x.group(1)), "containerPort": int(x.group(2))} for y in self.json.get("ports", []) for x in [regex.search(y)] if x]

        regex = re.compile("(.+):(.+):(.+)")
        self.volumes = [{"name": x.group(1), "host": x.group(2), "container": x.group(3)} for y in self.json.get("volumes",[]) for x in [regex.search(y)] if x]

        self.scheduling_strategy = self.json.get("scheduling_strategy", "REPLICA")

        merge_rs = merger.merge(json_stack.get("logging", {}), self.json.get("logging", {}))
        self.log_configuration = LogConfiguration(merge_rs)

        self.healthcheck = None

        if self.defaults.healthcheck:
            self.healthcheck = self.defaults.healthcheck

        if self.json.get("healthcheck"):
            self.healthcheck = HealthCheckDefinition(self.json.get("healthcheck"))

    def get_task_definition(self, cluster):
        family = "%s-%s" % (cluster, self.name)

        # ENVIRONMENTS
        environments = self.environment
        environments.extend([g for g in self.defaults.environment if
                             len([v for v in self.environment if v["name"] == g["name"]]) == 0])

        pattern = re.compile(r"\$\{(.*)\}")
        for env in environments:
            match = re.search(pattern, env["value"])
            if match:
                env["value"] = os.getenv(match.group(1))

        td = {
            "family": family,
            "networkMode": "host" if self.dns_discovery is None else "awsvpc",
            "containerDefinitions": [
                {
                    "name": self.name,
                    "image": self.image,
                    "essential": True,
                    "memory": self.memory,
                    "privileged": self.privileged,
                    "logConfiguration": self.log_configuration.to_aws_json(),
                    "environment": environments,
                    "portMappings": self.ports,
                    "mountPoints": [{
                        "sourceVolume": x["name"],
                        "containerPath": x["container"],
                        "readOnly": False
                    } for x in self.volumes]
                }
            ],
            "volumes": [{
                "name": x["name"],
                "host": {"sourcePath": x["host"]}
            } for x in self.volumes]
        }

        if self.healthcheck:
            td["containerDefinitions"][0]["healthCheck"] = self.healthcheck.to_aws_json()

        return EcsTaskDefinition(td)


class DNSServiceDiscovery(object):
    def __init__(self, json_spec):
        self.name = json_spec.get("name")
        self.healthcheck = ServiceHealthCheck(json_spec.get("healthcheck", {}))


class ElbDefinition(object):
    def __init__(self, json_spec):
        self.name = json_spec.get("name", "")
        self.type = json_spec.get("type")
        self.ports = ServicePortsDefinition(json_spec.get("ports"))
        self.dns = ElbDnsDefinition(json_spec.get("dns"))
        self.certificates = [{"CertificateArn": x} for x in json_spec.get("certificates", [])]
        self.healthcheck = ServiceHealthCheck(json_spec.get("healthcheck", {}))
        self.protocol = json_spec.get("protocol", "HTTP")


class ServiceHealthCheck(object):
    def __init__(self, json_spec):
        self.protocol = json_spec.get("protocol", "HTTP")
        self.port = json_spec.get("port")
        self.path = json_spec.get("path", "/")
        self.interval_seconds = json_spec.get("interval_seconds", 30)
        self.timeout_seconds = json_spec.get("timeout_seconds", 5)
        self.healthy_threshold_count = json_spec.get("healthy_threshold_count", 2)
        self.unhealthy_threshold_count = json_spec.get("unhealthy_threshold_count", 10)
        self.failure_threshold = json_spec.get("FailureThreshold", 1)


class ServicePortsDefinition(object):
    def __init__(self, json_spec):
        self.public = json_spec.get("public")
        self.container = json_spec.get("container")


class ElbDnsDefinition(object):
    def __init__(self, json_spec):
        self.hosted_zone_id = json_spec.get("hosted_zone_id")
        self.record_name = json_spec.get("record_name")


class HealthCheckDefinition(object):
    def __init__(self, json_spec):
        self.command = json_spec.get("command", [])
        self.interval = json_spec.get("interval", 30)
        self.timeout = json_spec.get("timeout", 5)
        self.retries = json_spec.get("retries", 3)
        self.start_period = json_spec.get("start_period", 0)

    def to_aws_json(self):
        return {
            "command": self.command,
            "interval": self.interval,
            "timeout": self.timeout,
            "retries": self.retries,
            "startPeriod": self.start_period
        }
