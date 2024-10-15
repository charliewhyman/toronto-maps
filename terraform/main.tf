# Create S3 bucket for storing data from API
resource "aws_s3_bucket" "data_bucket" {
  bucket = "charliewhyman-toronto-maps"
}

# Variables for source and output directories
variable "lambda_src_dir" {
  description = "Source directory for Lambda functions"
  type        = string
}

variable "lambda_payload_dir" {
  description = "Output directory for lambda payloads"
  type        = string
}

# Data source to create a zip file for get_data lambda
data "archive_file" "get_data_lambda_payload" {
  type        = "zip"
  source_dir = "${var.lambda_src_dir}/get_data"  # Adjust filename as necessary
  output_path = "${var.lambda_payload_dir}/get_data_payload.zip"
  excludes    = [
    "venv",
    "__pycache__"
  ]
}

# Data source to create a zip file for s3_to_supabase lambda
data "archive_file" "s3_to_supabase_lambda_payload" {
  type        = "zip"
  source_dir = "${var.lambda_src_dir}/s3_to_supabase"  # Adjust filename as necessary
  output_path = "${var.lambda_payload_dir}/s3_to_supabase_payload.zip"
  excludes    = [
    "venv",
    "__pycache__"
  ]
}

# Create Lambda function to get data from API
resource "aws_lambda_function" "get_data_lambda" {
  filename         = data.archive_file.get_data_lambda_payload.output_path  # Use the zipped file output
  function_name    = "get_data"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "get_data.handler"  # Adjust this according to your function's handler
  runtime          = "python3.12"

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data_bucket.bucket
    }
  }
}

# Create Lambda function to move data from S3 to Supabase
resource "aws_lambda_function" "s3_to_supabase_lambda" {
  filename         = data.archive_file.s3_to_supabase_lambda_payload.output_path  # Use the zipped file output
  function_name    = "s3_to_supabase"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "s3_to_supabase.handler"  # Adjust this according to your function's handler
  runtime          = "python3.12"

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data_bucket.bucket
    }
  }
}

# Create IAM role for Lambda function
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attach policy to IAM role for Lambda function with S3 and logging permissions
resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"

        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}
