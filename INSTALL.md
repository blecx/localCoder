# Installation Guide

## Dependencies

- Python 3.10+
- Docker and Docker Compose
- Node.js (optional, for specific tooling)

## 1. Clone the repository

```bash
git clone <repository-url>
cd localCoder
```

## 2. Set up a Python Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

## 3. Install Python Dependencies

```bash
# Install root requirements if applicable
pip install -r poc/requirements.txt
```

## 4. Docker Environment Setup

To run the full stack locally via Docker:

```bash
cd poc
docker-compose up --build -d
```
