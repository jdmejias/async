# 1. RabbitMQ EC2
resource "aws_instance" "rabbitmq" {
  ami               = var.ami_id
  instance_type     = var.instance_type
  key_name          = var.key_name
  subnet_id         = var.subnet_id
  vpc_security_group_ids = [aws_security_group.rabbitmq_sg.id]
  user_data         = file("${path.module}/install_rabbitmq.sh")

  tags = {
    Name    = "RabbitMQ-Server"
    Role    = "MessageBroker"
  }
}

# 2. Docker / API Rest EC2
resource "aws_instance" "api_server" {
  ami               = var.ami_id
  instance_type     = var.instance_type
  key_name          = var.key_name
  subnet_id         = var.subnet_id
  vpc_security_group_ids = [aws_security_group.api_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ssm_read_profile.name
  user_data         = templatefile("${path.module}/install_api.sh", {
    repo_url = var.repo_url
  })

  tags = {
    Name    = "Docker-API-Server"
    Role    = "BackendAPI"
  }
}

# 3. Worker EC2
resource "aws_instance" "worker" {
  ami               = var.ami_id
  instance_type     = var.instance_type
  key_name          = var.key_name
  subnet_id         = var.subnet_id
  vpc_security_group_ids = [aws_security_group.worker_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ssm_read_profile.name
  user_data         = templatefile("${path.module}/install_worker.sh", {
    repo_url = var.repo_url
  })

  tags = {
    Name    = "Worker-Server"
    Role    = "AsyncWorker"
  }
}

# 4. PostgreSQL EC2
resource "aws_instance" "postgres" {
  ami               = var.ami_id
  instance_type     = var.instance_type
  key_name          = var.key_name
  subnet_id         = var.subnet_id
  vpc_security_group_ids = [aws_security_group.postgres_sg.id]
  user_data         = file("${path.module}/install_postgres.sh")

  tags = {
    Name    = "Postgres-Server"
    Role    = "Database"
  }
}

# 5. Synthetic Producer EC2
resource "aws_instance" "synthetic_producer" {
  ami               = var.ami_id
  instance_type     = var.instance_type
  key_name          = var.key_name
  subnet_id         = var.subnet_id
  vpc_security_group_ids = [aws_security_group.worker_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ssm_read_profile.name
  user_data         = templatefile("${path.module}/install_synthetic_producer.sh", {
    repo_url = var.repo_url
  })

  tags = {
    Name    = "Synthetic-Producer-Server"
    Role    = "SyntheticProducer"
  }
}

# ==========================================
# AWS Systems Manager Parameter Store
# ==========================================

resource "aws_ssm_parameter" "rabbitmq_ip" {
  name  = "/message-queue/dev/rabbitmq/public_ip"
  type  = "String"
  value = aws_instance.rabbitmq.public_ip
  description = "Public IP for RabbitMQ Server"
}

resource "aws_ssm_parameter" "api_ip" {
  name  = "/message-queue/dev/api/public_ip"
  type  = "String"
  value = aws_instance.api_server.public_ip
  description = "Public IP for Docker API Server"
}

resource "aws_ssm_parameter" "worker_ip" {
  name  = "/message-queue/dev/worker/public_ip"
  type  = "String"
  value = aws_instance.worker.public_ip
  description = "Public IP for Async Worker Server"
}

resource "aws_ssm_parameter" "postgres_ip" {
  name        = "/message-queue/dev/postgres/public_ip"
  type        = "String"
  value       = aws_instance.postgres.public_ip
  description = "Public IP for PostgreSQL Server"
}

resource "aws_ssm_parameter" "synthetic_producer_ip" {
  name        = "/message-queue/dev/synthetic-producer/public_ip"
  type        = "String"
  value       = aws_instance.synthetic_producer.public_ip
  description = "Public IP for Synthetic Producer Server"
}

resource "aws_iam_role" "ec2_ssm_read_role" {
  name = "ec2-ssm-read-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_ssm_read_attach" {
  role       = aws_iam_role.ec2_ssm_read_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ssm_read_profile" {
  name = "ec2-ssm-read-profile"
  role = aws_iam_role.ec2_ssm_read_role.name
}

