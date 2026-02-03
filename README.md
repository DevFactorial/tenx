# tenx
Workflow Orchestration Software.


python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

## Alembic
alembic revision --autogenerate -m "Initial workflow tables"

alembic upgrade head

# Celery
celery -A app.core.celery_app worker --loglevel=info --concurrency=1 -Q execution_queue --logfile=/Users/raghuveermb/logs/celery.log