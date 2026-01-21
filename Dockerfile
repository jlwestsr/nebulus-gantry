FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "nebulus_gantry.main:app", "--host", "0.0.0.0", "--port", "8000"]
