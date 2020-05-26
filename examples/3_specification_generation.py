# This demonstrates using the specification generator to save writing each specification out
import typing

import random

from examples.example_utils import delete_experiments_folder
from smallab.experiment_types.experiment import Experiment
from smallab.runner.runner import ExperimentRunner
from smallab.specification_generator import SpecificationGenerator


# Same experiment as before
class SimpleExperiment(Experiment):
    def main(self, specification: typing.Dict) -> typing.Dict:
        random.seed(specification["seed"])
        for i in range(specification["num_calls"]):
            random.random()
        return {"number": random.random()}


# In the generation specification keys that have lists as their values will be cross producted with other list valued keys to create many specifications
# in this instance there will be 8 * 3 = 24 specifications
generation_specification = {"seed": [1, 2, 3, 4, 5, 6, 7, 8], "num_calls": [1, 2, 3]}

# Call the generate method. Will create the cross product.
specifications = SpecificationGenerator().generate(generation_specification)
print(specifications)

name = "specification_generation_experiment"
runner = ExperimentRunner()
runner.run(name, specifications, SimpleExperiment())

delete_experiments_folder(name)