import logging

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django_q.tasks import async_task


def message_task(message: str):
    logger = logging.getLogger("task_queue_debug")
    logger.debug("Message %s", message)
    if message == "crash":
        raise AssertionError("Crashed!")
    print(message)


def debug(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(request, "cciw/debug.html", {})


def task_queue_debug(request: HttpRequest) -> HttpResponse:
    message = request.GET.get("message", "[no message]")
    async_task(message_task, message)
    return HttpResponse(f"Task queued with message: {message}".encode())
