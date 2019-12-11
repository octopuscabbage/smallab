import datetime
import logging
import logging.config
import os
import traceback
import typing
import pprint

from smallab.callbacks import CallbackManager


class LoggingCallback(CallbackManager):
    @staticmethod
    def pretty_printer():
        return pprint.PrettyPrinter()

    def set_experiment_name(self,name):
        super().set_experiment_name(name)
        folder_loc = os.path.join("experiment_runs", name, "logs")
        file_loc = os.path.join(folder_loc, str(datetime.datetime.now()) + ".log")
        if not os.path.exists(folder_loc):
            os.makedirs(folder_loc)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
            handlers=[
                logging.FileHandler(file_loc),
                logging.StreamHandler()
            ])


    def on_specification_complete(self, specification: typing.Dict, result: typing.Dict) -> typing.NoReturn:
        pp = LoggingCallback.pretty_printer()
        specification_string = pp.pformat(specification)
        result_string = pp.pformat(result)
        logging.info(
            "\nSpecification Complete\nSpecification:\n{}\nResult:\n{}".format(specification_string, result_string))

    def on_specification_failure(self, exception: Exception, specification: typing.Dict) -> typing.NoReturn:
        pp = LoggingCallback.pretty_printer()
        traceback_string = traceback.format_exc()
        specification_string = pp.pformat(specification)
        logging.error("\nSpecification Failure\nSpecification:\n{}\nException:\n{}".format(specification_string,
                                                                                           traceback_string))

