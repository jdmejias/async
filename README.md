# IOT Async Request Reply

Minimal demo of an asynchronous request-reply pattern with an HTTP API, background worker, PostgreSQL, RabbitMQ and a synthetic producer.
The API now runs on two EC2 instances behind a Network Load Balancer with static IPs.

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

Inside your AWS browser lab console get the credentials:

```sh
cat .aws/credentials
```

Also get the vpc info:

```sh
aws ec2 describe-subnets --query "Subnets[*].[SubnetId, VpcId, AvailabilityZone]" --output text
```

Inside your terminal in your computer, check the credentials file and configure AWS if needed:

```sh
aws configure 
```

If the session token is missing, you must add it with:

```sh
aws configure set aws_session_token YOUR_SESSION_TOKEN --profile default
```

### Edit Terraform variables

Keep the values in [terraform/variables.tf](terraform/variables.tf) aligned with the VPC, the two public subnets for `us-east-1a` and `us-east-1b`, the key pair and the rest of the values from your Amazon account before applying Terraform.

The load balancer exposes static public IPs through the outputs in Terraform. Use one of those IPs in the browser as `http://<load-balancer-ip>/docs`.

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
