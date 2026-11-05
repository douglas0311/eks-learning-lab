locals {
  name          = "rag-interview-lab-web"
  function_name = module.query.function_name
  function_arn  = module.query.function_arn
}
resource "aws_s3_bucket" "site" { bucket = "${local.name}-490224159848" }
resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "site" {
  bucket = aws_s3_bucket.site.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_object" "index" {
  bucket        = aws_s3_bucket.site.id
  key           = "index.html"
  source        = "${path.module}/site/index.html"
  source_hash   = filemd5("${path.module}/site/index.html")
  content_type  = "text/html; charset=utf-8"
  cache_control = "max-age=60"
}
resource "aws_api_gateway_rest_api" "query" {
  name = local.name
  endpoint_configuration { types = ["REGIONAL"] }
  body = jsonencode({
    openapi = "3.0.1"
    info    = { title = local.name, version = "1.0" }
    paths = {
      "/api/query" = {
        post = {
          responses = { "200" = { description = "Query result" } }
          "x-amazon-apigateway-integration" = {
            type                = "aws"
            httpMethod          = "POST"
            uri                 = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/${local.function_arn}/invocations"
            passthroughBehavior = "never"
            requestTemplates    = { "application/json" = "$input.body" }
            timeoutInMillis     = 29000
            responses = {
              default = {
                statusCode        = "200"
                responseTemplates = { "application/json" = "#set($result = $input.path('$'))\n#set($context.responseOverride.status = $result.statusCode)\n$input.json('$')" }
              }
            }
          }
        }
      }
    }
  })
}
resource "aws_api_gateway_deployment" "query" {
  rest_api_id = aws_api_gateway_rest_api.query.id
  triggers    = { redeployment = sha1(aws_api_gateway_rest_api.query.body) }
  lifecycle { create_before_destroy = true }
}
resource "aws_api_gateway_stage" "query" {
  rest_api_id   = aws_api_gateway_rest_api.query.id
  deployment_id = aws_api_gateway_deployment.query.id
  stage_name    = "lab"
}
resource "aws_lambda_permission" "query_api" {
  statement_id  = "AllowKnowledgeBaseWebAPI"
  action        = "lambda:InvokeFunction"
  function_name = local.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.query.execution_arn}/lab/POST/api/query"
}
data "aws_cloudfront_cache_policy" "static" { name = "Managed-CachingOptimized" }
data "aws_cloudfront_cache_policy" "api" { name = "Managed-CachingDisabled" }
data "aws_cloudfront_origin_request_policy" "api" { name = "Managed-AllViewerExceptHostHeader" }
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = local.name
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}
resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  wait_for_deployment = true
  origin {
    origin_id                = "static"
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }
  origin {
    origin_id   = "query"
    domain_name = "${aws_api_gateway_rest_api.query.id}.execute-api.us-east-1.amazonaws.com"
    origin_path = "/${aws_api_gateway_stage.query.stage_name}"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  default_cache_behavior {
    target_origin_id       = "static"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.static.id
    compress               = true
  }
  ordered_cache_behavior {
    path_pattern             = "/api/query"
    target_origin_id         = "query"
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.api.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.api.id
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  viewer_certificate { cloudfront_default_certificate = true }
}
resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.site.arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.web.arn } }
    }]
  })
}
output "website_url" { value = "https://${aws_cloudfront_distribution.web.domain_name}" }
output "distribution_id" { value = aws_cloudfront_distribution.web.id }
