import json
from io import StringIO

import xml.sax
from xml.sax import ContentHandler

from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible

import bleach

ALLOWED_TAGS = ['a', 'i', 'b', 'u', 'strong', 'em', 'br']
ALLOWED_ATTRIBUTES = {'a': ['href', 'data-metric']}


@deconstructible
class MinValueValidator(BaseValidator):
    message = 'Ensure this value is greater than or equal to %(limit_value)s.'
    code = 'min_value'

    def compare(self, a, b):
        return int(a) < int(b)


def validate_xml_template(data):
    parser = xml.sax.make_parser()
    parser.setContentHandler(ContentHandler())
    parser.setFeature(xml.sax.handler.feature_external_ges, 0)

    xml_str = '<div>\n{0}</div>'.format(data)
    try:
        parser.parse(StringIO(xml_str))
    except xml.sax.SAXParseException as e:
        # getLineNumber() - 1 to get the correct line number because
        # we're wrapping contents into a div.
        error_msg = (
            'XML Error: {message} in line {line} column {column}').format(
                message=e.getMessage(), line=e.getLineNumber() - 1, column=e.getColumnNumber())
        raise ValidationError(error_msg)
    return data


def validate_xml_variables(data):
    data_dict = json.loads(data)

    # set up a safer XML parser that does not resolve external
    # entities
    parser = xml.sax.make_parser()
    parser.setContentHandler(ContentHandler())
    parser.setFeature(xml.sax.handler.feature_external_ges, 0)

    for name, value in list(data_dict.items()):
        # Skip over values that aren't strings.
        if not isinstance(value, str):
            continue

        xml_str = '<div>{0}</div>'.format(value)
        try:
            parser.parse(StringIO(xml_str))
        except xml.sax.SAXParseException as e:
            error_msg = (
                'Data is not XML valid.\n'
                'XML Error in value "{name}": {message} in column {column}'
                .format(name=name, message=e.getMessage(),
                        column=e.getColumnNumber()))
            raise ValidationError(error_msg)
    return data


def validate_as_router_fluent_variables(data):
    data_dict = json.loads(data)

    # Will be replaced with a more generic solution when we develop more AS
    # Router templates. See #565
    if 'text' not in data_dict:
        return data

    text = data_dict['text']
    bleached_text = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    # Bleach escapes '&' to '&amp;'. We need to revert back to compare with
    # text
    bleached_text = bleached_text.replace('&amp;', '&')
    if text != bleached_text:
        error_msg = ('Text contains unsupported tags.'
                     'Only {} are supported'.format(', '.join(ALLOWED_TAGS)))
        raise ValidationError(error_msg)
    return data
