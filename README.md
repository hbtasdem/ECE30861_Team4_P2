# 461_repo
461 repo

Phase 2:
Team 4
Navya Datla, Sai Gandavarapu, Georgia Griffin, Hilal Beyza Tasdemir

Phase 1:
Anjali Vanamala, Andrew Diab, Pryce Tharpe, Shaan Sriram (Shaantanu Sriram)

For exe rebuild use:
pyinstaller --onefile --console --name "model_scorer" src/__main__.py


The Model Registry API is a backend service for registering, managing, and analyzing machine learning artifacts such as models, datasets, and code. Artifacts are registered via source URLs (e.g., Hugging Face or GitHub) and stored with structured metadata, allowing users to retrieve, update, and analyze artifacts through a RESTful API.

The system is implemented using FastAPI, deployed on AWS EC2, and uses Amazon S3 for persistent artifact storage. Authentication is handled through a user-based, token-driven mechanism, and the API is fully documented via OpenAPI.

Features:
- Register ML artifacts (models, datasets, code) from URLs
- Retrieve, update, and delete artifacts by ID
- Enumerate and search artifacts
- User registration and authentication with bearer tokens
- Artifact cost estimation (download size)
- License compatibility checks for models
- Basic artifact lineage endpoint (structure present)
- Health and monitoring endpoints with CloudWatch integration
- Automated deployment to AWS EC2 via GitHub Actions


Architecture:

Backend Framework: FastAPI (Python)
Storage: Amazon S3
Compute: AWS EC2
CI/CD: GitHub Actions (push-to-main deployment)
Monitoring: AWS CloudWatch
API Documentation: OpenAPI 3.1 (/docs)
