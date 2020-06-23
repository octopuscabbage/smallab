import unittest

import os

from examples.example_utils import delete_experiments_folder
from smallab.runner.runner import ExperimentRunner
from smallab.runner_implementations.fixed_resource.simple import SimpleFixedResourceAllocatorRunner
from smallab.specification_generator import SpecificationGenerator
from smallab.utilities.experiment_loading.experiment_loader import experiment_iterator
from tests.test_overlapping_checkpointed_experiment import SimpleExperiment, SimpleFailExperiment


class TestResourceAllocator(unittest.TestCase):
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
        expr = SimpleExperiment()
        runner.run(name, specifications, expr, specification_runner=SimpleFixedResourceAllocatorRunner([1,2,3]),
                   use_dashboard=True, propagate_exceptions=True,context_type="spawn")
        log_base = os.path.join("experiment_runs",name,"logs")
        for root, dirs, files in  os.walk(log_base):
            for file in files:
                with open(os.path.join(root,file),"r") as f:
                    lines = f.readlines()
                    self.assertNotEqual([],lines)

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
        runner.run(name, specifications, SimpleExperiment(), specification_runner=SimpleFixedResourceAllocatorRunner([1,2,3]),
                   use_dashboard=False, propagate_exceptions=True)
        for result in experiment_iterator(name):
            if result["result"] != []:
                output_specifications.remove(result["specification"])
        self.assertEqual([], output_specifications)
        runner.run(name,specifications,SimpleFailExperiment())

