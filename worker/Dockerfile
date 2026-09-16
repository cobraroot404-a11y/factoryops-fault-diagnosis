FROM python:3.12-slim

WORKDIR /srv

COPY worker/requirements.txt ./worker-requirements.txt
RUN pip install --no-cache-dir -r worker-requirements.txt

COPY backend/app ./app
COPY worker/*.py ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/srv

# Overridden by docker-compose `command:` per service (diagnosis_consumer.py,
# missing_telemetry_checker.py, outbox_relay.py all live in this same image).
CMD ["python", "diagnosis_consumer.py"]
