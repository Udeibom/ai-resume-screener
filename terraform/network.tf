# Default VPC

data "aws_vpc" "default" {
  default = true
}


# Default Subnets

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}


# Security Group for PostgreSQL

resource "aws_security_group" "postgres" {
  name        = "resume-screener-postgres"
  description = "Allow PostgreSQL access"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "PostgreSQL"

    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"

    # For development only.
    # We'll lock this down later.
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = "AI-Resume-Screener"
  }
}


# DB Subnet Group

resource "aws_db_subnet_group" "postgres" {
  name       = "resume-screener-db-subnets"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Project = "AI-Resume-Screener"
  }
}