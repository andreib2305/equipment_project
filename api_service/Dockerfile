FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY api_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY api_service ./api_service

EXPOSE 8001

CMD ["uvicorn", "api_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
