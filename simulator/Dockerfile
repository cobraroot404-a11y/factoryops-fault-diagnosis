FROM python:3.12-slim

WORKDIR /srv

COPY simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator/simulate.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "simulate.py"]
