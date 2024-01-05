FROM python:3.10 AS builder

ARG PENDING_REPO=https://github.com/biothings/pending.api.git
ARG PENDING_BRANCH=master
WORKDIR /build/pending.api
RUN git clone -b ${PENDING_BRANCH} --recursive ${PENDING_REPO} .
WORKDIR /build/wheels
RUN pip wheel -r /build/pending.api/requirements.txt


FROM python:3.10-slim
RUN apt update -q -y && apt install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN apt-get update -y && apt-get install vim -y && apt-get install sudo -y && apt-get install telnet -y
RUN useradd -m pending && usermod -aG sudo pending
USER pending
RUN python -m venv /home/pending/venv
COPY --from=builder --chown=pending:pending /build/wheels /home/pending/wheels
RUN /home/pending/venv/bin/pip install /home/pending/wheels/*.whl && rm -rf /home/pending/wheels
COPY --from=builder --chown=pending:pending /build/pending.api /home/pending/pending.api

STOPSIGNAL SIGINT

WORKDIR /home/pending/pending.api
EXPOSE 9000

ENV ES_HOST 127.0.0.1:9200
ENV OPENTELEMETRY_ENABLED False
ENV OPENTELEMETRY_SERVICE_NAME "Service Provider"
ENV OPENTELEMETRY_JAEGER_HOST localhost
ENV OPENTELEMETRY_JAEGER_PORT 6831

ENTRYPOINT ["/home/pending/venv/bin/python", "index.py"]
CMD ["--conf=config_web", "--port=9000"]
