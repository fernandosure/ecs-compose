import boto3
import re
import os


class EcsClient(object):

    def __init__(self):
        self._client = boto3.client('ecs')

    def _describe_cluster(self, cluster):

        rs = self._client.describe_clusters(clusters=[cluster])
        ls = [EcsCluster(item) for item in rs[u'clusters']]
        return ls[0] if len(ls) > 0 else None

    def _list_clusters_arn(self):
        rs = self._client.list_clusters()
        ls = [item for item in rs[u'clusterArns']]

        while rs.get(u'nextToken'):
            rs = self._client.list_clusters(nextToken=rs.get(u'nextToken'))
            ls.extend([item for item in rs[u'clusterArns']])
        return ls

    def get_all_clusters(self):
        return [self._describe_cluster(cluster) for cluster in self._list_clusters_arn()]

    def get_single_cluster(self, cluster):
        return self._describe_cluster(cluster)


class EcsCluster(dict):

    def __init__(self, *args, **kwargs):
        super(EcsCluster, self).__init__(*args, **kwargs)
        self._client = boto3.client('ecs')

    @property
    def arn(self):
        return self.get(u'clusterArn')

    @property
    def name(self):
        return self.get(u'clusterName')

    def _list_services_arn(self):
        rs = self._client.list_services(cluster=self.name)
        ls = [arn for arn in rs[u'serviceArns']]

        while rs.get(u'nextToken') is not None:
            rs = self._client.list_services(cluster=self.name, nextToken=rs.get(u'nextToken'))
            ls.extend(arn for arn in rs[u'serviceArns'])
        return ls

    def _describe_service(self, service):
        rs = self._client.describe_services(cluster=self.name, services=[service])
        ls = [EcsService(item) for item in rs[u'services']]
        return ls[0] if len(ls) > 0 else None

    def get_all_services(self):
        return [self._describe_service(service) for service in self._list_services_arn()]

    def get_single_service(self, service):
        return self._describe_service(service)


class EcsService(dict):

    def __init__(self, *args, **kwargs):
        super(EcsService, self).__init__(*args, **kwargs)
        self._client = boto3.client('ecs')

    @property
    def arn(self):
        return self.get(u'serviceArn')

    @property
    def name(self):
        return self.get(u'serviceName')

    @property
    def cluster_arn(self):
        return self.get(u'clusterArn')

    @property
    def desired_count(self):
        return self.get(u'desiredCount')

    @desired_count.setter
    def desired_count(self, value):
        self[u'desiredCount'] = value

    @property
    def running_count(self):
        return self.get(u'runningCount')

    @property
    def task_definition_arn(self):
        return self.get(u'taskDefinition')

    @task_definition_arn.setter
    def task_definition_arn(self, value):
        self[u'taskDefinition'] = value

    def update_service(self):
        rs = self._client.update_service(cluster=self.cluster_arn,
                                         service=self.name,
                                         desiredCount=self.desired_count,
                                         taskDefinition=self.task_definition_arn)

        return EcsService(rs[u'service'])


class EcsTaskDefinition(dict):

    def __init__(self, *args, **kwargs):
        super(EcsTaskDefinition, self).__init__(*args, **kwargs)
        self._client = boto3.client('ecs')

    @staticmethod
    def from_arn(task_arn):
        _client = boto3.client('ecs')
        rs = _client.describe_task_definition(taskDefinition=task_arn)
        return EcsTaskDefinition(rs[u'taskDefinition'])

    @property
    def arn(self):
        return self.get(u'taskDefinitionArn')

    @property
    def family(self):
        return self.get(u'family')

    @property
    def revision(self):
        return self.get(u'revision')

    @property
    def family_revision(self):
        return '%s:%d' % (self.family, self.revision)

    @property
    def containers(self):
        return [EcsContainerDefinition(item) for item in self.get(u'containerDefinitions')]

    def register_as_new_task_definition(self):
        td = self.copy()
        td.pop(u'status', None)
        td.pop(u'requiresAttributes', None)
        td.pop(u'compatibilities', None)
        td.pop(u'taskDefinitionArn', None)
        td.pop(u'revision', None)

        rs = self._client.register_task_definition(**td)
        return EcsTaskDefinition(rs[u'taskDefinition'])


class EcsContainerDefinition(dict):
    def __init__(self, *args, **kwargs):
        super(EcsContainerDefinition, self).__init__(*args, **kwargs)
        self._client = boto3.client('ecs')

    @property
    def name(self):
        return self.get(u'name')

    @name.setter
    def name(self, value):
        self[u'name'] = value

    @property
    def image(self):
        return self.get(u'image')

    @image.setter
    def image(self, value):
        self[u'image'] = value

    @property
    def memory(self):
        return self.get(u'memory')

    @memory.setter
    def memory(self, value):
        self[u'memory'] = value

    @property
    def memory_reservation(self):
        return self.get(u'memoryReservation')

    @property
    def entrypoint(self):
        return self.get(u'entryPoint')

    @entrypoint.setter
    def entrypoint(self, value):
        self[u'entryPoint'] = value

    @property
    def command(self):
        return self.get(u'command')

    @command.setter
    def command(self, value):
        self[u'command'] = value

    @property
    def environment(self):
        return self.get(u'environment')

    @environment.setter
    def environment(self, value):
        self[u'environment'] = value

    @property
    def healthcheck(self):
        return self.get(u'healthCheck')

    @healthcheck.setter
    def healthcheck(self, value):
        self[u'healthCheck'] = value

    # def apply_environments(self):
    #     pattern = re.compile(r"\$\{(.*)\}")
    #     for env in self[u'environment']:
    #         match = re.search(pattern, env[u'value'])
    #         if match:
    #             env[u'value'] = os.getenv(match.group(1))

