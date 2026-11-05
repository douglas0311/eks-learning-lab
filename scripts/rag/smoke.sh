#!/usr/bin/env bash
set -euo pipefail
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export RAG_SMOKE_PDF="$TMP/smoke.pdf"
python - <<'PY'
import os
from reportlab.pdfgen import canvas
c=canvas.Canvas(os.environ['RAG_SMOKE_PDF'])
c.drawString(50,750,'RAG smoke test: The fictional project Cedar has recovery code CEDAR-731.')
c.save()
PY
BUCKET=$(terraform -chdir=infra/rag output -raw source_bucket)
URL=$(terraform -chdir=infra/rag output -raw website_url)
aws s3 cp "$TMP/smoke.pdf" "s3://$BUCKET/smoke/pipeline.pdf" --only-show-errors
# Invoke explicitly as well: source reindexing must work after runtime recreation.
# Deterministic keys in the ingestor make duplicate S3 delivery idempotent for this fixture.
printf '{"Records":[{"s3":{"bucket":{"name":"%s"},"object":{"key":"smoke/pipeline.pdf"}}}]}' "$BUCKET" > "$TMP/event.json"
aws lambda invoke --function-name rag-interview-lab-ingestor --cli-binary-format raw-in-base64-out --payload "file://$TMP/event.json" "$TMP/ingest.json" > "$TMP/invoke.json"
jq -e 'has("FunctionError") | not' "$TMP/invoke.json"
jq -e '.statusCode == 200 and (.body | fromjson | .results | length > 0 and all(.status == "ok"))' "$TMP/ingest.json"
curl --fail --silent --show-error "$URL/" > "$TMP/index.html"
grep -q 'Engineering Knowledge Base' "$TMP/index.html"
# Bounded retries are read-only queries; never retry an infrastructure apply blindly.
for attempt in 1 2 3 4 5 6; do
  CODE=$(curl --silent --show-error --max-time 40 -o "$TMP/answer.json" -w '%{http_code}' "$URL/api/query" -H 'Content-Type: application/json' -d '{"question":"What is the recovery code for fictional project Cedar?"}')
  if [ "$CODE" = 200 ] && jq -e '.statusCode == 200 and .count > 0 and .generation_status == "completed" and (.answer | contains("CEDAR-731"))' "$TMP/answer.json" > /dev/null; then
    echo "RAG smoke passed: website, retrieval and grounded fixture answer. $URL" >> "$GITHUB_STEP_SUMMARY"
    exit 0
  fi
  sleep 10
done
echo 'Smoke failed: inspect query/ingestor CloudWatch logs. Runtime remains deployed.' >&2
exit 1
