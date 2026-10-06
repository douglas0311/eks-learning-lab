"""Apply the version-pinned controller policy to its existing managed policy only."""
import json
from pathlib import Path
import subprocess

ACCOUNT = '490224159848'
ROLE = 'eks-learning-lab-lab-eks-aws-load-balancer-controller'
ARN = 'arn:aws:iam::' + ACCOUNT + ':policy/' + ROLE
SOURCE = Path('modules/aws_load_balancer_controller_iam/policy.json')


def aws(*args):
    result = subprocess.run(['aws', *args, '--output', 'json'], check=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main():
    if aws('sts', 'get-caller-identity')['Account'] != ACCOUNT:
        raise RuntimeError('Unexpected AWS account')
    attached = aws('iam', 'list-attached-role-policies', '--role-name', ROLE)['AttachedPolicies']
    if not any(p['PolicyArn'] == ARN for p in attached):
        raise RuntimeError('Expected managed policy is not attached to the controller role')
    policy = aws('iam', 'get-policy', '--policy-arn', ARN)['Policy']
    previous = policy['DefaultVersionId']
    current = aws('iam', 'get-policy-version', '--policy-arn', ARN, '--version-id', previous)['PolicyVersion']['Document']
    desired = json.loads(SOURCE.read_text())
    if current == desired:
        print('Controller IAM policy already matches the pinned repository policy.')
        return
    versions = aws('iam', 'list-policy-versions', '--policy-arn', ARN)['Versions']
    if len(versions) >= 5:
        raise RuntimeError('Policy has five versions. Review retained versions before making room; no version was deleted.')
    result = aws('iam', 'create-policy-version', '--policy-arn', ARN,
                 '--policy-document', 'file://' + str(SOURCE), '--set-as-default')
    version = result['PolicyVersion']['VersionId']
    actual = aws('iam', 'get-policy', '--policy-arn', ARN)['Policy']['DefaultVersionId']
    if actual != version:
        raise RuntimeError('Default version changed unexpectedly; inspect IAM before continuing')
    print('Updated only controller policy:', ARN)
    print('New default:', version, '| previous version retained:', previous)
    print('IAM propagation and controller reconciliation still need live validation. No Kubernetes operation was executed.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stderr)
        raise
