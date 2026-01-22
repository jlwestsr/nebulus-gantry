FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser
USER appuser

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "nebulus_gantry.main:app", "--host", "0.0.0.0", "--port", "8000"]
