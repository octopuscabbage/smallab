import datetime
import json
import os
import pickle
import typing
from multiprocessing import cpu_count

from joblib import Parallel, delayed
from tqdm import tqdm

from smallab.callbacks import CallbackManager, PrintCallback
from smallab.experiment import Experiment
from smallab.utilities.hooks import format_exception


class ExperimentRunner(object):
    """
    The class which runs the batch of experiments
    """
    def __init__(self):
        self.experiment_folder = "experiment_runs/"
        self.callbacks = [PrintCallback]

    def attach_callbacks(self, callbacks: typing.List[CallbackManager]):
        """
        Attach callback handlers to this runner object, will call them in order they are presented
        :param args:
        :return:
        """
        self.callbacks = callbacks

    def set_experiment_folder(self, folder: typing.AnyStr) -> typing.NoReturn:
        """
        Sets the folder where experiments will be stored
        defaults to "experiment_runs/"

        :param folder: A String folder path for the experiments
        :return: Nothing
        """
        self.experiment_folder = folder

    def get_save_directory(self, name: typing.AnyStr) -> typing.AnyStr:
        """
        Get the directory that the runs will be saved under
        :param name: The name of the current batch
        :return: The folder to save the runs under
        """
        return os.path.join(self.experiment_folder, name)

    def get_pkl_file_location(self, name: typing.AnyStr, specification: typing.Dict) -> typing.AnyStr:
        """
        Get the filename to save the file under
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The filename to save this run under
        """
        return os.path.join(self.get_save_file_directory(name,specification), str(hash(json.dumps(specification, sort_keys=True))) + ".pkl")

    def get_specification_file_location(self,name: typing.AnyStr,specification: typing.Dict) -> typing.AnyStr:
        """
        Get the specification file location
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The location where the specification.json should be saved
        """
        return os.path.join(self.get_save_file_directory(name, specification),"specification.json")

    def get_save_file_directory(self,name: typing.AnyStr,specification: typing.Dict) -> typing.AnyStr:
        """
        Get the folder to save the .pkl file and specification.json file under
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The location where specification.json should be saved
        """
        return os.path.join(self.get_save_directory(name),
                            str(hash(json.dumps(specification, sort_keys=True))))

    def _write_to_completed_json(self, name:typing.AnyStr, completed_specifications:typing.List[typing.Dict], failed_specifications:typing.List[typing.Dict]):
        with open(os.path.join(self.get_save_directory(name),"completed.json"),'w') as f:
            json.dump(completed_specifications,f)
        with open(os.path.join(self.get_save_directory(name),"failed.json"),'w') as f:
            json.dump(failed_specifications, f)

    def _find_uncompleted_specifications(self, name, specifications):
        already_completed_specifications = []
        for root, _, files in os.walk(self.get_save_directory(name)):
            for fname in files:
                if ".pkl" in fname:
                    with open(os.path.join(root,fname),"rb") as f:
                        completed = pickle.load(f)
                    already_completed_specifications.append(completed["specification"])

        need_to_run_specifications = []
        for specification in specifications:
            if specification in already_completed_specifications:
                print("Skipping: " + str(specification))
            else:
                need_to_run_specifications.append(specification)
        return need_to_run_specifications

    def run(self, name: typing.AnyStr, specifications: typing.List[typing.Dict], experiment: Experiment,
            continue_from_last_run=True, num_parallel=1, show_progress=True, dont_catch_exceptions=False) -> typing.NoReturn:
        """
        The method called to run an experiment
        :param name: The name of this experiment batch
        :param specifications: The list of specifications to run. Should be a list of dictionaries. Each dictionary is passed to the experiment run method
        :param experiment: The experiment object to run
        :param continue_from_last_run: If true, will not redo already completed experiments. Defaults to true
        :param num_parallel: The number of experiments to run in parallel. 1 is don't run in parallel. Defaults to 1. None is use all available.
        :param show_progress: Whether or not to show a progress bar for experiment completion
        :return: No return
        """
        if not os.path.exists(self.get_save_directory(name)):
            os.makedirs(self.get_save_directory(name))

        if continue_from_last_run:
            need_to_run_specifications = self._find_uncompleted_specifications(name, specifications)
        else:
            need_to_run_specifications = specifications
        for callback in self.callbacks:
            callback.set_experiment_name(name)
        exceptions = []
        failed_specifications = []
        completed_specifications = []
        if num_parallel == 1:
            for specification in tqdm(need_to_run_specifications, desc="Experiments", disable=not show_progress):
                exception_thrown = self.__run_and_save(name, experiment, specification,dont_catch_exceptions)

                #Add to batch completions and failures
                if exception_thrown is None:
                    completed_specifications.append(specification)
                    self._write_to_completed_json(name, completed_specifications, failed_specifications)
                else:
                    exceptions.append(exception_thrown)
                    failed_specifications.append(specification)
                    self._write_to_completed_json(name, completed_specifications, failed_specifications)
        else:
            #Find the number of jobs to run
            if num_parallel is None:
                cores_to_use = min(cpu_count(), len(specifications))
            else:
                cores_to_use = min(num_parallel,len(specifications))
            #Begin to run everything in joblib
            with tqdm(total=len(need_to_run_specifications)) as pbar:
                def parallel_f(name,experiment,specification):
                    self.__run_and_save(name, experiment, specification,dont_catch_exceptions)
                    pbar.update(1)
                exceptions_thrown = Parallel(n_jobs=cores_to_use, prefer="threads")(
                    delayed(lambda specification: parallel_f(name, experiment, specification))(specification) for
                    specification in need_to_run_specifications)

            #Look through output to create batch failures and sucesses
            for specification,exception_thrown in zip(specifications,exceptions_thrown):
                if exception_thrown is None:
                    completed_specifications.append(specification)
                    self._write_to_completed_json(name, completed_specifications, failed_specifications)
                else:
                    exceptions.append(exception_thrown)
                    failed_specifications.append(exception_thrown)
                    self._write_to_completed_json(name, completed_specifications, failed_specifications)


        #Call batch complete functions
        if exceptions:
            for callback in self.callbacks:
                callback.on_batch_failure(exceptions,failed_specifications)

        if completed_specifications :
            for callback in self.callbacks:
                callback.on_batch_complete(specifications)


    def __run_and_save(self, name, experiment, specification,dont_catch_exceptions):
        def _interior_fn():
            result = experiment.main(specification)
            self._save_run(name, specification, result)
            for callback in self.callbacks:
                callback.on_specification_complete(specification, result)
            return None

        if not dont_catch_exceptions:
            try:
                _interior_fn()
            except Exception as e:
                for callback in self.callbacks:
                    callback.on_specification_failure(e, specification)
                return e
        else:
            _interior_fn()
            return None

    def _save_run(self, name, specification, result):
        os.makedirs(self.get_save_file_directory(name,specification))
        output_dictionary = {"specification": specification, "result": result}
        with open(self.get_pkl_file_location(name, specification), "wb") as f:
            pickle.dump(output_dictionary, f)
        with open(self.get_specification_file_location(name,specification),"w") as f:
            json.dump(specification,f)

