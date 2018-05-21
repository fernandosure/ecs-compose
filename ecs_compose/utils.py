from jsonmerge import Merger

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
