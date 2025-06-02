# Django Ledger Docker Setup

This document provides instructions for running the Django Ledger project using Docker and Docker Compose.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

1. **Clone the repository and navigate to the project directory**
   ```bash
   git clone <repository-url>
   cd REPORT-SACCOS-MICROSERVICE-MVP1
   ```

2. **Copy and configure the environment file**
   ```bash
   cp .env .env.local
   # Edit .env.local with your specific configuration
   ```

3. **Build and start the services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Django application: http://localhost:8000
   - Django admin: http://localhost:8000/admin
   - API documentation: http://localhost:8000/swagger/
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

## Environment Configuration

The `.env` file contains all the configuration options. Key settings include:

### Database Options

**PostgreSQL (Default)**
```env
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=django_ledger_db
DATABASE_USER=django_ledger_user
DATABASE_PASSWORD=your_secure_password
DATABASE_HOST=db
DATABASE_PORT=5432
```

**SQLite (Alternative for development)**
```env
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=db.sqlite3
```

**MySQL (Alternative)**
```env
DATABASE_ENGINE=django.db.backends.mysql
DATABASE_NAME=django_ledger_db
DATABASE_USER=django_ledger_user
DATABASE_PASSWORD=your_secure_password
DATABASE_HOST=db
DATABASE_PORT=3306
```

### Security Settings
```env
SECRET_KEY=your_very_secure_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## Docker Compose Configurations

### Development (docker-compose.yml)
- Uses PostgreSQL database
- Includes Redis for caching
- Volume mounts for live code editing
- Exposes ports for direct access

### Production (docker-compose.prod.yml)
- Uses PostgreSQL database
- Includes Nginx reverse proxy
- Optimized for production deployment
- SSL/TLS ready configuration

## Commands

### Development
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Build and start
docker-compose up --build

# Stop services
docker-compose down

# View logs
docker-compose logs -f web
```

### Production
```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Stop production services
docker-compose -f docker-compose.prod.yml down
```

### Database Management
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic

# Access Django shell
docker-compose exec web python manage.py shell

# Access PostgreSQL shell
docker-compose exec db psql -U django_ledger_user -d django_ledger_db
```

### Database Operations
```bash
# Backup database (PostgreSQL)
docker-compose exec db pg_dump -U django_ledger_user django_ledger_db > backup.sql

# Restore database (PostgreSQL)
docker-compose exec -T db psql -U django_ledger_user django_ledger_db < backup.sql

# View database logs
docker-compose logs db

# Reset database (DESTRUCTIVE)
docker-compose down
docker volume rm $(docker volume ls -q | grep postgres_data)
docker-compose up -d
```

## Volumes

- `static_volume`: Django static files
- `media_volume`: User uploaded media files
- `redis_data`: Redis cache data
- `postgres_data`: PostgreSQL database files (production)

## Networking

All services communicate through the `django_ledger_network` bridge network.

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   # Change port in docker-compose.yml if needed
   ```

2. **Permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

3. **Database connection issues**
   ```bash
   # Check database logs
   docker-compose logs db
   ```

4. **Redis connection issues**
   ```bash
   # Check Redis logs
   docker-compose logs redis
   ```

### Logs and Debugging
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Follow logs in real-time
docker-compose logs -f web
```

## Production Deployment

1. **Configure environment variables**
   - Set `DEBUG=False`
   - Use strong `SECRET_KEY`
   - Configure proper `ALLOWED_HOSTS`
   - Set up database credentials

2. **Use production compose file**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Set up SSL certificates**
   - Place SSL certificates in `./ssl/` directory
   - Uncomment HTTPS server block in `nginx.conf`

4. **Configure domain and DNS**
   - Point your domain to the server
   - Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`

## Monitoring

- Application logs: `docker-compose logs web`
- Database logs: `docker-compose logs db`
- Nginx logs: `docker-compose logs nginx`
- Redis logs: `docker-compose logs redis`

## Backup Strategy

1. **Database backups**: Regular PostgreSQL dumps
2. **Media files**: Backup `media_volume`
3. **Configuration**: Version control `.env` files (without secrets)

For more information, refer to the main project documentation.
