from smallab.dashboard.dashboard_events import LogEvent


class FileLikeQueue:
    """A file-like object that writes to the event queue.
     This is used so that logs will get added to the event queue to be displayed by the dashboard"""

    def __init__(self, q):
        self.q = q

    def write(self, t):
        self.q.put(LogEvent(t))

    def flush(self):
        pass
