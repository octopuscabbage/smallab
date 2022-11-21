import os
import typing

from smallab.experiment_types.checkpointed_experiment import IterativeExperiment
from smallab.experiment_types.experiment import ExperimentBase
from smallab.smallab_types import Specification

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
                          specification: Specification,experiment) -> typing.AnyStr:
    """
    Get the filename to save the file under
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The filename to save this run under
    """
    return os.path.join(get_save_file_directory(name, specification, experiment), "run.pkl")


def get_json_file_location(name, specification,experiment):
    return os.path.join(get_save_file_directory(name, specification, experiment), "run.json")


def get_specification_file_location(name: typing.AnyStr, specification: typing.Dict,experiment) -> typing.AnyStr:
    """
    Get the specification file location
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The location where the specification.json should be saved
    """
    return os.path.join(get_save_file_directory(name, specification, experiment), "specification.json")

def resolve_current_experiment_name(experiment:ExperimentBase, specification: Specification):
    if isinstance(experiment, IterativeExperiment):
        return experiment.get_current_name(specification)
    else:
        return experiment.get_name(specification)

def get_save_file_directory(name: typing.AnyStr, specification: Specification, experiment :ExperimentBase) -> typing.AnyStr:
    """
    Get the folder to save the .pkl file and specification.json file under
    :param name: The name of the current batch
    :param specification: The specification of the current run
    :return: The location where specification.json should be saved
    """
    dir = os.path.join(get_experiment_save_directory(name),resolve_current_experiment_name(experiment,specification))
    return dir


def get_partial_save_directory(name, specification, experiment:ExperimentBase):
    expr_name = experiment.get_name(specification)
    return os.path.join(get_save_directory(name), "checkpoints", expr_name)


def get_log_file(experiment, specification_id):
    return os.path.join(experiment.get_logging_folder(), specification_id + ".log")


def get_experiment_local_storage(name):
    return os.path.join(get_save_directory(name),"tmp")


def get_specification_local_storage(name, specification, experiment: ExperimentBase):
    expr_name = experiment.get_name(specification)
    return os.path.join(get_experiment_local_storage(name),expr_name)

def get_dashboard_file(name):
    return os.path.join(get_save_directory(name), ".dashboard.csv")

def get_specification_save_dir(name):
    return os.path.join(get_save_directory(name), "specifications")