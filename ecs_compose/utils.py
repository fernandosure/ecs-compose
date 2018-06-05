from jsonmerge import Merger
from dictdiffer import diff, PathLimit
from pprint import pprint
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


def get_ecs_service_diff(old_td, new_td):
    image_diff = list(diff(old_td[u'containerDefinitions'][0][u'image'], new_td[u'containerDefinitions'][0][u'image']))
    return image_diff
