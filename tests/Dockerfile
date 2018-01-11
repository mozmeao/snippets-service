FROM python:2-alpine3.7
WORKDIR /src
COPY requirements.txt /src
RUN pip install -r requirements.txt
COPY . /src
CMD pytest
