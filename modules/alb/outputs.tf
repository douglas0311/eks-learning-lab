output "target_group_arn" {
  description = "ARN of the application Target Group."
  value       = aws_lb_target_group.application.arn
}

output "application_security_group_id" {
  description = "ID of the application Security Group."
  value       = aws_security_group.application.id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer."
  value       = aws_lb.this.dns_name
}