import typing

import os

from smallab.smallab_types import Specification
from smallab.specification_hashing import specification_hash

experiment_folder = "experiment_runs"


def get_save_directory(name: typing.AnyStr) -> typing.AnyStr:
    """
    Get the directory that the runs will be saved under
    :param name: The name of the current batch
    :return: The folder to save the runs under
    """
    return os.path.join(experiment_folder, name)


def get_experiment_save_directory(name):
    return os.path.join(get_save_directory(name), "experiments")


def get_pkl_file_location(name: typing.AnyStr,
                          specification: Specification) -> typing.AnyStr:
    """
    Get the filename to save the file under
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The filename to save this run under
    """
    return os.path.join(get_save_file_directory(name, specification), "run.pkl")


def get_json_file_location(name, specification):
    return os.path.join(get_save_file_directory(name, specification), "run.json")


def get_specification_file_location(name: typing.AnyStr, specification: typing.Dict) -> typing.AnyStr:
    """
    Get the specification file location
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The location where the specification.json should be saved
    """
    return os.path.join(get_save_file_directory(name, specification), "specification.json")


def get_save_file_directory(name: typing.AnyStr, specification: Specification) -> typing.AnyStr:
    """
    Get the folder to save the .pkl file and specification.json file under
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The location where specification.json should be saved
    """
    return os.path.join(get_experiment_save_directory(name), specification_hash(specification))


def get_partial_save_directory(name, specification):
    return os.path.join(get_save_directory(name), "checkpoints", specification_hash(specification))


def get_log_file(experiment, specification_id):
    return os.path.join(experiment.get_logging_folder(), specification_id + ".log")
