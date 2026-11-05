terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

locals {
  generation_profile_arn = "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:inference-profile/${var.generation_model_id}"
  vector_index_arn       = "arn:aws:s3vectors:${var.aws_region}:${var.aws_account_id}:bucket/${var.vector_bucket_name}/index/${var.vector_index_name}"
}

# Same handler-only packaging as ingestion; uses the Lambda Python runtime SDK.
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/function/handler.py"
  output_path = "${path.module}/function/handler.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    sid     = "AllowLambdaAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_execution" {
  name               = "${var.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags = {
    Name        = "${var.function_name}-role"
    Environment = var.environment
  }
}

data "aws_iam_policy_document" "lambda_runtime" {
  statement {
    sid       = "WriteQueryLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:log-stream:*"]
  }
  statement {
    sid       = "InvokeTitanEmbeddings"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"]
    resources = ["arn:aws:bedrock:${var.aws_region}::foundation-model/${var.embedding_model_id}"]
  }
  statement {
    sid       = "InvokeNovaMicroProfile"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.generation_profile_arn]
  }
  statement {
    sid     = "InvokeNovaMicroThroughProfile"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel"]
    # Exact destinations returned by GetInferenceProfile on 2026-09-23.
    resources = [
      "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0",
      "arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-micro-v1:0",
      "arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-micro-v1:0",
    ]
    condition {
      test     = "StringEquals"
      variable = "bedrock:InferenceProfileArn"
      values   = [local.generation_profile_arn]
    }
  }
  statement {
    sid    = "QueryExistingIndexWithMetadata"
    effect = "Allow"
    # GetVectors is required by QueryVectors when returnMetadata is true.
    actions   = ["s3vectors:QueryVectors", "s3vectors:GetVectors"]
    resources = [local.vector_index_arn]
  }
}

resource "aws_iam_role_policy" "lambda_runtime" {
  name   = "${var.function_name}-runtime-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_runtime.json
}

resource "aws_lambda_function" "query" {
  function_name    = var.function_name
  description      = "Phase 5B: Titan retrieval with grounded Nova Micro answers"
  role             = aws_iam_role.lambda_execution.arn
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  handler          = "handler.handler"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      VECTOR_BUCKET_NAME    = var.vector_bucket_name
      VECTOR_INDEX_NAME     = var.vector_index_name
      EMBEDDING_MODEL_ID    = var.embedding_model_id
      EMBEDDING_DIMENSIONS  = tostring(var.embedding_dimensions)
      TOP_K                 = tostring(var.top_k)
      GENERATION_MODEL_ID   = var.generation_model_id
      GENERATION_MAX_TOKENS = tostring(var.generation_max_tokens)
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda, aws_iam_role_policy.lambda_runtime]
}
