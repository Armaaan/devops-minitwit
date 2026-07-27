# devops-minitwit

ITU DevOps, Software Evolution and Software Maintenance (Spring 2026)

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI (not Flask — as required by session 02)
- **ORM:** SQLAlchemy (no raw SQL — as required by session 05)
- **Database:** SQLite (migrated to PostgreSQL in session 06)
- **Container:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Hosting:** DigitalOcean (Frankfurt, FRA1)

**Why FastAPI?** FastAPI provides automatic OpenAPI documentation, type safety via Python type hints, and modern async support — while keeping Python as the implementation language as required. It uses the same Jinja2 templating engine as Flask, making the migration straightforward.

## Live Application

- **Web UI:** http://46.101.179.118:5000
- **Simulator API:** http://46.101.179.118:5000

## Repository Structure

```
itu-minitwit/       # Original legacy Python 2 + Flask app (session 01)
minitwit/           # Refactored FastAPI app (session 02+)
  app.py            # Application routes and simulator API
  models.py         # SQLAlchemy ORM models (User, Message, Follower)
  schema.sql        # Original DB schema
  requirements.txt  # Python dependencies
  Dockerfile        # Container definition
  templates/        # Jinja2 HTML templates
  static/           # CSS
remote_files/       # Production deployment files
  docker-compose.yml
.github/workflows/
  ci.yml            # Run tests on every push
  cd.yml            # Build, push, deploy on main push
provision.sh        # Provision a new DigitalOcean droplet (session 03)
```

## Deploying from scratch (session 03 task 2a+2b)

### Step 1: Provision a new server

```bash
export DO_API_TOKEN=<your-digitalocean-api-token>
export SSH_KEY_ID=<your-ssh-key-id>
./provision.sh
```

To find your SSH key ID:
```bash
curl -X GET -H "Authorization: Bearer $DO_API_TOKEN" \
  "https://api.digitalocean.com/v2/account/keys"
```

### Step 2: Deploy the application

SSH into the server and run:

```bash
ssh root@<server-ip>
apt-get update && apt-get install -y docker.io
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
systemctl start docker && systemctl enable docker
mkdir -p /minitwit
curl -o /minitwit/docker-compose.yml \
  https://raw.githubusercontent.com/Armaaan/devops-minitwit/main/remote_files/docker-compose.yml
cd /minitwit && docker compose up -d
```

The application will be available at `http://<server-ip>:5000`.

## Running locally

```bash
git clone https://github.com/Armaaan/devops-minitwit.git
cd devops-minitwit
docker compose up --build
```

Open http://localhost:5001/public

## Running tests

```bash
cd minitwit
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt pytest httpx
pytest minitwit_tests.py -v
```

## CI/CD Pipeline

Every push to `main`:
1. **CI** — runs `minitwit_tests.py` (4 integration tests)
2. **CD** — builds Docker image, pushes to Docker Hub, deploys to server

## Session Progress

| Session | Task | Status |
|---------|------|--------|
| 01 | Python 3 migration | ✅ |
| 02 | FastAPI refactor + Docker | ✅ |
| 03 | Simulator API + DigitalOcean deploy | ✅ |
| 04 | GitHub Actions CI/CD | ✅ |
| 05 | SQLAlchemy ORM (no raw SQL) | ✅ |
