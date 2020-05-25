import dill
import typing
import unittest

import numpy as np
import os

from smallab.experiment_types.handlers.checkpointed_experiment_handler import CheckpointedExperimentHandler
from smallab.experiment_types.checkpointed_experiment import CheckpointedExperiment
from smallab.file_locations import get_save_file_directory, get_partial_save_directory
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.main_process_runner import MainRunner
from smallab.smallab_types import Specification
from tests.utils import delete_experiments_folder


class SerializableExperiment(CheckpointedExperiment):
    def initialize(self, specification: Specification):
        self.j = 0

    def step(self) -> typing.Optional[typing.Dict]:
        self.j += 1
        if self.j == 2:
            return dict()
        else:
            return None


class ReturnBadExperiment(CheckpointedExperiment):
    def initialize(self, specification: Specification):
        self.j = 0
        self.bad = []

    def step(self):
        self.j += 1
        if self.j == 10:
            return {"x": self.bad}
        else:
            return None


class PickleOnlySerializableExeperiment(ReturnBadExperiment):
    def initialize(self, specification: Specification):
        self.bad = np.array([1, 2, 3])
        self.j = 0

def generator():
    i = 0
    while True:
        i+=1
        yield i

class UnserializableExperiment(ReturnBadExperiment):
    def initialize(self, specification: Specification):
        self.bad = generator()
        self.j = 0


class SerializableExperimentFailsAfter4Steps(CheckpointedExperiment):
    def initialize(self, specification: Specification):
        self.j = 0

    def step(self):
        self.j += 1
        if self.j == 4:
            self.j += 1
            raise Exception()
        elif self.j == 10:
            return dict
        else:
            return None


class TestInProgressSerialization(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            os.remove("tmp.pkl")
        except FileNotFoundError:
            pass
        try:
            delete_experiments_folder("test")
        except FileNotFoundError:
            pass

    def test_serialize_generator_experiment(self):
        experiment = SerializableExperiment()
        experiment.initialize(None)
        experiment.step()
        with open("tmp.pkl", "wb") as f:
            dill.dump(experiment, f)
        del experiment
        with open("tmp.pkl", "rb") as f:
            loaded_experiment = dill.load(f)
        self.assertEqual(loaded_experiment.step(), dict())

    def test_with_runner(self):
        experiment = SerializableExperiment()
        runner = ExperimentRunner()
        specification = {"test": "test"}
        runner.run("test", [specification], experiment, specification_runner=MainRunner())
        self.assertEqual(1, len(os.listdir(get_save_file_directory('test', specification))))

    def test_checkpoint_handler_rotates_checkpoints_properly(self):
        experiment = SerializableExperimentFailsAfter4Steps()
        runner = ExperimentRunner()
        specification = {"test": "test"}
        runner.run("test", [specification], experiment, specification_runner=MainRunner())
        self.assertEqual(3, len(os.listdir(get_partial_save_directory("test", specification))))
        partial_experiment = CheckpointedExperimentHandler().load_most_recent("test", specification)
        self.assertEqual(partial_experiment.j, 3)

    def test_un_serializable_experiment_failure(self):
        experiment = UnserializableExperiment()
        runner = ExperimentRunner()
        specification = {"test": "test"}
        runner.run("test", [specification], experiment, specification_runner=MainRunner())
        self.assertEqual(0, len(os.listdir(get_save_file_directory('test', specification))))

    def test_pickle_serializable_experiment_success(self):
        experiment = PickleOnlySerializableExeperiment()
        runner = ExperimentRunner()
        specification = {"test": "test"}
        runner.run("test", [specification], experiment, specification_runner=MainRunner())
        self.assertIn("run.pkl", os.listdir(get_save_file_directory('test', specification)))
        self.assertIn("specification.json", os.listdir(get_save_file_directory('test', specification)))
