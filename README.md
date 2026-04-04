# IOT Async Request Reply

Minimal demo of an asynchronous request-reply pattern with an HTTP API, background worker, PostgreSQL, RabbitMQ and a synthetic producer.

## Requirements

- Docker and Docker Compose
- Python 3.11+ if you run tests locally
- AWS credentials configured if you use the Terraform deployment

## Quick Commands

### Run unit tests

From the root of the project:

```bash
docker compose run --rm api pytest
```

### Enter the AWS CLI container

Use the compose service that already mounts the AWS credentials volume:

```bash
docker compose run --rm --entrypoint sh awscli
```

Inside that shell, check the credentials file and configure AWS if needed:

```sh
cat .aws/credentials
aws configure set aws_access_key_id YOUR_ACCESS_KEY_ID --profile default
aws configure set aws_secret_access_key YOUR_SECRET_ACCESS_KEY --profile default
aws configure set aws_session_token YOUR_SESSION_TOKEN --profile default
aws configure set region us-east-1 --profile default
```

If the session token is missing, you must add it with:

```sh
aws configure set aws_session_token YOUR_SESSION_TOKEN --profile default
```

### Edit Terraform variables

Keep the values in [terraform/variables.tf](terraform/variables.tf) aligned with the VPC, subnet, key pair and other values from your own Amazon account before applying Terraform.

### Run Terraform from the project root

```bash
docker run --rm --entrypoint /bin/sh -v "${PWD}:/workspace" -v async_aws_credentials:/root/.aws -w /workspace/terraform hashicorp/terraform:1.8.5 -lc "terraform init && terraform plan -out=project.tfplan && terraform apply project.tfplan"
```

### Destroy Terraform resources from the project root

```bash
docker run --rm --entrypoint /bin/sh -v "${PWD}:/workspace" -v async_aws_credentials:/root/.aws -w /workspace/terraform hashicorp/terraform:1.8.5 -lc "terraform init && terraform destroy -auto-approve"
```

### Useful local commands

```bash
docker compose up --build -d
docker compose logs -f api
docker compose logs -f worker
docker compose down
```
