import unittest
from ecs_compose.stack_definition import StackDefinition
from ecs_compose.utils import get_ecs_service_diff
from ecs_compose.ecs import EcsService,EcsTaskDefinition
import yaml
import os


class UtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        self.json_stack = yaml.load(open(self.fixtures_dir + "/base.yml"))
        self.sd = StackDefinition(self.json_stack)

    def test_there_should_not_be_difference_in_task_definitions(self):
        new_svc = next((x for x in self.sd.services if x.name == "service_A"), None)

        old_svc = EcsService({
            'serviceName': 'service_A',
            'desiredCount': 1,
        })

        old_td = EcsTaskDefinition({
                'containerDefinitions': [
                    {
                        'name': 'service_A',
                        'image': 'xxx/service_A:latest',
                        'environment': [
                            {'name': 'PORT', 'value': '8888'},
                            {'name': 'JAVA_OPTS', 'value': '-Duser.timezone="UTC" -Xms256m -Xmx322m -XX:MetaspaceSize=64m -XX:MaxMetaspaceSize=135m -XX:CompressedClassSpaceSize=16m -XX:ReservedCodeCacheSize=50m'},
                            {'name': 'SPRING_PROFILES_ACTIVE', 'value': 'dev,ecs,standalone'},
                            {'name': 'LOGGING_LEVEL_ROOT', 'value': 'INFO'},
                        ],
                        'healthCheck': {
                            'command': ['CMD-SHELL', 'sh healthcheck.sh'],
                            'interval': 30,
                            'timeout': 5,
                            'retries': 3,
                            'startPeriod': 60
                        }
                    }
                ]
            })

        rs = get_ecs_service_diff(old_svc, old_td, new_svc)
        self.assertEqual(len(rs), 0)

    def test_service_b_should_have_difference_in_healthcheck(self):
        new_svc = next((x for x in self.sd.services if x.name == "service_B"), None)

        old_svc = EcsService({
            'serviceName': 'service_B',
            'desiredCount': 1,
        })

        old_td = EcsTaskDefinition({
            'containerDefinitions': [
                {
                    'name': 'service_B',
                    'image': 'xxx/service_B:100',
                    'environment': [
                        {'name': 'PORT', 'value': '8761'},
                        {'name': 'JAVA_OPTS',
                         'value': '-Duser.timezone="UTC" -Xms256m -Xmx322m -XX:MetaspaceSize=64m -XX:MaxMetaspaceSize=135m -XX:CompressedClassSpaceSize=16m -XX:ReservedCodeCacheSize=50m'},
                        {'name': 'SPRING_PROFILES_ACTIVE', 'value': 'ecs'},
                        {'name': 'LOGGING_LEVEL_ROOT', 'value': 'INFO'},
                    ],
                    'healthCheck': {
                        'command': ['CMD-SHELL', 'sh healthcheck.sh'],
                        'interval': 30,
                        'timeout': 5,
                        'retries': 3,
                        'startPeriod': 60
                    }
                }
            ]
        })

        rs = get_ecs_service_diff(old_svc, old_td, new_svc)
        self.assertTrue(rs.get(u'healthcheck'))

    def test_service_b_should_not_have_difference_in_healthcheck(self):
        new_svc = next((x for x in self.sd.services if x.name == "service_B"), None)

        old_svc = EcsService({
            'serviceName': 'service_B',
            'desiredCount': 1,
        })

        old_td = EcsTaskDefinition({
            'containerDefinitions': [
                {
                    'name': 'service_B',
                    'image': 'xxx/service_B:100',
                    'environment': [
                        {'name': 'PORT', 'value': '8761'},
                        {'name': 'JAVA_OPTS',
                         'value': '-Duser.timezone="UTC" -Xms256m -Xmx322m -XX:MetaspaceSize=64m -XX:MaxMetaspaceSize=135m -XX:CompressedClassSpaceSize=16m -XX:ReservedCodeCacheSize=50m'},
                        {'name': 'SPRING_PROFILES_ACTIVE', 'value': 'ecs'},
                        {'name': 'LOGGING_LEVEL_ROOT', 'value': 'INFO'},
                    ]
                }
            ]
        })

        rs = get_ecs_service_diff(old_svc, old_td, new_svc)
        self.assertIsNone(rs.get(u'healthcheck'))
