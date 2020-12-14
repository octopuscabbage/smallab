import os
import typing

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
                          specification: Specification, diff_namer,extended_keys=False) -> typing.AnyStr:
    """
    Get the filename to save the file under
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The filename to save this run under
    """
    return os.path.join(get_save_file_directory(name, specification, diff_namer,extended_keys=False), "run.pkl")


def get_json_file_location(name, specification, diff_namer,extended_keys=False):
    return os.path.join(get_save_file_directory(name, specification, diff_namer,extended_keys), "run.json")


def get_specification_file_location(name: typing.AnyStr, specification: typing.Dict, diff_namer,extended_keys=False) -> typing.AnyStr:
    """
    Get the specification file location
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The location where the specification.json should be saved
    """
    return os.path.join(get_save_file_directory(name, specification, diff_namer,extended_keys), "specification.json")


def get_save_file_directory(name: typing.AnyStr, specification: Specification, diff_namer,extended_keys=False) -> typing.AnyStr:
    """
    Get the folder to save the .pkl file and specification.json file under
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The location where specification.json should be saved
    """

    if diff_namer is not None:
        if extended_keys:
            expr_name = diff_namer.get_extended_name(specification)
        else:
            expr_name = diff_namer.get_name(specification)
    else:
        expr_name = specification_hash(specification)
    return os.path.join(get_experiment_save_directory(name), expr_name)


def get_partial_save_directory(name, specification, diff_namer):
    if diff_namer is not None:
        specification_name = diff_namer.get_name(specification)
    else:
        specification_name = specification_hash(specification)

    return os.path.join(get_save_directory(name), "checkpoints", specification_name)


def get_log_file(experiment, specification_id):
    return os.path.join(experiment.get_logging_folder(), specification_id + ".log")
