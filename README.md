# devops-minitwit

ITU DevOps, Software Evolution and Software Maintenance (Spring 2026)

## Session 01
The `itu-minitwit/` directory contains the original legacy Python 2 + Flask
application migrated to Python 3.

## Session 02
The `minitwit/` directory contains the refactored application using:
- **FastAPI** (Python, not Flask — as required by session 02)
- **SQLAlchemy ORM** (no raw SQL — as required by session 05)
- **SQLite** (migrated to PostgreSQL in session 06)
- **Docker** for containerization

### Run locally
```bash
cd minitwit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

### Run with Docker
```bash
docker compose up --build
```

### Run tests
```bash
cd minitwit
source venv/bin/activate
pip install pytest httpx
python3 -m pytest minitwit_tests.py -v
```
