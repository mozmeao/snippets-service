from django.forms import widgets


class JEXLMultiWidget(widgets.MultiWidget):

    def __init__(self, *args, **kwargs):
        if 'template_name' in kwargs:
            self.template_name = kwargs.pop('template_name')
        super().__init__(*args, **kwargs)

    def decompress(self, value):
        if value:
            return value.split(',')
        return [None, None]
