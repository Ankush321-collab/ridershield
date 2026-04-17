# Incremental AWS Deployment Guide

This guide is designed for a step-by-step implementation. You will deploy the application in distinct phases, testing and verifying the system works at the end of every phase before adding more complexity (Nginx, Auto Scaling, CI/CD).

**Prerequisite:** Since your ultimate goal is an Auto Scaling network, you must host your database and cache externally.
1. Provision **AWS RDS (PostgreSQL 16)**.
2. Provision **Amazon ElastiCache (Redis 7)**.
Note both endpoint URLs.

---

## Phase 1: Bare-Metal Deployment on a Single EC2 (Verify via IP:PORT)

In this phase, you will spin up one Ubuntu EC2 instance and run your Docker containers directly to confirm the base app works.

### 1. Launch a Single EC2 Instance
1. Go to AWS EC2 -> Launch Instance.
2. Choose **Ubuntu 24.04** and instance type `t3.medium`.
3. Open ports **22 (SSH)**, **3000 (Admin Dashboard)**, and **8000 (Backend API)** in the Security Group.

### 2. Install Docker and Clone Code
SSH into your instance and run:
```bash
# Install Docker Core
sudo apt-get update -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker

# Clone your code
git clone https://github.com/Ankush321-collab/ridershield.git
cd ridershield
```

### 3. Setup Environment Variables and Run
**Note on Environment Variables:** You might have multiple environment files locally (`backend/.env`, `admin/.env`, etc.). **You do NOT need to recreate all of these on EC2.** Docker Compose will read a single, unified `.env` file at the root folder and automatically distribute the correct variables to the correct containers through the `docker-compose.yml` environment mappings.

Create a single unified `.env` file at the project root referencing your RDS and ElastiCache instances:
```bash
nano .env
```
Fill it with your database variables, GitHub tokens, and API keys:
```env
DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/zylo?schema=public"
REDIS_HOST=your-elasticache-endpoint
REDIS_PORT=6379
BACKEND_URL=http://localhost:8000
ADMIN_URL=http://<EC2-PUBLIC-IP>:3000
# Add your other tokens...
```

Run Docker Compose:
```bash
docker compose up --build -d
```

### 🎯 Verification (Phase 1)
Visit `http://<EC2-PUBLIC-IP>:3000` in your browser. Your admin dashboard should load, and the backend connections to RDS/ElastiCache should be working flawlessly. Do not proceed until this step is verified.

---

## Phase 2: Add Nginx Reverse Proxy (Verify via IP:80)

Using ports like 3000/8000 isn't scalable. In this phase, we add Nginx to act as a reverse proxy on that same machine.

### 1. Configure Nginx
```bash
sudo apt-get install -y nginx
sudo rm /etc/nginx/sites-enabled/default
sudo nano /etc/nginx/sites-available/app
```

Add the following config:
```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_addrs;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
    }

    location /docs {
        proxy_pass http://localhost:8000/docs;
    }

    location /redoc {
        proxy_pass http://localhost:8000/redoc;
    }
}
```

Enable it:
```bash
sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### 🎯 Verification (Phase 2)
In AWS, modify your EC2 Security Group to allow inbound traffic on **Port 80 (HTTP)**. 
Now visit `http://<EC2-PUBLIC-IP>` (Without the `:3000` port). The app should load seamlessly, entirely proxied through Nginx.

---

## Phase 3: Auto Scaling & Load Balancing (Verify via ALB)

Now we will turn your working Stage 2 machine into a master "Template" for Auto Scaling. Whenever AWS needs more power, it will clone this exact machine.

### 1. Prepare Secrets for Auto Scaling
Store your `.env` contents securely in AWS Systems Manager (SSM) instead of leaving them on disk.
1. Go to AWS **Systems Manager** -> **Parameter Store** -> **Create parameter**.
2. Name it `/ridershield/prod/env`, set Type to **SecureString**, and paste your `.env` text from Phase 1.

### 2. Create the AMI (Golden Image)
1. Go back to your EC2 console, select your working instance. 
2. Choose **Actions** -> **Image and templates** -> **Create image**. Name it `Ridershield-Base-Image`.

### 3. Create a Launch Template and ASG
1. Go to **EC2** -> **Launch Templates** -> Create.
2. Select your `Ridershield-Base-Image`.
3. Add a **User Data** script. This runs autonomously every time a new instance boots to grab the latest `.env` config from Parameter Store and start Docker:
```bash
#!/bin/bash
sudo su - ubuntu
cd /home/ubuntu/ridershield

# Fetch secrets from SSM
aws ssm get-parameter --name "/ridershield/prod/env" --with-decryption --query "Parameter.Value" --output text > .env --region us-east-1

# Start Docker containers
docker compose pull
docker compose up -d
```

### 4. Create the Load Balancer
1. Create a **Target Group** (type: instance) pointing to port 80.
2. Create an **Application Load Balancer (ALB)** listening on Port 80, tied to the Target Group.
3. Create an **Auto Scaling Group (ASG)** using your Launch Template, setting Minimum/Maximum capacity to 2. Attach it to your Load Balancer's Target Group.

### 🎯 Verification (Phase 3)
Find the **DNS Name** of your Application Load Balancer in the EC2 console (e.g., `my-alb-12345.us-east-1.elb.amazonaws.com`).
Visit `http://<ALB-DNS-NAME>`. The application should be visible, and AWS will automatically distribute traffic to the EC2 instances in the background.

---

## Phase 4: CI/CD Setup with GitHub Actions (Verify via git push)

To achieve automatic deployments on future code updates, we utilize AWS Elastic Container Registry (ECR) instead of building the repository natively on instances.

### 1. Set Up GitHub Secrets
Go to AWS IAM. Create a user with `AmazonEC2ContainerRegistryPowerUser` and `AmazonSSMFullAccess`.
In your GitHub repo, add the following secrets:
* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`
* `AWS_ACCOUNT_ID`

### 2. Create the ECR Repositories
In the AWS Console, visit ECR and create exactly 2 empty repositories:
`ridershield-backend` and `ridershield-admin`.

### 3. Configure GitHub Workflow
Create a file at `.github/workflows/deploy.yml` in your project:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches:
      - main

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and Push Images
        run: |
          docker build -t $ECR_REGISTRY/ridershield-backend:latest -f backend/Dockerfile.prod .
          docker push $ECR_REGISTRY/ridershield-backend:latest
          
          docker build -t $ECR_REGISTRY/ridershield-admin:latest -f admin/Dockerfile.prod .
          docker push $ECR_REGISTRY/ridershield-admin:latest

  deploy-to-asg:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Trigger Rolling Deployment via SSM
        run: |
          aws ssm send-command \
            --targets "Key=tag:aws:autoscaling:groupName,Values=YourAutoScalingGroupName" \
            --document-name "AWS-RunShellScript" \
            --parameters 'commands=["cd /home/ubuntu/ridershield", "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin '${{ env.ECR_REGISTRY }}'", "docker compose pull", "docker compose up -d"]'
```

### 🎯 Verification (Phase 4)
Make a visible change to your Admin app (like modifying a text header) and push to the `main` branch. 
Monitor the **GitHub Actions** tab to ensure the runner builds and pushes the image. Once complete, wait 60 seconds and refresh your Application Load Balancer URL. You should see your new changes live across all Auto Scaled instances simultaneously.
ultaneously.
