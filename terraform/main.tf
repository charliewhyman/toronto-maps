# Create S3 bucket for storing data from API
resource "aws_s3_bucket" "data_bucket" {
  bucket = "charliewhyman-toronto-maps"
}

# Create Lambda function to get data from API
resource "aws_lambda_function" "get_data_lambda" {
  filename         = "${path.module}/lambdas/get_data.py"   
  function_name    = "get_data"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "get_data.handler"                     # Entry point for the Lambda function
  runtime          = "python3.12"
  
  source_code_hash = filebase64sha256("${path.module}/lambdas/get_data.py")  # Ensure Lambda updates when code changes

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data_bucket.bucket
    }
  }
}

# Create Lambda function to move data from S3 to Supabase
resource "aws_lambda_function" "get_data_lambda" {
  filename         = "${path.module}/lambdas/s3_to_supabase.py"   
  function_name    = "s3_to_supabase"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "s3_to_supabase.handler"                     # Entry point for the Lambda function
  runtime          = "python3.12"
  
  source_code_hash = filebase64sha256("${path.module}/lambdas/s3_to_supabase.py")  # Ensure Lambda updates when code changes

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
