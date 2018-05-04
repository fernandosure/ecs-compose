import re


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
            self.services = [ServiceDefinition(x, self.defaults) for x in json_stack.get("services", [])]

        self.log_configuration = LogConfiguration(json_stack.get("logging", {}))

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
        str
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


class ServiceDefinition(object):
    def __init__(self, json_spec, defaults):
        self.name = json_spec.keys()[0]
        self.json = json_spec[self.name]
        self.image = self.json.get("image")
        self.type = self.json.get("type", "service")
        self.memory = self.json.get("memory", defaults.memory)
        self.environment = [{"name": y.keys()[0], "value": str(y[y.keys()[0]])} for y in self.json.get("environment", [])]
        self.desired_count = self.json.get("desired_count", 1)
        self.privileged = self.json.get("privileged", False)
        self.elb = ElbDefinition(self.json.get("elb")) if self.json.get('elb') else None
        self.dns_discovery = DNSServiceDiscovery(self.json.get("dns_discovery")) if self.json.get("dns_discovery") else None

        regex = re.compile("([0-9]{4}):([0-9]{4})")
        self.ports = [{"hostPort": int(x.group(1)), "containerPort": int(x.group(2))} for y in self.json.get("ports", []) for x in [regex.search(y)] if x]

        regex = re.compile("(.+):(.+):(.+)")
        self.volumes = [{"name": x.group(1), "host": x.group(2), "container": x.group(3)} for y in self.json.get("volumes",[]) for x in [regex.search(y)] if x]

        self.placement_strategy = {
                "placement_strategy": {
                    'type': 'spread',
                    'field': 'host'
                },
                "placement_constraints": {
                    "type": "distinctInstance"
                }
            } if self.json.get("placement_strategy") == "every_node" else None


class DNSServiceDiscovery(object):
    def __init__(self, json_spec):
        self.name = json_spec.get('name')
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
        self.failure_threshold = json_spec.get('FailureThreshold', 1)


class ServicePortsDefinition(object):
    def __init__(self, json_spec):
        self.public = json_spec.get("public")
        self.container = json_spec.get("container")


class ElbDnsDefinition(object):
    def __init__(self, json_spec):
        self.hosted_zone_id = json_spec.get("hosted_zone_id")
        self.record_name = json_spec.get("record_name")
