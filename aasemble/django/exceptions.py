from rest_framework.exceptions import APIException


class DuplicateResourceException(APIException):
    status_code = 409
    default_detail = 'Duplicate resource'
