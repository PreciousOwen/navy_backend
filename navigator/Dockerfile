FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmariadb-dev \
    pkg-config \
    git \
    curl \
    netcat-traditional \
    postgresql-client \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip==24.0

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p staticfiles media
RUN chmod +x entrypoint.sh

RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "your_project.wsgi:application", "--bind", "0.0.0.0:8000"]
