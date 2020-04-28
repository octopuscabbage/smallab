import json

import hashlib
import humanhash


def specification_hash(specification):
    return humanhash.humanize(hashlib.md5(json.dumps(specification, sort_keys=True).encode("utf-8")).hexdigest())
