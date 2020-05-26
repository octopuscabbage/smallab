class LogEvent():
    def __init__(self, message):
        self.message = message


class BeginEvent():
    def __init__(self, specification_id):
        self.specification_id = specification_id


class ProgressEvent():
    def __init__(self, specification_id, progress, max):
        self.specification_id = specification_id
        self.progress = progress
        self.max = max


class CompleteEvent():
    def __init__(self, specification_id):
        self.specification_id = specification_id


class StartExperimentEvent():
    def __init__(self, name):
        self.name = name


class RegisterEvent():
    def __init__(self, specification_id, specification):
        self.specification_id = specification_id
        self.specification = specification


class FailedEvent():
    def __init__(self, specification_id):
        self.specification_id = specification_id
