FROM python:3.12-slim

# Don't run as root (session 11 security hardening)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Create data directory for DB and latest file
RUN mkdir -p /data && chown appuser:appgroup /data

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY app.py models.py schema.sql ./
COPY templates/ templates/
COPY static/ static/

# Switch to non-root user
USER appuser

EXPOSE 5000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
