output "alb_dns_name" {
  description = "ALB DNS name to access the API"
  value       = module.alb.alb_dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing images"
  value       = module.ecr.repository_url
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache endpoint"
  value       = module.elasticache.endpoint
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "s3_bucket_id" {
  description = "S3 artifacts bucket ID"
  value       = module.s3.bucket_id
}
