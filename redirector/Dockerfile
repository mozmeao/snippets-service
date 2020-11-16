FROM python:3.7-slim-buster

EXPOSE 8000
CMD ["python", "main.py"]

RUN adduser --uid 1000 --disabled-password --gecos '' webdev

WORKDIR /app

COPY requirements.txt ./
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . /app

RUN chown webdev.webdev -R .
USER webdev

ARG GIT_SHA=head
ENV GIT_SHA=${GIT_SHA}
