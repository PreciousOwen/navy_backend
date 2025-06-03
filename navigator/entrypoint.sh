#!/bin/bash

set -e

echo "Starting Django Ledger application..."

# Wait for database to be ready (if using PostgreSQL or MySQL)
if [ "$DATABASE_ENGINE" = "django.db.backends.postgresql" ] || [ "$DATABASE_ENGINE" = "django.contrib.gis.db.backends.postgis" ]; then
    echo "Waiting for PostgreSQL..."
    until nc -z $DATABASE_HOST $DATABASE_PORT; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 1
    done
    echo "PostgreSQL is up - continuing..."

    # Additional check using pg_isready
    until pg_isready -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER; do
        echo "PostgreSQL is not ready - sleeping"
        sleep 1
    done
    echo "PostgreSQL is ready!"
elif [ "$DATABASE_ENGINE" = "django.db.backends.mysql" ]; then
    echo "Waiting for MySQL..."
    until nc -z $DATABASE_HOST $DATABASE_PORT; do
        echo "MySQL is unavailable - sleeping"
        sleep 1
    done
    echo "MySQL is up - continuing..."
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if it doesn't exist..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
EOF

# Start the Django development server
echo "Starting Django development server..."
exec python manage.py runserver 0.0.0.0:8000