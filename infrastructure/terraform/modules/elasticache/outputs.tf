output "endpoint" {
  description = "ElastiCache primary endpoint"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "port" {
  description = "ElastiCache port"
  value       = aws_elasticache_cluster.main.port
}

output "redis_url" {
  description = "Redis connection URL for the application"
  value       = "rediss://${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.port}/0"
}

output "security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}
