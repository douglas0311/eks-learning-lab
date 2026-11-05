"""Read-only IAM simulation. Does not install permissions or prove SCP/service availability."""
import json
import subprocess
from pathlib import Path
import tempfile

role='arn:aws:iam::490224159848:role/TerraformSRELabGitHubActionsRole'
policy=Path('iam/rag-actions-additions.json').read_text()
cases=[('s3:GetReplicationConfiguration','arn:aws:s3:::rag-interview-lab-knowledge-source'),
 ('lambda:CreateFunction','arn:aws:lambda:us-east-1:490224159848:function:rag-interview-lab-query'),
 ('s3vectors:CreateVectorBucket','arn:aws:s3vectors:us-east-1:490224159848:bucket/rag-interview-lab-vectors'),
 ('s3:PutObject','arn:aws:s3:::douglas-sre-s3-terraform-state/rag-interview/terraform.tfstate'),
 ('s3:DeleteObject','arn:aws:s3:::douglas-sre-s3-terraform-state/rag-interview/terraform.tfstate.tflock'),
 ('cloudfront:CreateDistribution','*'),
 ('apigateway:POST','arn:aws:apigateway:us-east-1::/restapis'),
 ('iam:PassRole','arn:aws:iam::490224159848:role/rag-interview-lab-query-role')]
failed=False
for action,resource in cases:
 with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
  json.dump(dict(PolicySourceArn=role,PolicyInputList=[policy],ActionNames=[action],ResourceArns=[resource]),f);f.flush()
  result=subprocess.run(['aws','iam','simulate-principal-policy','--cli-input-json','file://'+f.name],check=True,capture_output=True,text=True)
  for item in json.loads(result.stdout)['EvaluationResults']:
   print(action,item['EvalDecision']);failed |= item['EvalDecision']!='allowed'
raise SystemExit(1 if failed else 0)
