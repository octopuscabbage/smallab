import typing

from smallab.experiment_types.checkpointed_experiment import CheckpointedExperiment
from smallab.experiment_types.experiment import ExperimentBase, Experiment
from smallab.experiment_types.handlers.checkpointed_experiment_handler import CheckpointedExperimentHandler
from smallab.experiment_types.handlers.overlapping_output_checkpointed_experiment_handler import \
    OverlappingOutputCheckpointedExperimentHandler
from smallab.experiment_types.overlapping_output_experiment import OverlappingOutputCheckpointedExperiment
from smallab.smallab_types import Specification


def run_with_correct_handler(experiment: ExperimentBase, name: typing.AnyStr, specification: Specification):
    if isinstance(experiment, CheckpointedExperiment):
        return CheckpointedExperimentHandler().run(experiment, name, specification)
    elif isinstance(experiment, OverlappingOutputCheckpointedExperiment):
        return OverlappingOutputCheckpointedExperimentHandler().run(experiment, name, specification)
    elif isinstance(experiment, Experiment):
        return experiment.main(specification)
    else:
        raise Exception("Experiment Handler not Understood")
