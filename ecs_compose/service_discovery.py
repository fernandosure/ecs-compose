from datetime import datetime as dt
import boto3


class ServiceDiscovery(object):

    def __init__(self):
        self._client = boto3.client('servicediscovery')

    def get_namespace(self, namespace_id):

        try:
            rs = self._client.get_namespace(Id=namespace_id)
            return Namespace.from_json(rs['Namespace'])
        except:
            return None

    def list_namespaces(self):

        rs = self._client.list_namespaces()
        namespaces = [Namespace.from_json(namespace) for namespace in rs['Namespaces']]

        while rs.get('NextToken') is not None:
            rs = self._client.list_namespaces(nextToken=rs.get('NextToken'))
            namespaces.extend([Namespace.from_json(namespace) for namespace in rs['Namespaces']])
        return namespaces

    def create_namespace(self, namespace, vpc_id):

        rs = self._client.create_private_dns_namespace(Name=namespace, Vpc=vpc_id)

        start_time = dt.now()
        while (dt.now() - start_time).seconds < 60:
            rs = self.get_operation_status(rs['OperationId'])

            if rs.status == 'SUCCESS':
                return self.get_namespace(rs.resource_id)

            if rs.status == 'FAIL':
                raise Exception(rs.error_message)

        raise Exception('Timeout reached')

    def get_operation_status(self, operation_id):
        rs = self._client.get_operation(OperationId=operation_id)
        return OperationStatus.from_json(rs['Operation'], 'NAMESPACE')

    @staticmethod
    def get_or_create_namespace(name, vpc_id):
        svc = ServiceDiscovery()
        namespace = next((x for x in svc.list_namespaces() if x.name == name), None)
        if not namespace:
            return svc.create_namespace(name, vpc_id)
        else:
            return svc.get_namespace(namespace.id)

    def list_services(self):

        rs = self._client.list_services()
        lst = [Service.from_json(service) for service in rs['Services']]

        while rs.get('NextToken') is not None:
            rs = self._client.list_services(nextToken=rs.get('NextToken'))
            lst.extend([Service.from_json(service) for service in rs['Services']])
        return lst

    @staticmethod
    def get_or_create_service(**kwargs):
        svc = ServiceDiscovery()
        service = next((x for x in svc.list_services() if x.name == kwargs.get('Name')), None)
        if not service:

            if kwargs.get('DnsConfig') is None and kwargs.get('NamespaceId') is not None:
                kwargs['DnsConfig'] = {
                                        'NamespaceId': kwargs.get('NamespaceId'),
                                        'RoutingPolicy': 'WEIGHTED',
                                        'DnsRecords': [
                                            {
                                                'Type': 'A',
                                                'TTL': 300
                                            }
                                        ]
                                    }
                kwargs.pop('NamespaceId')

            if kwargs.get('HealthCheckCustomConfig') is None and kwargs.get('HealthCheckConfig') is None:
                kwargs['HealthCheckCustomConfig'] = {'FailureThreshold': 1}

            return svc.create_service(**kwargs)
        else:
            return svc.get_service(service.id)

    def create_service(self, **kwargs):
        rs = self._client.create_service(**kwargs)
        return Service.from_json(rs['Service'])

    def get_service(self, service_id):
        try:
            rs = self._client.get_service(Id=service_id)
            return Service.from_json(rs['Service'])
        except:
            return None


class Service(object):

    def __init__(self):
        self._client = boto3.client('servicediscovery')

    @classmethod
    def from_json(cls, value):
        cls.id = value.get('Id')
        cls.arn = value.get('Arn')
        cls.name = value.get('Name')
        cls.description = value.get('Description')
        cls.instance_count = value.get('ServiceCount')
        cls.dns_config = DNSConfig.from_json(value.get('DnsConfig')) if value.get('DnsConfig') else None
        cls.healthcheck_config = HealthCheckConfig.from_json(value.get('HealthCheckConfig')) if value.get('HealthCheckConfig') else None
        cls.healthcheck_custom_config = HealthCheckCustomConfig.from_json(value.get('HealthCheckCustomConfig')) if value.get('HealthCheckCustomConfig') else None
        return cls


class DNSConfig(object):

    @classmethod
    def from_json(cls, value):
        cls.namespace_id = value.get('NamespaceId')
        cls.routing_policy = value.get('RoutingPolicy')
        cls.dns_records = [DNSRecord.from_json(x) for x in value.get('DnsRecords')]
        return cls

    def to_json(self):
        return {
            'NamespaceId': self.namespace_id,
            'RoutingPolicy': self.routing_policy,
            'DnsRecords':  [x.to_json() for x in self.dns_records]
        }


class DNSRecord(object):

    @classmethod
    def from_json(cls, value):
        cls.type = value.get('Type')
        cls.ttl = value.get('TTL')
        return cls

    def to_json(self):
        return {
            'Type': self.type,
            'TTL': self.ttl
        }


class HealthCheckConfig(object):

    @classmethod
    def from_json(cls, value):
        cls.type = value.get('Type')
        cls.resource_path = value.get('ResourcePath')
        cls.failure_threshold = value.get('FailureThreshold')
        return cls

    def to_json(self):
        return {
            'Type': self.type,
            'ResourcePath': self.resource_path,
            'FailureThreshold': self.failure_threshold
        }


class HealthCheckCustomConfig(object):

    @classmethod
    def from_json(cls, value):
        cls.failure_threshold = value.get('FailureThreshold')
        return cls

    def to_json(self):
        return {
            'FailureThreshold': self.failure_threshold
        }


class Namespace(object):

    @classmethod
    def from_json(cls, value):
        cls.id = value.get('Id')
        cls.arn = value.get('Arn')
        cls.name = value.get('Name')
        cls.type = value.get('Type')
        cls.description = value.get('Description')
        cls.service_count = value.get('ServiceCount')
        cls.dns_properties = DNSProperties.from_json(value.get('DnsProperties')) if value.get('DnsProperties') else None
        return cls


class DNSProperties(object):

    @classmethod
    def from_json(cls, value):
        cls.hosted_zone_id = value['DnsProperties']['HostedZoneId']
        return cls


class OperationStatus(object):

    @classmethod
    def from_json(cls, value, target_key):
        cls.id = value.get('Id')
        cls.type = value.get('Type')
        cls.status = value.get('Status')
        cls.error_message = value.get('ErrorMessage')
        cls.error_code = value.get('ErrorCode')
        cls.create_date = value.get('CreateDate')
        cls.update_date = value.get('UpdateDate')
        cls.resource_id = value.get('Targets', {}).get(target_key)
        return cls
