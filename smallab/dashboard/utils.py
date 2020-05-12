from smallab.dashboard.dashboard_events import LogEvent


class FileLikeQueue:
    """A file-like object that writes to a queue"""
    def __init__(self, q):
        self.q = q
    def write(self, t):
        self.q.put(LogEvent(t))
    def flush(self):
        pass