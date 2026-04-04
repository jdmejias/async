output "rabbitmq_public_ip" {
  value = aws_instance.rabbitmq.public_ip
  description = "IP pública del servidor RabbitMQ"
}

output "api_public_ip" {
  value = [for instance in aws_instance.api_server : instance.public_ip]
  description = "IPs públicas de las instancias API"
}

output "api_load_balancer_ips" {
  value       = [for eip in aws_eip.api_lb : eip.public_ip]
  description = "IPs públicas fijas del Network Load Balancer"
}

output "api_load_balancer_dns_name" {
  value       = aws_lb.api_lb.dns_name
  description = "DNS del Network Load Balancer"
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
