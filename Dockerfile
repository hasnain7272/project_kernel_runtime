FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY ./src /app/src
COPY ./main.py /app/main.py
COPY ./ui /app/ui

EXPOSE 8089

CMD ["python", "-m", "uvicorn", "src.api.fastapi_gateway:app", "--host", "0.0.0.0", "--port", "8089", "--workers", "2"]
