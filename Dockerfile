FROM python:3.8-slim-buster AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="/venv/bin:$PATH"
ENV LANG=C.UTF-8

RUN python -m venv /venv/

# Debian slim images needs the man directories created
# https://github.com/debuerreotype/debuerreotype/issues/10#issuecomment-438342078
RUN bash -c 'for i in {1..8}; do mkdir -p "/usr/share/man/man$i"; done' && \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential libxslt1.1 libxml2 libxml2-dev \
                                               libxslt1-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/* /user/share/man

WORKDIR /app

COPY requirements.txt .
RUN pip install --require-hashes --no-cache-dir -r requirements.txt

COPY . /app
RUN DEBUG=False SECRET_KEY=foo ALLOWED_HOSTS=localhost,\
    DATABASE_URL=sqlite:/// SITE_URL= \
    ./manage.py collectstatic --noinput



# Production image

FROM python:3.8-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="/venv/bin:$PATH"
ENV LANG=C.UTF-8

EXPOSE 8000
CMD ["./bin/run-prod.sh"]

RUN adduser --uid 1000 --disabled-password --gecos '' webdev

WORKDIR /app

RUN bash -c 'for i in {1..8}; do mkdir -p "/usr/share/man/man$i"; done' && \
    apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client pngquant libxslt1.1 libxml2 && \
    rm -rf /var/lib/apt/lists/* /usr/share/man

COPY --from=builder /venv /venv
COPY --from=builder /app /app

RUN chown webdev.webdev -R .
USER webdev

ARG GIT_SHA=head
ENV GIT_SHA=${GIT_SHA}
