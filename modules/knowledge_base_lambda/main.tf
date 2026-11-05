# -----------------------------------------------------------------------
# Phase 3 / Phase 4 — Knowledge Base Lambda Module
#
# Resources managed here:
#   - CloudWatch Log Group (explicit, with retention)
#   - IAM execution role + inline runtime policy
#     Phase 4 additions: Bedrock InvokeModel, S3 Vectors PutVectors/GetIndex
#   - Lambda deployment package (archive_file — handler.py only)
#   - Lambda layer (pypdf — built externally, referenced via local ZIP)
#   - Lambda function (Terraform-managed)
#   - Lambda resource-based permission (S3 → Lambda invoke)
#   - S3 bucket notification (ObjectCreated, .pdf suffix)
# -----------------------------------------------------------------------

# -----------------------------------------------------------------------
# Deployment package
# Zips handler.py from the function/ subdirectory relative to this module.
# The archive is written to the same directory and ignored by .gitignore.
# -----------------------------------------------------------------------
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/function/handler.py"
  output_path = "${path.module}/function/handler.zip"
}

# -----------------------------------------------------------------------
# Lambda layer — pypdf (Phase 4)
#
# pypdf is a pure-Python PDF extraction library with no native dependencies.
# It is packaged into a Lambda layer so handler.py stays small and the
# dependency is cached across deployments.
#
# Build the layer ZIP before terraform apply:
#
#   mkdir -p /tmp/pypdf-layer/python
#   pip install pypdf==4.3.1 -t /tmp/pypdf-layer/python --quiet
#   cd /tmp/pypdf-layer && zip -r9 pypdf-layer.zip python/
#   cp /tmp/pypdf-layer/pypdf-layer.zip \
#      <repo>/modules/knowledge_base_lambda/layer/pypdf-layer.zip
#
# The ZIP path is controlled by var.layer_zip_path so the root module
# can point to the built artifact.
# -----------------------------------------------------------------------
resource "aws_lambda_layer_version" "pypdf" {
  layer_name          = "${var.function_name}-pypdf"
  filename            = var.layer_zip_path
  source_code_hash    = filebase64sha256(var.layer_zip_path)
  compatible_runtimes = ["python3.12"]
  description         = "pypdf 4.3.1 — pure-Python PDF text extraction for Phase 4"
}

# -----------------------------------------------------------------------
# CloudWatch Log Group
# Created explicitly so retention is enforced from the first invocation.
# Lambda would auto-create the group, but without a retention policy.
#
# The null_resource trigger on iam_policy_attachment_ids ensures this
# resource is not created until the IAM policy attachments are confirmed.
# IAM is eventually consistent — without this gate the logs:CreateLogGroup
# call races ahead of policy propagation and fails with AccessDenied.
# -----------------------------------------------------------------------

# Gate resource: becomes tainted whenever attachment IDs change, forcing
# dependents to re-evaluate after IAM propagation.
resource "terraform_data" "iam_ready" {
  input = var.iam_policy_attachment_ids
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  # ignore_changes on tags_all prevents the provider from calling
  # logs:TagResource atomically inside CreateLogGroup when default_tags
  # are present. That inline tag call consistently races against IAM
  # propagation and fails with AccessDeniedException. Tags are still
  # applied by the provider in a separate post-create pass on subsequent
  # plans once propagation has settled.
  lifecycle {
    ignore_changes = [tags_all]
  }

  depends_on = [terraform_data.iam_ready]
}

# -----------------------------------------------------------------------
# Lambda execution role
# Trust policy allows only lambda.amazonaws.com to assume this role.
# -----------------------------------------------------------------------
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

# -----------------------------------------------------------------------
# Lambda runtime IAM policy (inline)
#
# Permissions are split by resource type to satisfy least-privilege:
#   - S3 object-level:  GetObject, GetObjectAttributes (object ARN /*  )
#   - CWL log group:    CreateLogStream, PutLogEvents  (log group ARN :*)
#   - CWL account:      CreateLogGroup                 (account-level  )
#
# Intentionally excluded:
#   s3:DeleteObject, s3:DeleteObjectVersion, s3:PutObject,
#   s3:ListBucket (not needed at runtime), bedrock:*, wildcard actions.
# -----------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_runtime" {
  # S3 — object-level read only (source knowledge bucket)
  statement {
    sid    = "S3ReadObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectAttributes",
    ]
    resources = ["${var.source_bucket_arn}/*"]
  }

  # CloudWatch Logs — write to this function's log group
  statement {
    sid    = "CWLWriteLogEvents"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }

  # CloudWatch Logs — allow the runtime to create the log group
  # (guards against race between first invocation and Terraform apply)
  statement {
    sid    = "CWLCreateLogGroup"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"]
  }

  # Bedrock — invoke the embedding model only (Phase 4)
  # Resource ARN format for foundation models does not include account ID.
  statement {
    sid    = "BedrockInvokeEmbeddingModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
    ]
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.embedding_model_id}",
    ]
  }

  # S3 Vectors — write vectors and read index config (Phase 4)
  # Index-level ARN: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
  statement {
    sid    = "S3VectorsPutVectors"
    effect = "Allow"
    actions = [
      "s3vectors:PutVectors",
      # GetIndex lets the handler verify the index exists on cold start
      # and is also called by the AWS SDK on some write paths.
      "s3vectors:GetIndex",
    ]
    resources = [
      "arn:aws:s3vectors:${var.aws_region}:${var.aws_account_id}:bucket/${var.vector_bucket_name}/index/${var.vector_index_name}",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_runtime" {
  name   = "${var.function_name}-runtime-policy"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_runtime.json
}

# -----------------------------------------------------------------------
# Lambda function — managed so a clean runtime can be recreated by Terraform.
# Preserve the last deployed ingestion settings and existing package/layer.
# -----------------------------------------------------------------------
resource "aws_lambda_function" "ingestor" {
  function_name    = var.function_name
  description      = "Phase 3: receives S3 ObjectCreated events and logs document metadata."
  role             = aws_iam_role.lambda_execution.arn
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  handler          = "handler.handler"
  memory_size      = 128
  timeout          = 300
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  layers           = [aws_lambda_layer_version.pypdf.arn]

  environment {
    variables = {
      VECTOR_BUCKET_NAME   = var.vector_bucket_name
      VECTOR_INDEX_NAME    = var.vector_index_name
      EMBEDDING_MODEL_ID   = var.embedding_model_id
      EMBEDDING_DIMENSIONS = tostring(var.embedding_dimensions)
      CHUNK_SIZE           = "800"
      CHUNK_OVERLAP        = "200"
    }
  }

  tags = {
    Name        = var.function_name
    Environment = var.environment
    Phase       = "3"
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda_runtime,
    aws_lambda_layer_version.pypdf,
    terraform_data.iam_ready,
  ]
}

# -----------------------------------------------------------------------
# Lambda resource-based permission
# Grants s3.amazonaws.com the right to invoke this specific function
# from this specific bucket only.  SourceAccount prevents confused-deputy
# attacks from other accounts' buckets sharing the same event pipeline.
# -----------------------------------------------------------------------
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id   = "AllowS3Invoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.ingestor.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = var.source_bucket_arn
  source_account = var.aws_account_id
}

# -----------------------------------------------------------------------
# S3 bucket notification
# Triggers Lambda on every ObjectCreated event for .pdf objects.
# aws_s3_bucket_notification is atomic — it replaces the full notification
# config for the bucket. Only one such resource should manage this bucket.
# -----------------------------------------------------------------------
resource "aws_s3_bucket_notification" "pdf_upload" {
  bucket = var.source_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingestor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".pdf"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
