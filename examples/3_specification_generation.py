# This demonstrates using the specification generator to save writing each specification out
import logging
import typing

import random

from examples.example_utils import delete_experiments_folder
from smallab.experiment_types.experiment import Experiment
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.multiprocessing_runner import MultiprocessingRunner
from smallab.specification_generator import SpecificationGenerator


# Same experiment as before
class SimpleExperiment(Experiment):
    def main(self, specification: typing.Dict) -> typing.Dict:
        random.seed(specification["seed"])
        for i in range(specification["num_calls"]):
            logging.getLogger(self.get_logger_name()).info("...")
            random.random()
        return {"number": random.random()}


# In the generation specification keys that have lists as their values will be cross producted with other list valued keys to create many specifications
# in this instance there will be 8 * 3 = 24 specifications
generation_specification = {"seed": list(range(100)), "num_calls": [100, 200, 300]}

# Call the generate method. Will create the cross product.
specifications = SpecificationGenerator().generate(generation_specification)
print(specifications)

name = "specification_generation_experiment"
runner = ExperimentRunner()
runner.run(name, specifications, SimpleExperiment(), specification_runner=MultiprocessingRunner(),use_dashboard=False,use_diff_namer=False)

delete_experiments_folder(name)