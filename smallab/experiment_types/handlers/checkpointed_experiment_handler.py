import datetime
import logging
import time
import typing

import dill
import os
from dateutil.parser import parse

from smallab.dashboard.dashboard_events import ProgressEvent
from smallab.dashboard.utils import put_in_event_queue
from smallab.experiment_types.checkpointed_experiment import CheckpointedExperiment, HasCheckpoint, IterativeExperiment
from smallab.experiment_types.experiment import ExperimentBase, Experiment
from smallab.experiment_types.handlers.base_handler import BaseHandler
from smallab.file_locations import get_partial_save_directory
from smallab.smallab_types import Specification


class CheckpointedExperimentHandler(BaseHandler):
    """
    An internal handler to handle running checkpointed experiments.
    """

    def __init__(self,eventQueue, rolled_backups=3):
        """

        :param rolled_backups: Controls how many backups are kept. Once this limit is reached the oldest is deleted.
        """
        self.eventQueue = eventQueue
        self.rolled_backups = rolled_backups
        self.filtered_delta = None


    def run(self, experiment: CheckpointedExperiment, name: typing.AnyStr, specification: Specification):
        self.last_timer = time.time()
        loaded_experiment = self.load_most_recent(experiment,name, specification)
        if loaded_experiment is None:
            experiment.initialize(specification)
            self._save_checkpoint(experiment, name, specification)
        else:
            experiment = loaded_experiment
        result = experiment.step()
        self.publish_progress(experiment,specification, result)
        while result is None or isinstance(result, tuple):
            self._save_checkpoint(experiment, name, specification)
            result = experiment.step()
            self.publish_progress(experiment,specification, result)
        return result

    def publish_progress(self,experiment, specification, result):
        if isinstance(result, tuple):
            name = experiment.get_name(specification)
            put_in_event_queue(self.eventQueue, ProgressEvent(name, result[0], result[1]))

            cur_time = time.time()
            delta = cur_time - self.last_timer
            #Simple low pass filter
            if self.filtered_delta is None:
                self.filtered_delta = delta
            else:
                self.filtered_delta = self.filtered_delta + .9 * (delta - self.filtered_delta)
            self.last_timer = cur_time
            reamining_iterations = result[1] - result[0]
            remaining_time = reamining_iterations * self.filtered_delta

            logging.getLogger(experiment.get_logger_name()).info(f"Update: {result[0]} / {result[1]} Est {round(remaining_time,2)}s")

    def load_most_recent(self, experiment:ExperimentBase, name, specification):
        specification_id = experiment.get_name(specification)
        location = get_partial_save_directory(name, specification,experiment)
        checkpoints = self._get_time_sorted_checkpoints(name, specification,experiment)
        if checkpoints == []:
            logging.getLogger(experiment.get_logger_name()).info("No checkpoints available")
            return
        # checkpoints = reversed(checkpoints)
        able_to_load_checkpoint = False
        checkpoints = reversed(checkpoints)
        used_checkpoint = None
        for checkpoint in checkpoints:
            try:
                with open(os.path.join(location, str(checkpoint) + ".pkl"), "rb") as f:
                    partial_experiment = dill.load(f)
                    able_to_load_checkpoint = True
                    used_checkpoint = checkpoint
                    break
            except:
                logging.getLogger(experiment.get_logger_name()).warning(
                    "Unable to load checkpoint {chp}".format(chp=checkpoint), exc_info=True)
        if not able_to_load_checkpoint:
            logging.getLogger(experiment.get_logger_name()).warning(
                "All checkpoints corrupt".format(id=specification_id))
            return
        else:
            logging.getLogger(experiment.get_logger_name()).info(
                "Successfully loaded checkpoint {chp}".format(chp=used_checkpoint))
        return partial_experiment

    def _get_time_sorted_checkpoints(self, name, specification,experiment):

        location = get_partial_save_directory(name, specification,experiment)
        try:
            checkpoints = os.listdir(location)
        except FileNotFoundError:
            return []
        checkpoints = sorted(
            list(map(parse, map(lambda x: x.strip(".pkl"), checkpoints))))
        return checkpoints

    def _save_checkpoint(self, save_data, name, specification):
        #assert isinstance(experiment,HasCheckpoint)
        if isinstance(save_data, tuple):
            experiment = save_data[0]
        else:
            experiment = save_data
        assert isinstance(experiment,HasCheckpoint) and isinstance(experiment,IterativeExperiment)


        experiment.set_steps_since_checkpoint(experiment.get_steps_since_checkpiont() + 1)
        if experiment.get_steps_since_checkpiont() >= experiment.steps_before_checkpoint():
            experiment.set_steps_since_checkpoint(0)
            experiment_name = experiment.get_name(specification)
            checkpoint_name = str(datetime.datetime.now())
            try:
                start_checkpoint_time = time.time()
                location = get_partial_save_directory(name, specification,experiment)
                os.makedirs(location, exist_ok=True)
                # TODO make sure a checkpoint with this name doesn't already exist
                with open(os.path.join(location, checkpoint_name + ".pkl"), "wb") as f:
                    dill.dump(save_data, f)
                checkpointing_time = time.time() - start_checkpoint_time
                logging.getLogger(experiment.get_logger_name()).info(
                    "Succesfully checkpointed {chp} in {dt}s".format(chp=checkpoint_name,dt=round(checkpointing_time,2)))
                checkpoints = os.listdir(location)
                if len(checkpoints) > self.rolled_backups:
                    checkpoints = self._get_time_sorted_checkpoints(name, specification,experiment)
                    os.remove(os.path.join(location, str(checkpoints[0]) + ".pkl"))
            except:
                logging.getLogger(experiment.get_logger_name()).warning(
                    "Unsuccesful checkpoint {chp}".format(chp=checkpoint_name),
                    exc_info=True)
