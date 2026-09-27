output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs (for ALB)"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (for ECS, RDS, ElastiCache)"
  value       = aws_subnet.private[*].id
}

output "availability_zones" {
  description = "Availability zones in use"
  value       = local.azs
}
