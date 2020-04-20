import typing

import abc

from smallab.utilities.hooks import format_exception


class CallbackManager(abc.ABC):
    def set_experiment_name(self, name):
        self.name = name

    def on_specification_complete(self, specification: typing.Dict, result: typing.Dict) -> typing.NoReturn:
        """
        Sets a method to be called on the completion of each experiment

        :return: No return
        """
        pass

    def on_specification_failure(self, exception: Exception, specification: typing.Dict) -> typing.NoReturn:
        """
        Sets a method to be called on the failure of each experiment
        :return: No Return
        """
        pass

    def on_batch_complete(self, specifications: typing.List[typing.Dict]) -> typing.NoReturn:
        """
        Sets a method to be called on the completion of all specifications provided to run
        :return: No return
        """
        pass

    def on_batch_failure(self, errors: typing.List[Exception],
                         specifications: typing.List[typing.Dict]) -> typing.NoReturn:
        """
        Sets a method to be called when 1 or more specifications failed to complete (Threw an exception
        :return: No return
        """
        pass


class PrintCallback(CallbackManager):
    def on_specification_complete(self, specification, return_value) -> typing.NoReturn:
        print("!!! Complete !!! ")
        print(specification)
        print(return_value)

    def on_specification_failure(self, exception, specification) -> typing.NoReturn:
        print("!!! Failure !!!")
        print(specification)
        print(format_exception(exception))
