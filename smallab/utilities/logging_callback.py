import logging
import logging.config
import pprint
import traceback
import typing

from smallab.callbacks import CallbackManager


class LoggingCallback(CallbackManager):
    @staticmethod
    def pretty_printer():
        return pprint.PrettyPrinter()

    def on_specification_complete(self, specification: typing.Dict, result: typing.Dict) -> typing.NoReturn:
        pp = LoggingCallback.pretty_printer()
        specification_string = pp.pformat(specification)
        result_string = pp.pformat(result)
        logging.info(
            "\nSpecification Complete\nSpecification:\n{}\nResult:\n{}".format(specification_string,
                                                                               result_string))

    def on_specification_failure(self, exception: Exception, specification: typing.Dict) -> typing.NoReturn:
        pp = LoggingCallback.pretty_printer()
        traceback_string = traceback.format_exc()
        specification_string = pp.pformat(specification)
        logging.error("\nSpecification Failure\nSpecification:\n{}\nException:\n{}".format(specification_string,
                                                                                           traceback_string))
