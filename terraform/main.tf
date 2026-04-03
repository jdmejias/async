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
  user_data         = templatefile("${path.module}/install_api.sh", {
    repo_url    = var.repo_url
    rabbitmq_ip = aws_instance.rabbitmq.public_ip
    postgres_ip = aws_instance.postgres.public_ip
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
  user_data         = templatefile("${path.module}/install_worker.sh", {
    repo_url    = var.repo_url
    rabbitmq_ip = aws_instance.rabbitmq.public_ip
    postgres_ip = aws_instance.postgres.public_ip
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
  user_data         = templatefile("${path.module}/install_synthetic_producer.sh", {
    repo_url = var.repo_url
    api_ip   = aws_instance.api_server.public_ip
  })

  tags = {
    Name    = "Synthetic-Producer-Server"
    Role    = "SyntheticProducer"
  }
}


