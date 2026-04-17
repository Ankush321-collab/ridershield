FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --default-timeout=100 --no-cache-dir -r /tmp/requirements.txt

COPY . /app

RUN python -m ml.training.train_isolation_forest

CMD ["uvicorn", "ml.serve:app", "--host", "0.0.0.0", "--port", "8001"]
