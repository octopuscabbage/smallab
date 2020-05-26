#Subclassing experiment is the simplest way to implement your experiment but is not fault tolerant
#Subclassing CheckpointedExperiment allows your experiment to fail (or the running machine to lose power) and resume at a later point
#Note: Checkpointing does have some overhead so if the experiment is very fast consider not using this
import logging
import time
import typing

import random
from numpy.random.mtrand import RandomState

from smallab.experiment_types.checkpointed_experiment import CheckpointedExperiment
from smallab.experiment_types.experiment import Experiment
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.multiprocessing_runner import MultiprocessingRunner
from smallab.smallab_types import Specification
from smallab.specification_generator import SpecificationGenerator
from examples.example_utils import delete_experiments_folder


#Similar experiment as before but now it will sleep for a bit, taking longer to complete in serial
class SimpleExperiment(CheckpointedExperiment):
    #Initialize will be called once to set up your experiment
    #Each specification will have one instance of your experiment saved with it, so save variables you need to self
    def initialize(self, specification: Specification):
        self.seed = specification['seed']
        self.num_calls = specification["num_calls"]
        logging.getLogger(self.get_logger_name()).info("Doing work!")
        self.rs = RandomState(self.seed)
        self.i = 0

    #Step will be called many times until it does not return None
    def step(self):
        logging.getLogger(self.get_logger_name()).info("Stepping")
        self.i += 1
        if self.i < self.num_calls:
            self.r = self.rs.random()
            time.sleep(10 * self.r)
        #this experiment can have a random transient failure!
        #Since it's checkpointed, it will likely succeed after running it again
        if random.randint(0,100) > 90:
            raise Exception("Something bad happened, a moth flew into the computer!")
        if self.i >= self.num_calls:
            #Done with the experiment, return the results dictionary like normal
            return {"number": self.r}
        else:
            #This experiment isn't done, return the progress as a tuple to update the dashboard
            return (self.i, self.num_calls)


#Same specification as before
generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [1, 2, 3]}
specifications = SpecificationGenerator().generate(generation_specification)

name = "checkpointed_run"
#This time we will run them all in parallel
runner = ExperimentRunner()
runner.run(name, specifications, SimpleExperiment(),specification_runner=MultiprocessingRunner())

#Some of our experiments may have failed, let's call run again to hopefully solve that
runner.run(name, specifications, SimpleExperiment(),specification_runner=MultiprocessingRunner())

#Cleanup example
delete_experiments_folder(name)