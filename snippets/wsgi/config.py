# see http://docs.gunicorn.org/en/latest/configure.html#configuration-file

from os import getenv


bind = '0.0.0.0:{}'.format(getenv('PORT', 8000))
workers = getenv('WSGI_NUM_WORKERS', 2)
accesslog = '-'
errorlog = '-'
loglevel = getenv('WSGI_LOG_LEVEL', 'info')

# Larger keep-alive values maybe needed when directly talking to ELBs
# See https://github.com/benoitc/gunicorn/issues/1194
keepalive = getenv('WSGI_KEEP_ALIVE', 2)
worker_class = getenv('GUNICORN_WORKER_CLASS', 'meinheld.gmeinheld.MeinheldWorker')
worker_tmp_dir = '/dev/shm'
