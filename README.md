# AI Resume Screener & Semantic Ranking Platform

An enterprise-grade, asynchronous backend API built with **FastAPI**, **PostgreSQL (pgvector)**, and **Google Gemini API** (using the new `google-genai` SDK) to ingest candidate resumes and rank them semantically against job descriptions.

---

## 🏗️ Architecture & Flow

```mermaid
graph TD
    A[Upload PDF Resume] --> B[FastAPI Endpoint /resumes/upload]
    B --> C[PyMuPDF Text Extraction & Chunking]
    C --> D[Gemini Embeddings Generator models/gemini-embedding-2]
    C --> E[Gemini Structured Profile Extractor gemini-2.5-flash]
    D --> F[(PostgreSQL + pgvector Database)]
    E --> F
    
    G[Job Description Match Request] --> H[FastAPI Endpoint /jobs/match]
    H --> I[Gemini Job Embeddings Generator]
    I --> J[pgvector Cosine Distance Search <=> ]
    J --> K[Retrieve Relevant Resume Snippets]
    K --> L[Gemini Evaluation and Fit Scoring gemini-2.5-flash]
    L --> M[Log Parameters & Metrics to MLflow]
    L --> N[Return Sorted Rankings to Client]
```

---

## 🛠️ Technology Stack

- **Framework**: FastAPI (Asynchronous Python API)
- **Database & Vectors**: PostgreSQL with the `pgvector` extension for semantic vector similarity search, mapped with SQLAlchemy.
- **AI Model Client**: Google GenAI SDK (`gemini-2.5-flash` for structured profile extraction and fit assessment, `models/gemini-embedding-2` for 3072-dimensional vector embedding generation).
- **ML / Experiment Tracking**: MLflow (for logging fit parameters, system prompts, and candidate match scores).
- **Infrastructure**: AWS (ECR, ECS Fargate, Application Load Balancer, S3, RDS PostgreSQL) configured via Terraform.
- **CI/CD**: GitHub Actions workflow verifying syntax, linting (Flake8), formatting (Black), and running unit tests.

---

## 🚀 Setup & Local Development

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11 or 3.12

### 2. Configure Environment Variables
Copy the template `.env.example` file and populate it with your API keys and configuration:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
- `GEMINI_API_KEY`: Your Google Gemini API Key
- `DATABASE_URL`: Connection string for PostgreSQL (e.g. `postgresql+asyncpg://postgres:postgres_password@localhost:5432/resume_screener`)
- `MLFLOW_TRACKING_URI`: URL to the MLflow tracking server (e.g. `http://localhost:5000`)

### 3. Spin up local database and MLflow
Use Docker Compose to launch PostgreSQL (pgvector) and MLflow:
```bash
docker compose -f docker/docker-compose.yml up -d
```

### 4. Setup Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 5. Initialize the Database
Enable the `vector` extension and run table creation scripts:
```bash
python init_db.py
```

### 6. Run the local demo
You can test the ingestion and ranking pipeline using the built-in local CLI demo:
```bash
python demo_phase1.py
```

---

## 🧪 Testing & Code Quality

Validate the backend and services using the command line:
```bash
# Run unit and integration tests
python -m pytest

# Run linting checks
flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics

# Verify code formatting matches black rules
black --check app tests
```

---

## 📡 API Reference & Interactive UI

FastAPI provides an automatic, interactive Swagger UI out of the box. Once the service is running, you can visit the dashboard to interact with all API endpoints:

- **Swagger UI**: `/docs` (e.g. `http://localhost:8000/docs`)
- **Alternative ReDoc UI**: `/redoc`

### Endpoints

#### 1. Upload Resume
- **Endpoint**: `POST /api/v1/resumes/upload`
- **Payload**: `multipart/form-data` with `file` (PDF)
- **Response**:
```json
{
  "message": "Resume successfully processed, embedded, and indexed.",
  "resume_id": 1,
  "filename": "sample.pdf",
  "detected_candidate": "John Doe"
}
```

#### 2. Match & Rank Candidates
- **Endpoint**: `POST /api/v1/jobs/match`
- **Payload**:
```json
{
  "job_description": "We need a Senior Python Developer with FastAPI.",
  "limit": 5
}
```
- **Response**:
```json
{
  "job_description": "We need a Senior Python Developer with FastAPI.",
  "results": [
    {
      "candidate_id": 1,
      "filename": "sample.pdf",
      "name": "John Doe",
      "fit_score": 100,
      "justification": "Candidate is a Senior Backend Developer with explicit proficiency and direct work experience in Python, FastAPI, and Docker..."
    }
  ]
}
```

#### 3. Health check
- **Endpoint**: `GET /health`
- **Response**: `{"status": "healthy", "service": "resume-screener-api"}`

---

## 📊 Experiment Tracking (MLflow)

All candidate assessment fits, model parameters, and prompts are tracked. 
- Open the MLflow dashboard locally by going to `http://localhost:5000`.
- Inside, you will find the `Resume_Screening_Rankings` experiment containing the run history, metrics, and prompts.

---

## 🚢 Production Deployment

Infrastructure is fully provisioned on AWS via Terraform.

1. **Navigate to the Terraform folder**: `cd terraform`
2. **Initialize Workspace**: `terraform init`
3. **Plan Changes**: `terraform plan -var="db_password=your_secure_password"`
4. **Deploy to Cloud**: `terraform apply -var="db_password=your_secure_password"`

Upon successful apply, Github Actions will automatically build the docker image (`docker/Dockerfile.production`) and push it to AWS ECR, triggering an update to your Amazon ECS Fargate service behind the Application Load Balancer.
