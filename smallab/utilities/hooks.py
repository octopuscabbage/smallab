import traceback
import typing


def format_exception(e: Exception) -> typing.AnyStr:
    # https://stackoverflow.com/questions/9555133/e-printstacktrace-equivalent-in-python
    return "".join(traceback.format_exception(None, e, e.__traceback__))
