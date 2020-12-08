import time
import typing
import unittest

from smallab.dashboard.dashboard import (TimeEstimator, update_possible_values, fit_encoders,
                                         specification_ids_to_specification)
from smallab.experiment_types.experiment import Experiment
from smallab.smallab_types import Specification

#These tests are kind of flimsy since they rely on time.sleep

class TenSecondExperiment(Experiment):
    def main(self, specification: Specification) -> typing.Dict:
        time.sleep(10)
        return dict()

class TestTimeEstimator(unittest.TestCase):
    def test_expectation_completed_experiment(self):
        sleep_time = 5
        timeestimator = TimeEstimator()
        timeestimator.record_start("test")
        time.sleep(sleep_time)
        timeestimator.record_completion("test")
        e,u,l = timeestimator.compute_time_stats(dict(),["test2"],[])
        self.assertEqual(e,l)
        self.assertEqual(e,u)
        self.assertAlmostEqual(e,sleep_time,places=1)

    def test_expectation_iterated_experiment(self):
        sleep_time = 1
        timeestimator = TimeEstimator()
        timeestimator.record_start("test")
        time.sleep(sleep_time)
        timeestimator.record_iteration("test",1)
        time.sleep(sleep_time)
        timeestimator.record_iteration("test",2)
        time.sleep(sleep_time)
        timeestimator.record_iteration("test",3)
        time.sleep(sleep_time)
        timeestimator.record_completion("test")
        e, u, l = timeestimator.compute_time_stats({"test":(0,1)}, [], [])
        self.assertLessEqual(e, l)
        self.assertGreaterEqual(e, u)
        self.assertAlmostEqual(e, sleep_time, places=1)

    def test_bimodal_experiment(self):

        # Register the specifications' values then create the encoders
        spec1, spec2 = {"what": "nice", "hm": 1}, {"what": "cool", "hm": 2}
        update_possible_values(spec1)
        update_possible_values(spec2)
        fit_encoders()
        specification_ids_to_specification.update({"test1": spec1, "test2": spec2})

        sleep1, sleep2 = .2, .3
        timeestimator = TimeEstimator()

        print("starting 1")
        timeestimator.record_start("test1")
        for i in range(20):
            time.sleep(sleep1)
            timeestimator.record_iteration("test1", i)

        print("starting 2")
        timeestimator.record_start("test2")
        for i in range(20):
            time.sleep(sleep2)
            timeestimator.record_iteration("test2", i)

        e, l, u = timeestimator.compute_time_stats({"test1": (20, 50), "test2": (20, 50)}, ["test2", "test1"], [])
        print(e, l, u)

        print("continuing 1")
        timeestimator.record_start("test1")
        for i in range(20):
            time.sleep(sleep1)
            timeestimator.record_iteration("test1", i + 20)
        timeestimator.record_completion("test1")

        print("continuing 2")
        timeestimator.record_start("test2")
        for i in range(20):
            time.sleep(sleep2)
            timeestimator.record_iteration("test2", i + 20)
        timeestimator.record_completion("test2")

        e, l, u = timeestimator.compute_time_stats({"test1": (40, 50), "test2": (40, 50)}, ["test2", "test1"], [])
        print(e, l, u)
