import email
import json
import smtplib
import typing
from smallab.utilities.hooks import  format_exception



def __send(email_address,message,port):
    message["Subject"] = "Smallab report"
    message["From"] = email_address
    message["To"] = email_address
    s = smtplib.SMTP('localhost',port)
    s.send_message(message)
    s.quit()


def email_on_specification_failure(email_address: typing.AnyStr,smtp_port:int) -> typing.Callable[[Exception,typing.Dict],typing.Any]:
    def closure(exception,specification):
        message = email.message.EmailMessage()
        content = "!!! Failure !!! \n\n Specification: %s \n\n Exception: %s" % (str(json.dumps(specification, sort_keys=True, indent=1)),str(format_exception(exception)))
        message.set_content(content)
        __send(email_address,message,smtp_port)


    return closure

def email_on_specification_success(email_address: typing.AnyStr,smtp_port:int) -> typing.Callable[[typing.Dict],typing.Any]:
    def closure(specification):
        message = email.message.EmailMessage()
        content = "!!! Sucesss !!! \n\n Specification: %s"  % (str(json.dumps(specification, sort_keys=True, indent=1)))
        message.set_content(content)
        __send(email_address,message,smtp_port)

    return closure

def email_on_batch_failure(email_address: typing.AnyStr,smtp_port:int) -> typing.Callable[[typing.List[Exception],typing.List[typing.Dict]],typing.Any]:
    def closure(exceptions,specifications):
        message = email.message.EmailMessage()

        content = "!!! Failure !!! \n\n "
        for exception, specification in zip(exceptions,specifications):
            content += "Specification: %s \n\n Exception: %s \n\n" % (str(json.dumps(specification, sort_keys=True, indent=1)),str(format_exception(exception)))
        message.set_content(content)

        __send(email_address,message,smtp_port)
    return closure

def email_on_batch_sucesss(email_address: typing.AnyStr,smtp_port:int) -> typing.Callable[[typing.List[typing.Dict]],typing.Any]:
    def closure(specifications):
        message = email.message.EmailMessage()
        content = "!!! Sucesss !!! \n\n"
        for specification in specifications:
            content += "Specification: %s \n\n"  % (str(json.dumps(specification, sort_keys=True, indent=1)))
        message.set_content(content)
        __send(email_address,message,smtp_port)

    return closure
