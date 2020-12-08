import logging
from copy import deepcopy

import os
import unittest

from numpy.random.mtrand import RandomState

from examples.example_utils import delete_experiments_folder
from smallab.experiment_types.overlapping_output_experiment import OverlappingOutputCheckpointedExperiment, \
    OverlappingOutputCheckpointedExperimentReturnValue
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.main_process_runner import MainRunner
from smallab.runner_implementations.multiprocessing_runner import MultiprocessingRunner
from smallab.smallab_types import Specification
from smallab.specification_generator import SpecificationGenerator
from smallab.utilities.experiment_loading.experiment_loader import experiment_iterator


class SimpleExperiment(OverlappingOutputCheckpointedExperiment):
    # Initialize will be called once to set up your experiment
    # Each specification will have one instance of your experiment saved with it, so save variables you need to self
    def initialize(self, specification: Specification):
        self.specification = specification
        self.seed = specification['seed']
        self.num_calls = specification["num_calls"]
        logging.getLogger(self.get_logger_name()).info("Doing work!")
        self.rs = RandomState(self.seed)
        self.i = 0

    # Step will be called many times until it does not return None
    def step(self):
        logging.getLogger(self.get_logger_name()).info("Stepping")
        self.i += 1
        self.r = self.rs.random()
        # this experiment can have a random transient failure!
        # Since it's checkpointed, it will likely succeed after running it again
        # if random.randint(0,100) > 90:
        #     raise Exception("Something bad happened, a moth flew into the computer!")
        if self.i in self.num_calls:
            should_continue = self.i != self.num_calls[-1]
            specification = deepcopy(self.specification)
            specification["num_calls"] = self.i
            result = {"r": self.r}
            progress = self.i
            max_iterations = self.num_calls
            return OverlappingOutputCheckpointedExperimentReturnValue(should_continue, specification, result,
                                                                      progress, max_iterations)
        else:
            # This experiment isn't done, return the progress as a tuple to update the dashboard
            return (self.i, self.num_calls)


class SimpleFailExperiment(SimpleExperiment):
    def step(self):
        raise Exception()

class TestOverlappingCheckpointedExperiment(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            os.remove("tmp.pkl")
        except FileNotFoundError:
            pass
        try:
            delete_experiments_folder("test")
        except FileNotFoundError:
            pass

    def testmain(self):

        # Same specification as before
        generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [[10, 20, 30]]}
        specifications = SpecificationGenerator().generate(generation_specification)

        output_generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [10, 20, 30]}
        output_specifications = SpecificationGenerator().generate(output_generation_specification)

        name = "test"
        # This time we will run them all in parallel
        runner = ExperimentRunner()
        runner.run(name, specifications, SimpleExperiment(), specification_runner=MainRunner(),
                   use_dashboard=False, propagate_exceptions=True)
        for result in experiment_iterator(name):
            if result["result"] != []:
                output_specifications.remove(result["specification"])
        self.assertEqual([],output_specifications)
    def test_save_correctly_final_output(self):
        # Same specification as before
        generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [[10, 20, 30]]}
        specifications = SpecificationGenerator().generate(generation_specification)

        output_generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [10, 20, 30]}
        output_specifications = SpecificationGenerator().generate(output_generation_specification)

        name = "test"
        # This time we will run them all in parallel
        runner = ExperimentRunner()
        runner.run(name, specifications, SimpleExperiment(), specification_runner=MultiprocessingRunner(),
                   use_dashboard=False, propagate_exceptions=True)
        for result in experiment_iterator(name):
            print(result)
            if result["result"] != []:
                output_specifications.remove(result["specification"])
        self.assertEqual([], output_specifications)
        runner.run(name,specifications,SimpleFailExperiment())
