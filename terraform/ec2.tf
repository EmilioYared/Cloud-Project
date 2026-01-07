# EC2 instance for RAG API
resource "aws_instance" "rag_api" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.ec2_instance_type
  key_name      = var.ssh_key_name
  
  vpc_security_group_ids = [aws_security_group.rag_api.id]
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true
  }
  
  user_data = templatefile("${path.module}/user-data.sh", {
    gemini_api_key = var.gemini_api_key
  })
  
  tags = {
    Name = "${var.project_name}-${var.environment}-ec2"
  }
}

# Elastic IP (keeps same IP on restart)
resource "aws_eip" "rag_api" {
  instance = aws_instance.rag_api.id
  domain   = "vpc"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-eip"
  }
}
