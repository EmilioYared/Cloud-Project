variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"  # Your region
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "rag-chatbot"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.small"
}

variable "ssh_key_name" {
  description = "Name of existing EC2 key pair"
  type        = string
}

variable "my_ip" {
  description = "Your IP address for SSH access (e.g., 1.2.3.4/32)"
  type        = string
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}
