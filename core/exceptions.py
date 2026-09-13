from rest_framework import status
from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT


class Gone(APIException):
    status_code = status.HTTP_410_GONE
