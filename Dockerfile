FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files (SECRET_KEY required by settings at build time)
ARG SECRET_KEY=build-time-placeholder-not-used-in-production
ENV SECRET_KEY=$SECRET_KEY
RUN python manage.py collectstatic --noinput

# Run migrations and start Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py create_superuser_env && python manage.py setup_demo && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60"]
