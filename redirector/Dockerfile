FROM python:3.8-slim-buster AS builder

EXPOSE 8000

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="/venv/bin:$PATH"
ENV LANG=C.UTF-8

RUN python -m venv /venv/


RUN bash -c 'for i in {1..8}; do mkdir -p "/usr/share/man/man$i"; done' && \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY requirements.txt ./
RUN pip install --require-hashes --no-cache-dir -r requirements.txt
COPY . /app


# Production Image
FROM python:3.8-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="/venv/bin:$PATH"
ENV LANG=C.UTF-8

CMD ["python", "main.py"]

WORKDIR /app

RUN adduser --uid 1000 --disabled-password --gecos '' webdev

COPY --from=builder /venv /venv
COPY --from=builder /app /app

RUN chown webdev.webdev -R .
USER webdev

ARG GIT_SHA=head
ENV GIT_SHA=${GIT_SHA}
