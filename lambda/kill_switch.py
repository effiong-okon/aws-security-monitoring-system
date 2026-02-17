def lambda_handler(event, context):
    iam_client = boto3.client('iam')
    username = event['detail']['userIdentity']['userName']
    
    # Strip all permissions
    policies = iam_client.list_attached_user_policies(UserName=username)
    for policy in policies['AttachedPolicies']:
        iam_client.detach_user_policy(
            UserName=username,
            PolicyArn=policy['PolicyArn']
        )
    
    # Apply quarantine boundary
    iam_client.put_user_permissions_boundary(
        UserName=username,
        PermissionsBoundary=quarantine_policy_arn
    )
