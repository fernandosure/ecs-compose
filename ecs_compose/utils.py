from jsonmerge import Merger
from jsondiff import diff
from ecs import EcsTaskDefinition

schema = {
    "properties": {
        "services": {
            "mergeStrategy": "append"
        },
        "logging": {
            "mergeStrategy": "overwrite"
        }
    }
}
merger = Merger(schema)


def get_ecs_service_diff(old_service, new_service):

    rs = {}

    old_td = EcsTaskDefinition.from_arn(old_service.task_definition_arn)

    # Get image differences
    old_image = old_td.containers[0].image
    new_image = new_service.image
    if old_image != new_image:
        rs[u"image"] = {u"old": old_image, u"new": new_image}

    # get Desired Count Diffs
    old_desired_count = old_service.desired_count
    new_desired_count = new_service.desired_count
    if old_desired_count != new_desired_count:
        rs[u"desired_count"] = {u"old": old_desired_count, u"new": new_desired_count}

    old_td_env = sorted(old_td.containers[0].environment, key=lambda o: o[u'name'])
    new_td_env = sorted(new_service.environment, key=lambda n: n[u'name'])

    if diff(old_td_env, new_td_env):
        rs[u"environment"] = {u"old": old_td_env, u"new": new_td_env}

    return rs

