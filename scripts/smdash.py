import sys

from smallab.dashboard.dashboard import start_dashboard


if __name__ == "__main__":
    experiment_name = sys.argv[1]
    start_dashboard(experiment_name)