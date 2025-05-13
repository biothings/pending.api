# Stage 1: Build Python wheels and Frontend static files
FROM python:3.10 AS builder

# Install Node.js and npm for frontend build
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs git && \
    rm -rf /var/lib/apt/lists/*

ARG PENDING_REPO=https://github.com/biothings/pending.api.git
# ARG PENDING_BRANCH=master
ARG PENDING_BRANCH=add-caddy-server-supervisord
WORKDIR /build/pending.api
RUN git clone -b ${PENDING_BRANCH} --recursive ${PENDING_REPO} .

# Build Python wheels
WORKDIR /build/wheels
RUN pip wheel -r /build/pending.api/requirements.txt

# Build Frontend (adjust path and build output dir if needed)
WORKDIR /build/pending.api/web/web-app
RUN npm install
RUN npm run build

# Stage 2: Final runtime image
FROM python:3.10-slim

# Install system dependencies: git, supervisor, utils, and Caddy prerequisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        vim \
        sudo \
        telnet \
        supervisor \
        debian-keyring \
        debian-archive-keyring \
        apt-transport-https \
        curl \
        gnupg && \
    rm -rf /var/lib/apt/lists/*

# Install Caddy using official instructions
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && \
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list && \
    apt-get update && \
    apt-get install -y caddy

# Create non-root user
RUN useradd -m pending && usermod -aG sudo pending

# Set up Python environment for the user
USER pending
WORKDIR /home/pending
RUN python -m venv /home/pending/venv

# Install Python dependencies
COPY --from=builder --chown=pending:pending /build/wheels /home/pending/wheels
RUN /home/pending/venv/bin/pip install --no-cache-dir /home/pending/wheels/*.whl && rm -rf /home/pending/wheels

# Copy application code
COPY --from=builder --chown=pending:pending /build/pending.api /home/pending/pending.api

# Create directory for static files and copy them
USER root
RUN mkdir -p /srv/app/static
COPY --from=builder --chown=root:root /build/pending.api/web/web-app/dist /srv/app/static
# Ensure Caddy (which might run as 'caddy' user or 'root') can read static files
RUN chown -R root:root /srv/app/static && chmod -R 755 /srv/app/static

# Copy configuration files from the build context
COPY configuration/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY configuration/CaddyFile /etc/caddy/Caddyfile

# Ensure supervisor config is readable
RUN chmod 644 /etc/supervisor/conf.d/supervisord.conf
RUN chmod 644 /etc/caddy/Caddyfile

USER pending
WORKDIR /home/pending/pending.api

# Runtime Environment Variables
ENV ES_HOST http://127.0.0.1:9200
ENV OPENTELEMETRY_ENABLED False
ENV OPENTELEMETRY_SERVICE_NAME "Service Provider"
ENV OPENTELEMETRY_JAEGER_HOST localhost
ENV OPENTELEMETRY_JAEGER_PORT 6831

# Add PYTHONUNBUFFERED=1 to ensure logs appear immediately
ENV PYTHONUNBUFFERED=1

EXPOSE 9000
# Supervisor default stop signal
STOPSIGNAL SIGINT

# Run Supervisor as root (common practice)
USER root
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
