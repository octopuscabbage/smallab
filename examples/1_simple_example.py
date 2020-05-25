#This is an example of a very simple experiment in smallab
# What you need to import from smallab
import logging

import random
import typing

from examples.example_utils import delete_experiments_folder
from smallab.experiment_types.experiment import Experiment


# Write a simple experiment
from smallab.runner.runner import ExperimentRunner


class SimpleExperiment(Experiment):
    # Need to implement this method, will be passed the specification
    # Return a dictionary of results
    def main(self, specification: typing.Dict) -> typing.Dict:
        random.seed(specification["seed"])
        for i in range(specification["num_calls"]):  # Advance the random number generator some amount
            random.random()
        #return the random number. This, along with the specification that generated it will be saved
        return {"number": random.random()}

#The name describes what experiment your doing
name = "simple_experiment1"
#The specifications are a list of dictionaries that will get passed to your experiment instance
specifications = [{"seed":1,"num_calls":1},{"seed":2,"num_calls":2}]
#This object is the code to run your experiment, an instance of the Experiment class
experiment_instance = SimpleExperiment()

#The experiment runner handles cloning your experiment instance and giving it a specification to run with
runner = ExperimentRunner()
runner.run(name,specifications,experiment_instance)

#If I run it again, nothing will happen because smallab knows those experiments succesfully completed
runner.run(name,specifications,experiment_instance)
delete_experiments_folder(name)
