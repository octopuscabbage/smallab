import json

def dict2name(dictionary):
    return '_'.join(['{0}-{1}'.format(k, v) for k, v in dictionary.items()])


def hash_dict(dictionary):
    return str(hash(json.dumps(dictionary)))

