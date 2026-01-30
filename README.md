# tenx
Workflow Orchestration Software.


python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Alembic
alembic revision --autogenerate -m "Initial workflow tables"

alembic upgrade head