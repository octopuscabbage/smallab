import json
import os
import pickle
import typing
from multiprocessing import cpu_count

from joblib import Parallel, delayed
from tqdm import tqdm

from smallab.experiment import Experiment
from smallab.utilities.hooks import format_exception


class ExperimentRunner(object):
    """
    The class which runs the batch of experiments
    """
    def __init__(self):
        self.on_specification_complete_function = None
        self.on_specification_failure_function = ExperimentRunner.__default_on_failure
        self.on_batch_complete_function = None
        self.on_batch_failure_function = None
        self.experiment_folder = "experiment_runs/"

    @staticmethod
    def __default_on_failure(exception: Exception,specification: typing.Dict):
        print("!!! Failure !!!")
        print(specification)
        print(format_exception(exception))

    def on_specification_complete(self, f: typing.Callable[[typing.Dict, typing.Dict], typing.NoReturn]) -> typing.NoReturn:
        """
        Sets a method to be called on the completion of each experiment
        :param f: A function to be called on the completiong of each experiment. It is passed the specification and the result and returns nothing
        :return: No return
        """
        self.on_specification_complete_function = f

    def on_specification_failure(self, f: typing.Callable[[Exception, typing.Dict], typing.NoReturn]) -> typing.NoReturn:
        """
        Sets a method to be called on the failure of each experiment
        :param f: A function called when an experiment fails. It is passed the exception raised and the specification for that experiment and returns nothing
        :return: No Return
        """
        self.on_specification_failure_function = f

    def on_batch_complete(self, f: typing.Callable[[typing.List[typing.Dict]],typing.NoReturn]) -> typing.NoReturn:
        """
        Sets a method to be called on the completion of all specifications provided to run
        :param f: The function to call. It is passed a list of specifications which were completed
        :return: No return
        """
        self.on_batch_complete_function = f
    def on_batch_failure(self, f: typing.Callable[[typing.List[Exception],typing.List[typing.Dict]],typing.NoReturn]) -> typing.NoReturn:
        """
        Sets a method to be called when 1 or more specifications failed to complete (Threw an exception
        :param f: The function to call. It is passed a list of exceptions and a list of specifications. The ith exception is the exception that was thrown for the ith specification
        :return: No return
        """
        self.on_batch_failure_function = f
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

    def get_save_file(self, name: typing.AnyStr, specification: typing.Dict) -> typing.AnyStr:
        """
        Get the filename to save the file under
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The filename to save this run under
        """
        return os.path.join(self.get_save_directory(name), str(hash(json.dumps(specification, sort_keys=True))))

    def find_uncompleted_specifications(self,name, specifications):
        already_completed_specifications = []

        for fname in os.listdir(self.get_save_directory(name)):
            with open(os.path.join(self.get_save_directory(name),fname),"rb") as f:
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
        if continue_from_last_run:
            need_to_run_specifications = self.find_uncompleted_specifications(name,specifications)
        else:
            need_to_run_specifications = specifications


        if not os.path.exists(self.get_save_directory(name)):
            os.makedirs(self.get_save_directory(name))

        exceptions = []
        failed_specifications = []
        completed_specifications = []
        if num_parallel == 1:
            for specification in tqdm(need_to_run_specifications, desc="Experiments", disable=not show_progress):
                exception_thrown = self.__run_and_save(name, experiment, specification,dont_catch_exceptions)

                #Add to batch completions and failures
                if exception_thrown is None:
                    completed_specifications.append(specification)
                else:
                    exceptions.append(exception_thrown)
                    failed_specifications.append(specification)
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
                else:
                    exceptions.append(exception_thrown)
                    failed_specifications.append(exception_thrown)


        #Call batch complete functions
        if exceptions and self.on_batch_failure_function is not None:
            self.on_batch_failure_function(exceptions,failed_specifications)

        if completed_specifications and self.on_batch_complete_function is not None:
            self.on_batch_complete_function(specifications)


    def __run_and_save(self, name, experiment, specification,dont_catch_exceptions):
        if not dont_catch_exceptions:
            try:
                result = experiment.main(specification)
                output_dictionary = {"specification": specification, "result": result}
                with open(self.get_save_file(name, specification), "wb") as f:
                    pickle.dump(output_dictionary, f)
                if self.on_specification_complete_function is not None:
                    self.on_specification_complete_function(specification, result)
                return None
            except Exception as e:
                self.on_specification_failure_function(e, specification)
                return e
        else:
            result = experiment.main(specification)
            output_dictionary = {"specification": specification, "result": result}
            with open(self.get_save_file(name, specification), "wb") as f:
                pickle.dump(output_dictionary, f)
            if self.on_specification_complete_function is not None:
                self.on_specification_complete_function(specification, result)
            return None

