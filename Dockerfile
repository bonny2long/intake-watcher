FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir -e .

ENV DATA_ROOT=/app/data \
    INTAKE_MODE=hybrid \
    STABILITY_SECONDS=1200 \
    POLL_SECONDS=300 \
    STATUS_LOG_HEARTBEAT_SECONDS=900 \
    REQUIRE_READY_MARKER=false \
    ALLOW_SINGLE_FILE_PROMOTION=true \
    COLLISION_POLICY=block \
    DESTRUCTIVE_ACTIONS_ENABLED=false \
    AUTO_RUN=true

EXPOSE 8091
CMD ["python", "-m", "intake_watcher.server", "--host", "0.0.0.0", "--port", "8091"]
