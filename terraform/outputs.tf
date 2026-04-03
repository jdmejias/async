output "rabbitmq_public_ip" {
  value = aws_instance.rabbitmq.public_ip
  description = "IP pública del servidor RabbitMQ"
}

output "api_public_ip" {
  value = aws_instance.api_server.public_ip
  description = "IP pública del servidor API (Docker)"
}

output "worker_public_ip" {
  value = aws_instance.worker.public_ip
  description = "IP pública del servidor Worker"
}

output "postgres_public_ip" {
  value = aws_instance.postgres.public_ip
  description = "IP pública del servidor PostgreSQL"
}

output "synthetic_producer_public_ip" {
  value = aws_instance.synthetic_producer.public_ip
  description = "IP pública del servidor Synthetic Producer"
}
