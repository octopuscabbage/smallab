import json
import logging
import shutil

import dill
import os
import types
from copy import deepcopy

from smallab.dashboard.dashboard_events import BeginEvent, CompleteEvent, FailedEvent
from smallab.dashboard.utils import put_in_event_queue, LogToEventQueue
from smallab.experiment_types.experiment import ExperimentBase
from smallab.experiment_types.handlers.registry import run_with_correct_handler
from smallab.file_locations import (get_json_file_location, get_save_file_directory, get_pkl_file_location,
                                    get_specification_file_location, get_log_file, get_experiment_local_storage,
                                    get_specification_local_storage)


def save_run(name, experiment, specification, result, force_pickle):
    os.makedirs(get_save_file_directory(name, specification,experiment), exist_ok=True)
    output_dictionary = {"specification": specification, "result": result}
    json_serialize_was_successful = False
    # Try json serialization
    if not force_pickle:
        json_filename = get_json_file_location(name, specification,experiment)
        try:
            with open(json_filename, "w") as f:
                json.dump(output_dictionary, f)
            json_serialize_was_successful = True
        except Exception:
            logging.getLogger(experiment.get_logger_name()).warning("Json serialization failed with exception",
                                                                    exc_info=True)
            os.remove(json_filename)
    # Try pickle serialization
    if force_pickle or not json_serialize_was_successful:
        pickle_file_location = get_pkl_file_location(name, specification,experiment)
        specification_file_location = get_specification_file_location(name, specification,experiment)
        try:
            with open(pickle_file_location, "wb") as f:
                dill.dump(output_dictionary, f)
            with open(specification_file_location, "w") as f:
                json.dump(specification, f)
        except Exception:
            logging.getLogger(experiment.get_logger_name()).critical("Experiment results serialization failed!!!",
                                                                     exc_info=True)
            try:
                os.remove(pickle_file_location)
            except FileNotFoundError:
                pass
            try:
                os.remove(specification_file_location)
            except FileNotFoundError:
                pass


def run_and_save(name, experiment, specification, propagate_exceptions, callbacks, force_pickle,eventQueue):
    experiment = deepcopy(experiment)
    specification_id = experiment.get_name(specification)
    logger_name = "smallab.{specification_id}".format(specification_id=specification_id)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(get_log_file(experiment, specification_id))
    #formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    fq = LogToEventQueue(eventQueue)
    sh = logging.StreamHandler(fq)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    #TODO need to attach eventqueue logger handler here and not at base logger

    experiment.set_logger_name(logger_name)
    experiment.set_experiment_local_storage(get_experiment_local_storage(name))
    experiment.set_specification_local_storage(get_specification_local_storage(name,specification,experiment))
    put_in_event_queue(eventQueue,BeginEvent(specification_id))

    def _interior_fn():
        result = run_with_correct_handler(experiment, name, specification,eventQueue)
        if isinstance(result, types.GeneratorType):
            for cur_result in result:
                save_run(name, experiment, cur_result["specification"], cur_result["result"], force_pickle)
        else:
            save_run(name, experiment, specification, result, force_pickle)
        for callback in callbacks:
            callback.on_specification_complete(specification, result)
        return None

    if not propagate_exceptions:
        try:
            _interior_fn()

            put_in_event_queue(eventQueue,CompleteEvent(specification_id))
        except Exception as e:
            logging.getLogger(experiment.get_logger_name()).error("Specification Failure", exc_info=True)
            put_in_event_queue(eventQueue,FailedEvent(specification_id))
            on_failure(experiment,specification_id)

            for callback in callbacks:
                callback.on_specification_failure(e, specification)
            return e
    else:
        _interior_fn()
        put_in_event_queue(eventQueue,CompleteEvent(specification_id))
        return None

def on_failure( experiment, specification_identity):
    log_file_location = get_log_file(experiment,specification_identity)
    failed_log_file_location = log_file_location.replace("logs","failed")
    os.makedirs(os.path.dirname(failed_log_file_location),exist_ok=True)
    shutil.copyfile(log_file_location,failed_log_file_location)

