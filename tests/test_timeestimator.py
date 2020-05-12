import time
import typing
import unittest

from smallab.dashboard.dashboard import TimeEstimator
from smallab.experiment import Experiment
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
