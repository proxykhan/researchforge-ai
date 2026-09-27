output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "api_service_name" {
  description = "API ECS service name"
  value       = aws_ecs_service.api.name
}

output "worker_service_name" {
  description = "Worker ECS service name"
  value       = aws_ecs_service.worker.name
}

output "task_role_arn" {
  description = "ECS task role ARN (for attaching additional policies)"
  value       = aws_iam_role.task.arn
}

output "task_role_name" {
  description = "ECS task role name"
  value       = aws_iam_role.task.name
}
