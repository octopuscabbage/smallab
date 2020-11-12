import json
import logging

import dill
import enum
import os
import types
from copy import deepcopy
from sqlitedict import SqliteDict

from smallab.dashboard.dashboard_events import BeginEvent, CompleteEvent, FailedEvent
from smallab.dashboard.utils import put_in_event_queue, LogToEventQueue
from smallab.experiment_types.handlers.registry import run_with_correct_handler
from smallab.file_locations import (get_json_file_location, get_save_file_directory, get_pkl_file_location,
                                    get_specification_file_location, get_log_file, get_sqlite_file_location)
from smallab.specification_hashing import specification_hash


class SerializationMethod(enum.Enum):
    JSON = "json",
    SQLITE = "sqlite",
    PICKLE = 'pickle'


def save_json(name, specification, diff_namer, extended_keys, output_dictionary, experiment):
    json_filename = get_json_file_location(name, specification, diff_namer, extended_keys)
    try:
        with open(json_filename, "w") as f:
            json.dump(output_dictionary, f)
        return True
    except Exception:
        logging.getLogger(experiment.get_logger_name()).warning("Json serialization failed with exception",
                                                                exc_info=True)
        os.remove(json_filename)
    return False


def save_sqlite(name, specification, diff_namer, extended_keys, output_dictionary, experiment):
    if diff_namer is not None:
        if extended_keys:
            expr_name = diff_namer.get_extended_name(specification)
        else:
            expr_name = diff_namer.get_name(specification)
    else:
        expr_name = specification_hash(specification)
    try:
        with SqliteDict(get_sqlite_file_location(name), encode=json.dumps, decode=json.loads, autocommit=True) as db:
            db[expr_name] = output_dictionary
    except Exception:
        logging.getLogger(experiment.get_logger_name()).warning("Sqlite serialization failed with exception",
                                                                exc_info=True)


def save_pickle(name, specification, diff_namer, extended_keys, output_dictionary, experiment):
    pickle_file_location = get_pkl_file_location(name, specification, diff_namer, extended_keys)
    specification_file_location = get_specification_file_location(name, specification, diff_namer, extended_keys)
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


def save_run(name, experiment, specification, result, diff_namer, extended_keys=False,
             serialization_method=SerializationMethod.PICKLE):
    os.makedirs(get_save_file_directory(name, specification, diff_namer, extended_keys), exist_ok=True)
    output_dictionary = {"specification": specification, "result": result}
    serialize_was_successful = False
    # Try json serialization
    if serialization_method == SerializationMethod.JSON:
        serialize_was_successful = save_json(name, specification, diff_namer, extended_keys, output_dictionary,
                                             experiment)
    if serialization_method == SerializationMethod.SQLITE:
        serialize_was_successful = save_sqlite(name, specification, diff_namer, extended_keys, output_dictionary,
                                               experiment)
    if SerializationMethod.PICKLE or not serialize_was_successful:
        save_pickle(name, specification, diff_namer, extended_keys, output_dictionary, experiment)


def run_and_save(name, experiment, specification, propagate_exceptions, callbacks, serialization_method, eventQueue,
                 diff_namer):
    experiment = deepcopy(experiment)
    if diff_namer is None:
        specification_id = specification_hash(specification)
    else:
        specification_id = diff_namer.get_name(specification)
    logger_name = "smallab.{specification_id}".format(specification_id=specification_id)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(get_log_file(experiment, specification_id))
    # formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    fq = LogToEventQueue(eventQueue)
    sh = logging.StreamHandler(fq)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    # TODO need to attach eventqueue logger handler here and not at base logger

    experiment.set_logger_name(logger_name)
    put_in_event_queue(eventQueue, BeginEvent(specification_id))

    def _interior_fn():
        result = run_with_correct_handler(experiment, name, specification, eventQueue, diff_namer=diff_namer)
        if isinstance(result, types.GeneratorType):
            for cur_result in result:
                diff_namer.extend_name(cur_result["specification"])
                save_run(name, experiment, cur_result["specification"], cur_result["result"],
                         diff_namer=diff_namer, extended_keys=True, serialization_method=serialization_method)
        else:
            save_run(name, experiment, specification, result, serialization_method=serialization_method, diff_namer=diff_namer)
        for callback in callbacks:
            callback.on_specification_complete(specification, result)
        return None

    if not propagate_exceptions:
        try:
            _interior_fn()

            put_in_event_queue(eventQueue, CompleteEvent(specification_id))
        except Exception as e:
            logger.error("Specification Failure", exc_info=True)
            put_in_event_queue(eventQueue, FailedEvent(specification_id))
            for callback in callbacks:
                callback.on_specification_failure(e, specification)
            return e
    else:
        _interior_fn()
        put_in_event_queue(eventQueue, CompleteEvent(specification_id))
        return None
