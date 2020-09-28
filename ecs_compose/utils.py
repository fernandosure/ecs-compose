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


def get_ecs_service_diff(old_service, old_td, new_service):

    rs = {}

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

    old_healthcheck =  old_td.containers[0].healthcheck if old_td.containers[0].healthcheck else {}
    new_healthcheck = new_service.healthcheck.to_aws_json() if new_service.healthcheck else {}

    if diff(old_healthcheck, new_healthcheck):
        rs[u"healthcheck"] = {u"old": old_healthcheck, u"new": new_healthcheck}

    old_placement_constraints = old_td.get('placementConstraints', [])
    new_placement_constraints = list(map(lambda item: item.to_aws_json(), new_service.placement_constraints))

    if diff(old_placement_constraints, new_placement_constraints):
        rs[u"PlacementConstraints"] = {u"old": old_placement_constraints, u"new": new_placement_constraints}
    return rs
