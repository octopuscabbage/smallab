#By defaualt, smallab will run your experiments in joblib using threads
#This can be a bit slower than using multiprocessing
import logging
import time
import typing

import random

from smallab.experiment_types.experiment import Experiment
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.multiprocessing_runner import MultiprocessingRunner
from smallab.specification_generator import SpecificationGenerator
from examples.example_utils import delete_experiments_folder


#Similar experiment as before but now it will sleep for a bit, taking longer to complete in serial
class SimpleExperiment(Experiment):
    def main(self, specification: typing.Dict) -> typing.Dict:
        logging.getLogger(self.get_logger_name()).info("Doing work!")
        random.seed(specification["seed"])
        for i in range(specification["num_calls"]):
            r = random.random()
        time.sleep(10 * r)
        return {"number": r}


#Same specification as before
generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [1, 2, 3]}
specifications = SpecificationGenerator().generate(generation_specification)

name = "multiprocessing_runner"
#This time we will run them all in parallel
runner = ExperimentRunner()
runner.run(name, specifications, SimpleExperiment(),specification_runner=MultiprocessingRunner())

#Cleanup example
delete_experiments_folder(name)
