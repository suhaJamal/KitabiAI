# KitabiAI Deployment Guide

Complete guide for deploying KitabiAI to production environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Production Deployment Options](#production-deployment-options)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Prerequisites

### Required Software
- Docker 20.10+ and Docker Compose 2.0+
- Git
- Python 3.11+ (for local development without Docker)

### Required Services
- **Azure Document Intelligence** account with API credentials
  - Endpoint URL
  - API Key
  - Used for Arabic PDF text extraction

---

## Environment Configuration

### 1. Create Environment File

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your actual values:

```bash
# Azure Document Intelligence (REQUIRED for Arabic PDFs)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_32_character_api_key_here

# FastText Language Detection (Cost Optimization)
USE_FASTTEXT_DETECTION=True
FASTTEXT_MODEL_PATH=lid.176.ftz
FASTTEXT_CONFIDENCE_THRESHOLD=0.5
FASTTEXT_SAMPLE_PAGES=15

# Application Settings
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=pdf
```

### 3. Important Notes

- **Never commit** the `.env` file to version control
- **Azure credentials** are required for Arabic PDF processing
- **FastText model** is automatically downloaded during Docker build

---

## Local Development

### Option 1: Docker Compose (Recommended)

```bash
# Build and start the application
docker-compose up --build

# Access the application
# Open http://localhost:8000 in your browser

# Stop the application
docker-compose down
```

### Option 2: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt

# Download FastText model
python scripts/validation/download_fasttext_model.py

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Production Deployment Options

### Option 1: Docker Deployment (Simplest)

#### On Any Server (Linux, Cloud VM, etc.)

```bash
# 1. Clone the repository
git clone https://github.com/suhaJamal/KitabiAI.git
cd KitabiAI

# 2. Create and configure .env file
cp .env.example .env
nano .env  # Edit with your Azure credentials

# 3. Build and run with Docker Compose
docker-compose up -d

# 4. Check status
docker-compose ps
docker-compose logs -f

# 5. Application is now running at http://your-server-ip:8000
```

#### Port Configuration

To use port 80 (standard HTTP), edit `docker-compose.yml`:

```yaml
ports:
  - "80:8000"  # Changed from "8000:8000"
```

---

### Option 2: Cloud Platforms

#### A. AWS Elastic Container Service (ECS)

```bash
# 1. Build and tag Docker image
docker build -t kitabiai:latest .
docker tag kitabiai:latest your-ecr-repo:latest

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-ecr-repo
docker push your-ecr-repo:latest

# 3. Create ECS task definition (use the image from ECR)
# 4. Create ECS service with load balancer
# 5. Configure environment variables in ECS task definition
```

#### B. Google Cloud Run

```bash
# 1. Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/your-project-id/kitabiai

# 2. Deploy to Cloud Run
gcloud run deploy kitabiai \
  --image gcr.io/your-project-id/kitabiai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=your-endpoint,AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key"
```

#### C. Azure Container Instances

```bash
# 1. Create resource group
az group create --name kitabiai-rg --location eastus

# 2. Deploy container
az container create \
  --resource-group kitabiai-rg \
  --name kitabiai-app \
  --image your-registry/kitabiai:latest \
  --dns-name-label kitabiai \
  --ports 8000 \
  --environment-variables \
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=your-endpoint \
    AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key
```

#### D. DigitalOcean App Platform

1. Connect your GitHub repository
2. Select the Dockerfile
3. Add environment variables in the dashboard
4. Deploy with one click

---

### Option 3: Kubernetes (Advanced)

```bash
# 1. Create Kubernetes secret for environment variables
kubectl create secret generic kitabiai-secrets \
  --from-literal=AZURE_ENDPOINT=your-endpoint \
  --from-literal=AZURE_KEY=your-key

# 2. Apply Kubernetes manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 3. Check deployment
kubectl get pods
kubectl logs -f deployment/kitabiai
```

**Sample `k8s/deployment.yaml`:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kitabiai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: kitabiai
  template:
    metadata:
      labels:
        app: kitabiai
    spec:
      containers:
      - name: kitabiai
        image: your-registry/kitabiai:latest
        ports:
        - containerPort: 8000
        env:
        - name: AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: kitabiai-secrets
              key: AZURE_ENDPOINT
        - name: AZURE_DOCUMENT_INTELLIGENCE_KEY
          valueFrom:
            secretKeyRef:
              name: kitabiai-secrets
              key: AZURE_KEY
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that automatically:

### Triggered On
- Push to `main` or `dev` branches
- Pull requests to `main`

### Pipeline Stages

1. **Lint**: Code quality checks (flake8, black)
2. **Build**: Run tests with pytest and coverage
3. **Docker**: Build Docker image
4. **Security**: Vulnerability scanning with Trivy

### Setup GitHub Secrets

Add these secrets to your GitHub repository:

1. Go to Repository Settings → Secrets and variables → Actions
2. Add the following secrets:

```
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=your-endpoint
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key
```

### Optional: Enable Docker Hub Publishing

Uncomment these lines in `.github/workflows/ci-cd.yml`:

```yaml
# - name: Login to Docker Hub
#   uses: docker/login-action@v2
#   with:
#     username: ${{ secrets.DOCKER_USERNAME }}
#     password: ${{ secrets.DOCKER_PASSWORD }}

# - name: Push Docker image
#   run: |
#     docker tag kitabiai:latest ${{ secrets.DOCKER_USERNAME }}/kitabiai:latest
#     docker push ${{ secrets.DOCKER_USERNAME }}/kitabiai:latest
```

Then add `DOCKER_USERNAME` and `DOCKER_PASSWORD` to GitHub secrets.

---

## Monitoring and Maintenance

### Health Checks

```bash
# Check if application is running
curl http://localhost:8000/

# Check application logs
docker-compose logs -f

# Check resource usage
docker stats
```

### Log Management

Logs are stored in the `logs/` directory:

```bash
# View logs
tail -f logs/app.log

# Rotate logs (add to cron)
find logs/ -name "*.log" -mtime +7 -delete
```

### Backup Strategy

Important directories to backup:
- `uploads/` - Uploaded PDF files
- `outputs/` - Generated HTML/Markdown files
- `.env` - Environment configuration (encrypted backup)

```bash
# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ outputs/ .env

# Restore backup
tar -xzf backup-20241029.tar.gz
```

### Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d
```

### Scaling Considerations

For high traffic, consider:

1. **Horizontal Scaling**: Run multiple containers behind a load balancer
2. **Caching**: Add Redis for session and TOC section caching
3. **Queue System**: Use Celery + RabbitMQ for async processing
4. **CDN**: Serve static assets via CloudFlare or AWS CloudFront
5. **Database**: Move from in-memory state to PostgreSQL or MongoDB

---

## Performance Optimization

### Current Optimizations

- ✅ FastText for instant language detection (vs Azure API calls)
- ✅ TOC section caching (eliminates 67% of Azure API calls)
- ✅ In-memory state for session data

### Future Optimizations

- Add Redis for distributed caching
- Implement result caching for repeated documents
- Use CDN for generated HTML/Markdown files
- Add database for persistent storage

---

## Cost Optimization

### Azure Document Intelligence Costs

With current optimizations:

- **Before**: 3 API calls per Arabic book (upload + HTML + Markdown)
- **After**: 1 API call per Arabic book (upload only)
- **Savings**: 67% reduction in API costs

### Estimated Costs (Azure Pricing)

- **Read API**: $1.50 per 1,000 pages
- **Example**: 100 Arabic books × 200 pages = 20,000 pages = **$30/month**
  - Without optimization: **$90/month**

### FastText Benefits

- **Zero cost** for language detection
- **Instant results** (no API latency)
- Works **offline**

---

## Troubleshooting

### Common Issues

#### 1. FastText Model Not Found

```bash
# Download manually
docker-compose exec kitabiai python scripts/validation/download_fasttext_model.py
```

#### 2. Azure API Errors

- Check endpoint URL format: `https://your-resource.cognitiveservices.azure.com/`
- Verify API key is correct (32 characters)
- Ensure Azure resource is in correct region

#### 3. Port Already in Use

```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # Use port 8080 instead
```

#### 4. Memory Issues

Increase Docker memory limit:

```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

---

## Security Best Practices

1. **Never commit secrets** - Use `.env` file and `.gitignore`
2. **Use HTTPS** - Add SSL certificate with nginx reverse proxy
3. **Rate limiting** - Add nginx or API gateway for rate limiting
4. **Input validation** - Already implemented for PDF uploads
5. **Regular updates** - Keep dependencies updated
6. **Firewall rules** - Restrict access to necessary ports only

### Adding HTTPS (Production)

Use Let's Encrypt with nginx:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/suhaJamal/KitabiAI/issues
- Email: your-email@example.com

---

## License

[Your License Here]
