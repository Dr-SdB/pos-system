FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies + pg_dump v18 from PGDG
# - libpq-dev is installed AFTER PGDG repo is added so apt picks libpq5 v18 (not Debian's v17)
# - VERSION_CODENAME is read dynamically (handles trixie, bookworm, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl ca-certificates \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail \
       https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-18 libpq-dev \
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
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py create_superuser_env && python manage.py seed_sample_data --subdomain demo; gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60"]
