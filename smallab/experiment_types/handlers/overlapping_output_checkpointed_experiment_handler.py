import logging
import time
import typing

from smallab.experiment_types.handlers.base_handler import BaseHandler
from smallab.experiment_types.handlers.checkpointed_experiment_handler import CheckpointedExperimentHandler
from smallab.experiment_types.overlapping_output_experiment import (OverlappingOutputCheckpointedExperiment,
                                                                    OverlappingOutputCheckpointedExperimentReturnValue)
from smallab.smallab_types import Specification



class OverlappingOutputCheckpointedExperimentHandler(BaseHandler):
    def __init__(self,eventQueue):
        self.checkpointed_experiment_handler = CheckpointedExperimentHandler(eventQueue)

    def run(self, experiment: OverlappingOutputCheckpointedExperiment, name: typing.AnyStr,
            specification: Specification):
        loaded_value = self.checkpointed_experiment_handler.load_most_recent(experiment,name, specification)
        if loaded_value is None:
            experiment.initialize(specification)
            results_list = []
            self.checkpointed_experiment_handler._save_checkpoint((experiment, results_list), name, specification)
        else:
            experiment = loaded_value[0]
            results_list = loaded_value[1]
        self.checkpointed_experiment_handler.last_timer = time.time()
        result = experiment.step()
        if isinstance(result, OverlappingOutputCheckpointedExperimentReturnValue):
            self.checkpointed_experiment_handler.publish_progress(experiment,specification,
                                                                  (result.progress, result.max_iterations))
            if result.should_serialize:
                yield {'specification': result.specification, 'result': result.return_value}
        else:
            self.checkpointed_experiment_handler.publish_progress(experiment,specification, result)

        self.checkpointed_experiment_handler.publish_progress(experiment,specification, result)
        while isinstance(result, tuple) or result.should_continue:
            self.checkpointed_experiment_handler._save_checkpoint((experiment, results_list), name, specification)
            result = experiment.step()
            if isinstance(result, OverlappingOutputCheckpointedExperimentReturnValue):
                self.checkpointed_experiment_handler.publish_progress(experiment,specification,
                                                                      (result.progress, result.max_iterations))
                if result.should_serialize:
                    yield {'specification': result.specification, 'result': result.return_value}
            else:
                self.checkpointed_experiment_handler.publish_progress(experiment, specification, result)
        #this is done to have the runner know that the entire experiment completed succesfully
        yield {"specification":specification, 'result': []}
