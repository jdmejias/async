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
  count                  = 2
  ami               = var.ami_id
  instance_type     = var.instance_type
  key_name          = var.key_name
  subnet_id         = count.index == 0 ? var.api_subnet_a_id : var.api_subnet_b_id
  vpc_security_group_ids = [aws_security_group.api_sg.id]
  associate_public_ip_address = true
  user_data         = templatefile("${path.module}/install_api.sh", {
    repo_url    = var.repo_url
    rabbitmq_ip = aws_instance.rabbitmq.public_ip
    postgres_ip = aws_instance.postgres.public_ip
  })

  tags = {
    Name    = "Docker-API-Server-${count.index + 1}"
    Role    = "BackendAPI"
  }
}

resource "aws_eip" "api_lb" {
  count  = 2
  domain = "vpc"

  tags = {
    Name = "api-lb-eip-${count.index + 1}"
  }
}

resource "aws_lb" "api_lb" {
  name                            = "async-api-nlb"
  load_balancer_type              = "network"
  enable_cross_zone_load_balancing = true

  subnet_mapping {
    subnet_id     = var.api_subnet_a_id
    allocation_id = aws_eip.api_lb[0].id
  }

  subnet_mapping {
    subnet_id     = var.api_subnet_b_id
    allocation_id = aws_eip.api_lb[1].id
  }

  tags = {
    Name = "async-api-nlb"
  }
}

resource "aws_lb_target_group" "api_tg" {
  name        = "async-api-tg"
  port        = 8000
  protocol    = "TCP"
  target_type = "instance"
  vpc_id      = var.vpc_id

  health_check {
    protocol = "TCP"
    port     = "8000"
  }
}

resource "aws_lb_listener" "api_listener" {
  load_balancer_arn = aws_lb.api_lb.arn
  port              = 80
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_tg.arn
  }
}

resource "aws_lb_target_group_attachment" "api_attachment" {
  count            = 2
  target_group_arn = aws_lb_target_group.api_tg.arn
  target_id        = aws_instance.api_server[count.index].id
  port             = 8000
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
    repo_url     = var.repo_url
    api_base_url = "http://${aws_lb.api_lb.dns_name}"
  })

  tags = {
    Name    = "Synthetic-Producer-Server"
    Role    = "SyntheticProducer"
  }
}


