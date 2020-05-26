
import logging

import random
import typing

from examples.example_utils import delete_experiments_folder
from smallab.experiment_types.experiment import Experiment


#This is another simple experiment, this time with logging involved!
from smallab.runner.runner import ExperimentRunner


class SimpleExperiment(Experiment):
    def main(self, specification: typing.Dict) -> typing.Dict:
        #Get logger name is set per experiment, all logging here will go to a seperate file with the experiment name and go to a main log as well
        logging.getLogger(self.get_logger_name()).info("Doing work!")
        random.seed(specification["seed"])
        for i in range(specification["num_calls"]):  # Advance the random number generator some amount
            random.random()
        return {"number": random.random()}


name = "simple_experiment2"
runner = ExperimentRunner()
runner.run(name,[{"seed":1,"num_calls":1},{"seed":2,"num_calls":2}],SimpleExperiment())

delete_experiments_folder(name)
