# ECS Cluster

resource "aws_ecs_cluster" "resume_screener" {
  name = "resume-screener-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# ECS Task Execution Role

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "resume-screener-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Action = "sts:AssumeRole"

        Effect = "Allow"

        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {

  role = aws_iam_role.ecs_task_execution_role.name

  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

}

resource "aws_iam_policy" "ecs_secrets" {
  name = "resume-screener-secrets"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "secretsmanager:GetSecretValue"
        ]

        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:resume-screener/database*",
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:resume-screener/gemini*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_secrets" {

  role = aws_iam_role.ecs_task_execution_role.name

  policy_arn = aws_iam_policy.ecs_secrets.arn
}

# CloudWatch Logs

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/resume-screener"
  retention_in_days = 7

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# ECS Task Definition

resource "aws_ecs_task_definition" "resume_screener" {

  family                   = "resume-screener"

  network_mode             = "awsvpc"

  requires_compatibilities = ["FARGATE"]

  cpu    = "256"

  memory = "512"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "resume-screener"

      image = "${aws_ecr_repository.api_repo.repository_url}:latest"

      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "arn:aws:secretsmanager:us-east-1:911195059158:secret:resume-screener/database-4FUYtG:DATABASE_URL::"
        },
        {
          name      = "GEMINI_API_KEY"
          valueFrom = "arn:aws:secretsmanager:us-east-1:911195059158:secret:resume-screener/gemini-cg14QU:GEMINI_API_KEY::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_logs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# ALB Security Group

resource "aws_security_group" "alb" {

  name        = "resume-screener-alb"

  description = "Security group for Application Load Balancer"

  vpc_id = data.aws_vpc.default.id

  ingress {

    description = "HTTP"

    from_port = 80

    to_port = 80

    protocol = "tcp"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  egress {

    from_port = 0

    to_port = 0

    protocol = "-1"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# ECS Security Group

resource "aws_security_group" "ecs_service" {

  name        = "resume-screener-ecs"

  description = "Security group for ECS service"

  vpc_id = data.aws_vpc.default.id

  ingress {
    description = "Traffic from ALB"

    from_port = 8000

    to_port = 8000

    protocol = "tcp"

    security_groups = [
      aws_security_group.alb.id
    ]
  }

  egress {

    from_port = 0

    to_port = 0

    protocol = "-1"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# Application Load Balancer

resource "aws_lb" "resume_screener" {

  name = "resume-screener-alb"

  internal = false

  load_balancer_type = "application"

  security_groups = [
    aws_security_group.alb.id
  ]

  subnets = data.aws_subnets.default.ids

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# Target Group

resource "aws_lb_target_group" "resume_screener" {

  name = "resume-screener-tg"

  port = 8000

  protocol = "HTTP"

  target_type = "ip"

  vpc_id = data.aws_vpc.default.id

  health_check {

    path = "/health"

    protocol = "HTTP"

    matcher = "200"

    interval = 30

    timeout = 5

    healthy_threshold = 2

    unhealthy_threshold = 2
  }

  tags = {
    Project = "AI-Resume-Screener"
  }
}

# HTTP Listener

resource "aws_lb_listener" "http" {

  load_balancer_arn = aws_lb.resume_screener.arn

  port = 80

  protocol = "HTTP"

  default_action {

    type = "forward"

    target_group_arn = aws_lb_target_group.resume_screener.arn

  }
}

# ECS Service

resource "aws_ecs_service" "resume_screener" {
  name            = "resume-screener-service"
  cluster         = aws_ecs_cluster.resume_screener.id
  task_definition = aws_ecs_task_definition.resume_screener.arn

  desired_count = 1
  launch_type   = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_service.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.resume_screener.arn
    container_name   = "resume-screener"
    container_port   = 8000
  }

  depends_on = [
    aws_lb_listener.http
  ]
}