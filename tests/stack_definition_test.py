import unittest
from ecs_compose.stack_definition import StackDefinition
import yaml
import os


class StackDefinitionTestCase(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        self.json_stack = yaml.load(open(self.fixtures_dir + "/base.yml"))
        self.sd = StackDefinition(self.json_stack)

    def test_should_load_yml(self):
        self.assertIsNotNone(self.sd)

    def test_should_have_three_services(self):
        self.assertEqual(len(self.sd.services), 4)

    def test_should_have_vpc_section(self):
        self.assertIsNotNone(self.sd.vpc)

    def test_nginx_should_exist(self):
        self.assertIsNotNone(next((x for x in self.sd.services if x.name == "nginx"), None))

    def test_healthcheck_should_exist_in_service_A(self):
        svc = next((x for x in self.sd.services if x.name == "service_A"), None)
        self.assertEqual(svc.healthcheck.to_aws_json().get('command'), ['CMD-SHELL', 'sh healthcheck.sh'])
        self.assertEqual(svc.healthcheck.to_aws_json().get('startPeriod'), 60)

    def test_task_definition_healthcheck_should_exist_in_service_A(self):
        svc = next((x for x in self.sd.services if x.name == "service_A"), None)
        td = svc.get_task_definition("test")
        self.assertTrue(td.containers[0].get("healthCheck") is not None)

    def test_task_definition_healthcheck_should_not_exists_in_service_B(self):
        svc = next((x for x in self.sd.services if x.name == "service_B"), None)
        td = svc.get_task_definition("test")
        self.assertTrue(td.containers[0].get("healthCheck") is None)

    def test_task_definition_gpus_should_exists_in_deeplearning_service(self):
        svc = next((x for x in self.sd.services if x.name == "deeplearning"), None)
        td = svc.get_task_definition("test")
        self.assertTrue(td.containers[0].get("resourceRequirements") is not None)

    def test_task_definition_gpus_should_not_exists_in_Service_A(self):
        svc = next((x for x in self.sd.services if x.name == "service_A"), None)
        td = svc.get_task_definition("test")
        self.assertTrue(td.containers[0].get("resourceRequirements") is None)