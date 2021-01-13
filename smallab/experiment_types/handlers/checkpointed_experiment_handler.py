import datetime
import logging
import typing

import dill
import os
from dateutil.parser import parse

from smallab.dashboard.dashboard_events import ProgressEvent
from smallab.dashboard.utils import put_in_event_queue
from smallab.experiment_types.checkpointed_experiment import CheckpointedExperiment, HasCheckpoint
from smallab.experiment_types.experiment import ExperimentBase
from smallab.experiment_types.handlers.base_handler import BaseHandler
from smallab.file_locations import get_partial_save_directory
from smallab.smallab_types import Specification
from smallab.specification_hashing import specification_hash


class CheckpointedExperimentHandler(BaseHandler):
    """
    An internal handler to handle running checkpointed experiments.
    """

    def __init__(self,eventQueue, diff_namer, rolled_backups=3):
        """

        :param rolled_backups: Controls how many backups are kept. Once this limit is reached the oldest is deleted.
        """
        self.eventQueue = eventQueue
        self.rolled_backups = rolled_backups
        self.diff_namer = diff_namer

    def run(self, experiment: CheckpointedExperiment, name: typing.AnyStr, specification: Specification):
        loaded_experiment = self.load_most_recent(name, specification)
        if loaded_experiment is None:
            experiment.initialize(specification)
            self._save_checkpoint(experiment, name, specification)
        else:
            experiment = loaded_experiment
        result = experiment.step()
        self.publish_progress(specification, result)
        while result is None or isinstance(result, tuple):
            self._save_checkpoint(experiment, name, specification)
            result = experiment.step()
            self.publish_progress(specification, result)
        return result

    def publish_progress(self, specification, result):
        if isinstance(result, tuple):
            if self.diff_namer is not None:
                name = self.diff_namer.get_name(specification)
            else:
                name = specification_hash(specification)
            put_in_event_queue(self.eventQueue, ProgressEvent(name, result[0], result[1]))


    def load_most_recent(self, name, specification):
        if self.diff_namer is not None:
            specification_id = self.diff_namer.get_name(specification)
        else:
            specification_id = specification_hash(specification)
        location = get_partial_save_directory(name, specification, self.diff_namer)
        checkpoints = self._get_time_sorted_checkpoints(name, specification)
        if checkpoints == []:
            logging.getLogger("smallab.{id}.checkpoint".format(id=specification_id)).info("No checkpoints available")
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
                logging.getLogger("smallab.{id}.checkpoint".format(id=specification_id)).warning(
                    "Unable to load checkpoint {chp}".format(chp=checkpoint), exc_info=True)
        if not able_to_load_checkpoint:
            logging.getLogger("smallab.{id}.checkpoint".format(id=specification_id)).warning(
                "All checkpoints corrupt".format(id=specification_id))
            return
        else:
            logging.getLogger("smallab.{id}.checkpoint".format(id=specification_id)).info(
                "Successfully loaded checkpoint {chp}".format(chp=used_checkpoint))
        return partial_experiment

    def _get_time_sorted_checkpoints(self, name, specification):

        location = get_partial_save_directory(name, specification,self.diff_namer)
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
        assert isinstance(experiment,HasCheckpoint)

        experiment.set_steps_since_checkpoint(experiment.get_steps_since_checkpiont() + 1)
        if experiment.get_steps_since_checkpiont() >= experiment.steps_before_checkpoint():
            experiment.set_steps_since_checkpoint(0)
            if self.diff_namer is not None:
                experiment_hash = self.diff_namer.get_name(specification)
            else:
                experiment_hash = specification_hash(specification)
            checkpoint_name = str(datetime.datetime.now())
            try:
                location = get_partial_save_directory(name, specification,self.diff_namer)
                os.makedirs(location, exist_ok=True)
                # TODO make sure a checkpoint with this name doesn't already exist
                with open(os.path.join(location, checkpoint_name + ".pkl"), "wb") as f:
                    dill.dump(save_data, f)
                logging.getLogger("smallab.{id}.checkpoint".format(id=experiment_hash)).info(
                    "Succesfully checkpointed {chp}".format(chp=checkpoint_name))
                checkpoints = os.listdir(location)
                if len(checkpoints) > self.rolled_backups:
                    checkpoints = self._get_time_sorted_checkpoints(name, specification)
                    os.remove(os.path.join(location, str(checkpoints[0]) + ".pkl"))
            except:
                logging.getLogger("smallab.{id}.checkpoint".format(id=experiment_hash)).warning(
                    "Unsuccesful checkpoint {chp}".format(chp=checkpoint_name),
                    exc_info=True)
