FROM python:2.7
RUN apt-get update && apt-get install -y libmysqlclient-dev gettext libjpeg62-turbo-dev

WORKDIR /app

# First copy requirements.txt and peep so we can take advantage of
# docker caching.
COPY requirements /tmp/requirements
RUN pip install -r /tmp/requirements/dev.txt

EXPOSE 8000
ENV PYTHONUNBUFFERED 1
