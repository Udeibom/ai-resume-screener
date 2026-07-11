resource "aws_db_instance" "postgres" {
  identifier = "resume-screener-db"

  engine         = "postgres"
  engine_version = "16"

  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "resume_screener"
  username = "postgres"
  password = var.db_password

  publicly_accessible = true

  db_subnet_group_name = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [
    aws_security_group.postgres.id
  ]

  backup_retention_period = 0

  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Project = "AI-Resume-Screener"
  }
}