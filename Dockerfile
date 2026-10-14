FROM python:3.12-slim AS dependencies
WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 RELAY_ALLOW_LIVE=0 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright RELAY_EMBEDDED_WORKER=0 RELAY_STATE_DIR=/state
COPY requirements.txt ./
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /opt/playwright
COPY src ./src
COPY data ./data
RUN mkdir -p /state /app/artifacts/generated && chown -R 10001:10001 /state /app/artifacts

FROM dependencies AS test
COPY tests ./tests
COPY scripts ./scripts
USER 10001:10001
ENV RELAY_EMBEDDED_WORKER=1
CMD ["sh", "scripts/container_checks.sh"]

FROM dependencies AS runtime
USER 10001:10001
EXPOSE 8100
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=10s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/healthz', timeout=2)"
CMD ["python", "-m", "uvicorn", "relayops.asgi:application", "--factory", "--host", "0.0.0.0", "--port", "8100"]
