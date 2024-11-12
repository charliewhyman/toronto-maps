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
  source_dir = "${var.lambda_src_dir}/get_data" 
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

resource "null_resource" "force_update" {
  triggers = {
    # Combine the MD5 hashes of both Lambda zips
    zip_file_md5 = "${filemd5(data.archive_file.get_data_lambda_payload.output_path)}-${filemd5(data.archive_file.s3_to_supabase_lambda_payload.output_path)}"
  }

  depends_on = [
    data.archive_file.get_data_lambda_payload,
    data.archive_file.s3_to_supabase_lambda_payload
  ]
}

# Create Lambda layer for Python requirements
resource "null_resource" "pip_install" {
  triggers = {
    shell_hash = "${sha256(file("${var.lambda_src_dir}//requirements.txt"))}"
  }

  provisioner "local-exec" {
    command = "python -m pip install -r ${var.lambda_src_dir}/requirements.txt -t ${var.lambda_src_dir}/layer/python --platform manylinux2014_x86_64 --only-binary=:all: --implementation cp"
  }

  
}

# zip the layer directory
data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${var.lambda_src_dir}/layer"
  output_path = "${var.lambda_src_dir}/layer.zip"
  depends_on  = [null_resource.pip_install]
}

resource "aws_lambda_layer_version" "layer" {
  layer_name          = "requirements-layer"
  filename            = data.archive_file.layer.output_path
  source_code_hash    = data.archive_file.layer.output_base64sha256
}

# Create Lambda function to get data from API
resource "aws_lambda_function" "get_data_lambda" {
  filename         = data.archive_file.get_data_lambda_payload.output_path  # Use the zipped file output
  function_name    = "get_data"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "get_data.handler" 
  runtime          = "python3.12"
  source_code_hash = "${data.archive_file.get_data_lambda_payload.output_base64sha256}"
  layers           = [aws_lambda_layer_version.layer.arn]
  timeout          = 300  # Increase timeout

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data_bucket.bucket
      TORONTO_API_URL = var.toronto_api_url
    }
  }
 depends_on = [null_resource.force_update]
}

# Create Lambda function to move data from S3 to Supabase
resource "aws_lambda_function" "s3_to_supabase_lambda" {
  filename         = data.archive_file.s3_to_supabase_lambda_payload.output_path  # Use the zipped file output
  function_name    = "s3_to_supabase"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "s3_to_supabase.handler"  
  runtime          = "python3.12"
  source_code_hash = "${data.archive_file.s3_to_supabase_lambda_payload.output_base64sha256}"

  layers           = [aws_lambda_layer_version.layer.arn,
                      # Pandas layer https://aws-sdk-pandas.readthedocs.io/en/stable/layers.html
                      "arn:aws:lambda:us-east-2:336392948345:layer:AWSSDKPandas-Python312:14"
                     ]
  timeout          = 300  # Increase timeout

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.data_bucket.bucket
      SUPABASE_URL = var.supabase_url
      SUPABASE_ACCESS_TOKEN = var.supabase_access_token
      SUPABASE_TABLE = var.supabase_table
      TORONTO_API_URL = var.toronto_api_url
    }
  }
 depends_on = [null_resource.force_update]

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
          "s3:PutObject",
          "s3:ListBucket",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"

        ],
        Effect   = "Allow",
        Resource = [
          "arn:aws:s3:::${aws_s3_bucket.data_bucket.bucket}",
          "arn:aws:s3:::${aws_s3_bucket.data_bucket.bucket}/*"
        ]
      }
    ]
  })
}

# Add EventBridge rule to run every Monday at 00:00 UTC
resource "aws_cloudwatch_event_rule" "weekly_trigger" {
  name                = "weekly-lambda-trigger"
  description         = "Triggers Lambda every Monday at 00:00 UTC"
  schedule_expression = "cron(0 0 ? * 2 *)"
}

# Set the get_data Lambda function as the target for the EventBridge rule
resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule      = aws_cloudwatch_event_rule.weekly_trigger.name
  arn       = aws_lambda_function.get_data_lambda.arn
}

# Grant permission to EventBridge to invoke the Lambda function
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_data_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_trigger.arn
}

# Grant S3 permission to invoke the s3_to_supabase_lambda function
resource "aws_lambda_permission" "allow_s3_trigger" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_to_supabase_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_bucket.arn
}

# S3 bucket event notification to trigger s3_to_supabase_lambda on new file upload to specific folder
resource "aws_s3_bucket_notification" "data_bucket_notification" {
  bucket = aws_s3_bucket.data_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_to_supabase_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "traffic-volumes-at-intersections-for-all-modes/"  # Only trigger for files in this folder
    filter_suffix       = ".csv"                                             # Optional: Limit to CSV files
  }

  depends_on = [aws_lambda_permission.allow_s3_trigger]
}

# Grant S3 permission to invoke the s3_to_supabase_lambda function
resource "aws_lambda_permission" "allow_s3_trigger" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_to_supabase_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_bucket.arn
}