import boto3


class EcrClient(object):

    def __init__(self):
        self._client = boto3.client('ecr')

    def _list_repositories(self, repositories):
        rs = self._client.describe_repositories(repositoryNames=repositories)
        ls = [EcrRepository(item) for item in rs[u'repositories']]

        while rs.get(u'nextToken'):
            rs = self._client.describe_repositories(nextToken=rs.get(u'nextToken'))
            ls.extend([EcrRepository(item) for item in rs[u'repositories']])
        return ls

    def get_all_repositories(self):
        return self._list_repositories()

    def get_single_repository(self, repository_arn):
        ls = self._list_repositories([repository_arn])
        return ls[0] if len(ls) > 0 else None


class EcrRepository(dict):

    def __init__(self, *args, **kwargs):
        super(EcrRepository, self).__init__(*args, **kwargs)
        self._client = boto3.client('ecr')

    @property
    def arn(self):
        return self.get(u'repositoryArn')
    
    @property
    def id(self):
        return self.get(u'registryId')

    @property
    def name(self):
        return self.get(u'repositoryName')

    @property
    def created_at(self):
        return self.get(u'createdAt')

    @property
    def images(self):
        rs = self._client.describe_images(repositoryName=self.name)
        ls = [EcrImage(item) for item in rs[u'imageDetails']]

        while rs.get(u'nextToken') is not None:
            rs = self._client.describe_images(nextToken=rs.get(u'nextToken'))
            ls.extend([EcrImage(item) for item in rs[u'imageDetails']])
        return ls


class EcrImage(dict):

    def __init__(self, *args, **kwargs):
        super(EcrImage, self).__init__(*args, **kwargs)
        self._client = boto3.client('ecr')

    @property
    def tags(self):
        return self.get(u'imageTags')

    @property
    def pushed_at(self):
        return self.get(u'imagePushedAt')
