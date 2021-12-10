# Similar experiment as before but now it will sleep for a bit, taking longer to complete in serial
import logging
import time

from copy import deepcopy
from numpy.random.mtrand import RandomState

from examples.example_utils import delete_experiments_folder
from smallab.experiment_types.overlapping_output_experiment import OverlappingOutputCheckpointedExperiment, \
    OverlappingOutputCheckpointedExperimentReturnValue
from smallab.name_helper.dict import dict2name
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.multiprocessing_runner import MultiprocessingRunner
from smallab.smallab_types import Specification
from smallab.specification_generator import SpecificationGenerator


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
        time.sleep(1)
        # this experiment can have a random transient failure!
        # Since it's checkpointed, it will likely succeed after running it again
        # if random.randint(0,100) > 90:
        #     raise Exception("Something bad happened, a moth flew into the computer!")
        should_continue = self.i != self.num_calls
        specification = deepcopy(self.specification)
        specification["num_calls"] = self.i
        result = {"r": self.r}
        progress = self.i
        max_iterations = self.num_calls
        return OverlappingOutputCheckpointedExperimentReturnValue(should_continue, specification, result, progress,
                                                                  max_iterations)
    #Tells the dashboard how many iterations this experiment will run for
    def max_iterations(self,specification):
        return specification["num_calls"]

    def get_name(self,specification):
        return dict2name(specification)
    def get_current_name(self,specification):
        cur_specification = deepcopy(specification)
        cur_specification["idx"] = self.i
        return dict2name(cur_specification)

# Same specification as before
generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": 30}
specifications = SpecificationGenerator().generate(generation_specification)

name = "overlapping_checkpointed_run"
# This time we will run them all in parallel
runner = ExperimentRunner()
runner.run(name, specifications, SimpleExperiment(), specification_runner=MultiprocessingRunner(), use_dashboard=True,
           propagate_exceptions=True)

# Some of our experiments may have failed, let's call run again to hopefully solve that
runner.run(name, specifications, SimpleExperiment(), specification_runner=MultiprocessingRunner(), use_dashboard=True,
           propagate_exceptions=True)

# Cleanup example
delete_experiments_folder(name)
