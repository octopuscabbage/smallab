import json
import pickle

import os

from smallab.file_locations import get_experiment_save_directory


def experiment_iterator(name):
    for root, _, files in os.walk(get_experiment_save_directory(name)):
        for fname in files:
            if ".pkl" in fname:
                with open(os.path.join(root, fname), "rb") as f:
                    yield pickle.load(f)
            if ".json" in fname and fname != "specification.json":
                with open(os.path.join(root, fname), "r") as f:
                    yield json.load(f)
