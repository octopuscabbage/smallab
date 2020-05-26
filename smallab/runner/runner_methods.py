import json
import logging

import dill
import os
import types
from copy import deepcopy

from smallab.dashboard.dashboard_events import BeginEvent, CompleteEvent, FailedEvent
from smallab.dashboard.utils import put_in_event_queue
from smallab.experiment_types.handlers.registry import run_with_correct_handler
from smallab.file_locations import (get_json_file_location, get_save_file_directory, get_pkl_file_location,
                                    get_specification_file_location, get_log_file)
from smallab.specification_hashing import specification_hash


def save_run(name, experiment, specification, result, force_pickle):
    os.makedirs(get_save_file_directory(name, specification))
    output_dictionary = {"specification": specification, "result": result}
    json_serialize_was_successful = False
    # Try json serialization
    if not force_pickle:
        json_filename = get_json_file_location(name, specification)
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
        pickle_file_location = get_pkl_file_location(name, specification)
        specification_file_location = get_specification_file_location(name, specification)
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


def run_and_save(name, experiment, specification, propagate_exceptions, callbacks, force_pickle):
    experiment = deepcopy(experiment)
    specification_id = specification_hash(specification)
    logger_name = "smallab.{specification_id}".format(specification_id=specification_id)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(get_log_file(experiment, specification_id))
    formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    experiment.set_logger_name(logger_name)
    put_in_event_queue(BeginEvent(specification_id))

    def _interior_fn():
        result = run_with_correct_handler(experiment, name, specification)
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

            put_in_event_queue(CompleteEvent(specification_id))
        except Exception as e:
            logger.error("Specification Failure", exc_info=True)
            put_in_event_queue(FailedEvent(specification_id))
            for callback in callbacks:
                callback.on_specification_failure(e, specification)
            return e
    else:
        _interior_fn()
        put_in_event_queue(CompleteEvent(specification_id))
        return None
