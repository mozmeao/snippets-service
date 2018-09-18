from django.forms import Select, widgets


class RangeWidget(widgets.MultiWidget):
    template_name = 'widgets/jexlrange.html'

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        kwargs['widgets'] = [
            Select(choices=choices),
            Select(choices=choices),
        ]
        super().__init__(*args, **kwargs)

    def decompress(self, value):
        if value:
            return value.split(',')
        return [None, None]
