from functools import wraps

from django.utils.decorators import available_attrs


def access_control(origin='*', max_age=1, methods=('GET', 'HEAD', 'OPTIONS')):
    def decorator(view_fn):
        @wraps(view_fn, assigned=available_attrs(view_fn))
        def _wrapped_view(*args, **kwargs):
            response = view_fn(*args, **kwargs)
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Max-Age'] = max_age
            response['Access-Control-Allow-Methods'] = ', '.join(methods)
            return response
        return _wrapped_view
    return decorator
