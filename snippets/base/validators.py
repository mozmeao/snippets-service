from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible


@deconstructible
class MinValueValidator(BaseValidator):
    message = 'Ensure this value is greater than or equal to %(limit_value)s.'
    code = 'min_value'

    def compare(self, a, b):
        return int(a) < int(b)
