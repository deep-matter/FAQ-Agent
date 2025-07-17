# FAQ AGENTIC FLOW System

[![CI/CD Pipeline](https://github.com/your-org/faq-agent/actions/workflows/deploy.yml/badge.svg)](https://github.com/your-org/faq-agent/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

An intelligent FAQ assistant system built with production-grade multi-agent architecture using LangChain and LangGraph. The system transforms stateless LLM interactions into stateful conversations through PostgreSQL-based session management and RAG (Retrieval-Augmented Generation) pipeline.

**Core Innovation**: Converting traditional stateless AI interactions into conversational FAQ support that remembers previous questions and builds contextual understanding over time.

![FAQ Agentic Flow Architecture](assets/e2e.png)

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Key Features](#key-features)
3. [Quick Start](#quick-start)
4. [Development Setup](#development-setup)
5. [Production Deployment](#production-deployment)
6. [API Documentation](#api-documentation)
7. [Configuration](#configuration)
8. [Monitoring & Observability](#monitoring--observability)
9. [Contributing](#contributing)

## System Architecture

### Multi-Agent Pipeline

The FAQ AGENTIC FLOW system implements a sophisticated multi-agent architecture:

- **Grader Agent**: Query preprocessing and relevance filtering
- **FAQ Agent**: Central response generation with session memory
- **Scrapper Agent**: Intelligent fallback with extended search capabilities
- **Orchestrator**: LangGraph-based workflow coordination

### Core Components

- **RAG Pipeline**: Automated content acquisition and vector storage
- **Session Management**: PostgreSQL-based conversation persistence
- **Knowledge Base**: Chroma + FAISS vector stores for semantic search
- **Workflow Engine**: LangGraph orchestration for agent coordination

## Key Features

**Architecture**
- Multi-stage Docker builds with security best practices
- Comprehensive CI/CD pipeline with GitHub Actions
- Environment-specific configurations (dev/staging/production)

**Intelligent Agent System**
- Context-aware responses with conversation history
- Three-tier fallback strategy for comprehensive coverage
- Real-time query preprocessing and intent classification

**Scalable Infrastructure**
- PostgreSQL for reliable session persistence
- Redis caching for improved performance
- Horizontal scaling with Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Clone Repository

```bash
git clone https://github.com/your-org/faq-agent.git
cd faq-agent
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required: OPENAI_API_KEY, database credentials
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
docker-compose logs -f faq-agent
```

### 4. Access Services

- **API Documentation**: http://localhost:8000/docs
- **FAQ API**: http://localhost:8000/api/v1/faq/query
- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/api/v1/status

## Development Setup

### Using uv (Recommended)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync --all-extras --dev

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Start development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Database Setup

```bash
# Start PostgreSQL only
docker-compose up -d postgres

# The application will automatically initialize tables on startup
```


### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy app/
```

## Production Deployment

### Docker Production Build

```bash
# Build production image
docker build --target production -t faq-agent:latest .

# Run production container
docker run -d \
  --name faq-agent \
  -p 8000:8000 \
  --env-file .env \
  faq-agent:latest
```

### AWS ECS Deployment

The repository includes GitHub Actions workflows for automated deployment to AWS ECS:

1. **Staging**: Deploys from `develop` branch to staging environment
2. **Production**: Deploys from `main` branch to production environment

### Environment Variables

Key  environment variables:

```bash
ENVIRONMENT=production
OPENAI_API_KEY=your_openai_api_key
DB_HOST=your_postgres_host
DB_PASSWORD=secure_password
```

## API Documentation

### Core Endpoints

#### Query FAQ
```
POST /api/v1/faq/query
```

Submit FAQ questions and receive intelligent responses with conversation context.

#### Session History
```
GET /api/v1/faq/session/{session_id}/history
```

Retrieve conversation history for a specific session.


Check system health and component status.

### Authentication

The system supports optional user authentication for personalized experiences and analytics.

### Rate Limiting

Default rate limits:
- 60 requests per minute per IP
- Burst capacity of 10 requests

## Configuration

### Core Settings

All configuration is managed through environment variables. See `.env.example` for comprehensive options:

- **Database**: PostgreSQL connection and pool settings
- **AI Models**: OpenAI API configuration and model selection
- **Monitoring**: Logging levels 

### Vector Store Configuration

- **Chunk Size**: 1000 characters (configurable)
- **Overlap**: 0 characters (configurable)
- **Similarity Search**: Top-3 retrieval with 0.7 threshold
- **Embedding Model**: text-embedding-3-small
s

### Logging

Structured JSON logging with configurable levels:
- Request/response logging
- Error tracking with stack traces



## Project Structure

```
faq-agent/
├── app/                    # Application source code
│   ├── agents/            # Multi-agent implementations
│   ├── api/               # FastAPI routes and models
│   ├── config/            # Configuration management
│   ├── core/              # Core business logic
│   ├── database/          # Database connections and setup
│   └── workflow/          # LangGraph orchestration
├── assets/                # Documentation assets
├── tests/                 # Test suite
├── .github/workflows/     # CI/CD pipeline
├── docker-compose.yml     # Development environment
├── Dockerfile            # Production container
├── pyproject.toml        # Project configuration
└── main.py              # Application entry point
```

