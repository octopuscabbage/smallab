import os

import shutil

from smallab.file_locations import experiment_folder


def delete_experiments_folder(name):
    shutil.rmtree(os.path.join(experiment_folder, name))