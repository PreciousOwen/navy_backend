# Django Ledger Docker Makefile

.PHONY: help build up down logs shell migrate createsuperuser collectstatic test clean backup restore

# Default target
help:
	@echo "Django Ledger Docker Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start development services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs"
	@echo "  make shell          - Access Django shell"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make createsuperuser - Create Django superuser"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make db-shell       - Access PostgreSQL shell"
	@echo "  make db-logs        - View database logs"
	@echo "  make backup         - Backup database"
	@echo "  make restore        - Restore database"
	@echo "  make db-reset       - Reset database (DESTRUCTIVE)"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up        - Start production services"
	@echo "  make prod-down      - Stop production services"
	@echo "  make prod-logs      - View production logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean up Docker resources"
	@echo "  make reset          - Reset everything (DESTRUCTIVE)"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart: down up

logs:
	docker-compose logs -f

shell:
	docker-compose exec web python manage.py shell

# Database commands
migrate:
	docker-compose exec web python manage.py migrate

createsuperuser:
	docker-compose exec web python manage.py createsuperuser

collectstatic:
	docker-compose exec web python manage.py collectstatic --noinput

# Production commands
prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

# Testing
test:
	docker-compose exec web python manage.py test

# Database management
db-shell:
	docker-compose exec db psql -U django_ledger_user -d django_ledger_db

db-logs:
	docker-compose logs db

# Backup and restore (PostgreSQL)
backup:
	@echo "Creating database backup..."
	docker-compose exec db pg_dump -U django_ledger_user django_ledger_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

restore:
	@read -p "Enter backup file name: " backup_file; \
	docker-compose exec -T db psql -U django_ledger_user django_ledger_db < $$backup_file

# Database reset (DESTRUCTIVE)
db-reset:
	@echo "WARNING: This will destroy all database data!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down; \
		docker volume rm $$(docker volume ls -q | grep postgres_data) 2>/dev/null || true; \
		docker-compose up -d db; \
		sleep 5; \
		make migrate; \
		make createsuperuser; \
		echo "Database reset complete."; \
	else \
		echo "Database reset cancelled."; \
	fi

# Maintenance commands
clean:
	docker system prune -f
	docker volume prune -f

reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker system prune -af; \
		docker volume prune -f; \
		echo "Reset complete."; \
	else \
		echo "Reset cancelled."; \
	fi

# Quick setup for new installations
setup: build up migrate createsuperuser
	@echo "Setup complete! Access the application at http://localhost:8000"

# Development workflow
dev: up logs

# Production deployment
deploy: prod-up
	@echo "Production deployment started. Check logs with 'make prod-logs'"
