import email
import json
import smtplib
import typing

from smallab.callbacks import CallbackManager
from smallab.utilities.hooks import format_exception


class EmailCallback(CallbackManager):
    def __init__(self, email_adress, port):
        self.email_address = email_adress
        self.smtp_port = port

    def __send(self, message):
        message["Subject"] = "Smallab report"
        message["From"] = self.email_address
        message["To"] = self.email_address
        s = smtplib.SMTP('localhost', self.smtp_port)
        s.send_message(message)
        s.quit()

    def on_specification_failure(self, exception, specification):
        message = email.message.EmailMessage()
        content = "!!! Failure !!! \n\n Specification: %s \n\n Exception: %s" % (
            str(json.dumps(specification, sort_keys=True, indent=1)), str(format_exception(exception)))
        message.set_content(content)
        self.__send(message)

    def on_specification_complete(self, specification: typing.Dict, result: typing.Dict) -> typing.NoReturn:
        message = email.message.EmailMessage()
        content = "!!! Sucesss !!! \n\n Specification: %s" % (str(json.dumps(specification, sort_keys=True, indent=1)))
        message.set_content(content)
        self.__send(message)

    def on_batch_failure(self, errors: typing.List[Exception],
                         specifications: typing.List[typing.Dict]) -> typing.NoReturn:
        message = email.message.EmailMessage()

        content = "!!! Failure !!! \n\n "
        for exception, specification in zip(errors, specifications):
            content += "Specification: %s \n\n Exception: %s \n\n" % (
                str(json.dumps(specification, sort_keys=True, indent=1)), str(format_exception(exception)))
        message.set_content(content)

        self.__send(message)

    def on_batch_complete(self, specifications: typing.List[typing.Dict]) -> typing.NoReturn:
        message = email.message.EmailMessage()
        content = "!!! Sucesss !!! \n\n"
        for specification in specifications:
            content += "Specification: %s \n\n" % (str(json.dumps(specification, sort_keys=True, indent=1)))
        message.set_content(content)
        self.__send(message)


class EmailCallbackBatchOnly(EmailCallback):
    def on_specification_complete(self, specification: typing.Dict, result: typing.Dict) -> typing.NoReturn:
        return None

    def on_batch_failure(self, errors: typing.List[Exception],
                         specifications: typing.List[typing.Dict]) -> typing.NoReturn:
        return None
