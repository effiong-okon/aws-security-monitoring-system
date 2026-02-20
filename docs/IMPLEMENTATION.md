# Implementation Guide

## Prerequisites

- AWS Account with administrative access
- AWS CLI configured
- Basic understanding of AWS services

## Deployment Steps

### 1. Set Up CloudTrail
```bash
# Create S3 bucket for logs
aws s3 mb s3://security-monitoring-logs-YOUR-INITIALS-2025 --region eu-north-1

# Create CloudTrail trail
aws cloudtrail create-trail \
  --name SecurityMonitoring-Trail \
  --s3-bucket-name security-monitoring-logs-YOUR-INITIALS-2025 \
  --is-multi-region-trail
```

### 2. Create Honeytoken Secret
```bash
aws secretsmanager create-secret \
  --name Production_Database_Credentials \
  --description "Honeytoken for detection" \
  --secret-string '{"username":"db_admin","password":"FakePassword123!"}'
```

### 3. Set Up CloudWatch

- Create metric filter (see AWS Console steps in README)
- Create alarm with threshold ≥ 1
- Connect to SNS topic

### 4. Deploy Lambda Function
```bash
cd lambda
zip function.zip kill_switch.py
aws lambda create-function \
  --function-name SecurityKillSwitch \
  --runtime python3.12 \
  --role YOUR-LAMBDA-ROLE-ARN \
  --handler kill_switch.lambda_handler \
  --zip-file fileb://function.zip
```

### 5. Configure EventBridge

- Create rule with event pattern
- Add Lambda as target

## Testing

Test the system:
```bash
aws secretsmanager get-secret-value \
  --secret-id Production_Database_Credentials
```

Check your email for alerts within 2-3 minutes.

## Cleanup

To remove all resources:
```bash
# Delete CloudTrail
aws cloudtrail delete-trail --name SecurityMonitoring-Trail

# Delete S3 bucket
aws s3 rb s3://security-monitoring-logs-YOUR-INITIALS-2025 --force

# Delete secret
aws secretsmanager delete-secret --secret-id Production_Database_Credentials

# Delete Lambda
aws lambda delete-function --function-name SecurityKillSwitch
```

## Troubleshooting

**Issue:** EventBridge not triggering
- **Check:** EventBridge monitoring metrics for invocations
- **Solution:** Verify event pattern matches CloudTrail structure

**Issue:** No email received
- **Check:** SNS subscription status (must be confirmed)
- **Solution:** Check spam folder, re-subscribe if needed
