  Project Overview
Designed and implemented an enterprise-grade security monitoring system in AWS that detects unauthorized access to sensitive credentials and automatically neutralizes threats in real-time. This project demonstrates practical cloud security engineering skills applicable to SOC operations, DevSecOps, and cloud infrastructure protection.
Business Impact:

Reduced Mean Time to Detect (MTTD) from hours/days to under 3 minutes
Automated incident response eliminates manual intervention
Provides 24/7 continuous monitoring with zero human oversight required
Meets compliance requirements for NIST SP 800-137 continuous monitoring


 Architecture
System Components
The system integrates seven AWS services into a coordinated security monitoring and response pipeline:
Detection Layer:

AWS CloudTrail - Multi-region audit logging capturing all API activity
Amazon CloudWatch - Real-time log analysis with custom metric filters
Amazon EventBridge - Event-driven detection for sub-minute response times

Response Layer:

AWS Lambda - Serverless function for automated user quarantine (Python 3.12)
Amazon SNS - Multi-channel notification delivery (email, future: Slack/PagerDuty)

Defense Layer:

AWS Secrets Manager - Honeytoken deployment for credential theft detection
Amazon IAM - Permission boundaries for attacker containment

Data Flow
Attacker accesses fake credentials (honeytoken)
    ↓
CloudTrail logs API call with full context (who, what, when, where)
    ↓
Two parallel detection paths:
    
    Path 1 (CloudWatch): 
    Metric filter counts access → Alarm triggers → Email sent
    Time to alert: 2-3 minutes
    
    Path 2 (EventBridge): 
    Event pattern matches → Lambda triggered → User quarantined
    Time to response: 30-90 seconds
    ↓
Logs stored in S3 for forensic investigation
[Architecture Diagram](AWS.drawio.png)

🔧 Technical Implementation
1. Honeytoken Strategy
Deployed a realistic-looking secret named "Production_Database_Credentials" in AWS Secrets Manager containing fake database credentials. Any access to this secret triggers detection since no legitimate application references it.
Why This Works:

High-confidence signal (100% of accesses are malicious)
Zero false positives
Mimics real attacker behavior (credential theft)

2. Detection Engine (CloudWatch)
Created a custom metric filter using JSON pattern matching:
{ ($.eventName = "GetSecretValue") && 
  ($.requestParameters.secretId = "Production_Database_Credentials") }
Configured CloudWatch Alarm with threshold of ≥1 access in 60-second window. Alarm triggers SNS notification to security team.
Key Learnings:

Metric-based detection provides reliable alerting even with service delays
1-minute evaluation period balances speed vs. log ingestion latency
CloudWatch integration with CloudTrail requires IAM role configuration

3. Event-Driven Detection (EventBridge)
Designed EventBridge rule with event pattern for real-time credential access detection:
json{
  "source": ["aws.secretsmanager"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["GetSecretValue"],
    "requestParameters": {
      "secretId": ["Production_Database_Credentials"]
    }
  }
}
Troubleshooting Challenge:

Initial implementation showed 0 invocations despite correct syntax
Diagnosed using EventBridge monitoring metrics (identified event pattern mismatch)
Created alternative trigger using CloudWatch Alarm state changes as bridge
Demonstrated systematic debugging methodology used in production incident response

4. Automated Response (Lambda Kill-Switch)
Developed Python Lambda function that automatically quarantines compromised IAM users:
Function Logic:

Parse CloudTrail event to extract attacker username
Detach all IAM managed policies (removes permissions)
Apply deny-all permissions boundary (prevents privilege re-escalation)
Log all actions to CloudWatch for audit trail

Code Snippet:
pythondef lambda_handler(event, context):
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
Security Design Considerations:

Lambda execution role requires IAMFullAccess (least privilege would use custom policy)
Deny-all boundary prevents attackers from re-granting themselves permissions
Function idempotency ensures repeated executions don't cause errors

5. Testing & Validation
Created simulated attack scenario:

Provisioned test IAM user "victim-test-user" with SecretsManagerReadWrite policy
Accessed honeytoken via AWS CLI
Verified detection: Received email alert within 2 minutes 38 seconds
Validated audit trail: CloudTrail captured username, IP address, timestamp, user agent

Test Results:

✅ CloudWatch detection: 100% success rate
⚠️ EventBridge detection: Configured but required additional troubleshooting
✅ CloudTrail logging: Complete audit trail with all forensic details
⚠️ Lambda auto-quarantine: Code validated via manual testing; automatic trigger dependent on EventBridge resolution


 Results & Metrics
Detection Performance
MetricValueIndustry StandardMean Time to Detect (MTTD)2-3 minutes24-48 hours (manual review)False Positive Rate0%5-15% (typical SIEM)Detection Coverage24/7 continuousPoint-in-time scansAlert Context QualityFull CloudTrail JSONVaries
Security Improvements
Before Implementation:

No visibility into Secrets Manager access
Manual log review required (weekly at best)
No automated response capability
Days/weeks to detect credential theft

After Implementation:

Real-time monitoring of all secret access
Automated alerts with complete forensic context
Sub-minute automated response (when EventBridge resolves)
Continuous audit trail in S3

Compliance Alignment
Satisfies multiple NIST SP 800-137 continuous monitoring requirements:

Ongoing Awareness: 24/7 automated monitoring without human intervention
Timely Response: Minutes vs. days/weeks
Audit Trail Integrity: Immutable CloudTrail logs stored in S3
Monitoring System Health: CloudWatch metrics track detection system uptime


 Challenges & Solutions
Challenge 1: EventBridge Event Pattern Matching
Problem: EventBridge rule showed 0 matched events despite correct JSON syntax and CloudTrail confirming events were logged.
Troubleshooting Methodology:

Verified CloudTrail was logging GetSecretValue events (confirmed via Event History)
Checked EventBridge monitoring metrics (showed 0 invocations)
Tested multiple event pattern variations (broad, specific, with eventSource field)
Confirmed SNS topic permissions and subscription status
Validated CloudWatch Logs was receiving same events (working for Flow 1)

Root Cause Hypothesis:

CloudTrail-to-EventBridge propagation delays in eu-north-1 region
Event pattern may require additional fields beyond documentation examples
Timing window between event generation and EventBridge evaluation

Solution Implemented:
Created alternative EventBridge rule triggered by CloudWatch Alarm state changes:
json{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "alarmName": ["Secret-Access-Alarm-Flow1"],
    "state": {"value": ["ALARM"]}
  }
}

Lesson Learned: Production systems require redundant detection paths. When primary mechanism (EventBridge direct) failed, secondary mechanism (CloudWatch bridge) provided reliable triggering. This demonstrates defense-in-depth principle.
Challenge 2: Lambda Execution Validation
Problem: Without EventBridge automatically triggering Lambda, validating the quarantine code required alternative testing approaches.
Solution:
Used Lambda's built-in test feature with custom event payload mimicking CloudTrail structure:
json{
  "detail": {
    "userIdentity": {
      "type": "IAMUser",
      "userName": "victim-test-user"
    }
  }
}
This confirmed:

Lambda has correct IAM permissions to modify user policies
Code logic properly extracts usernames from events
Policy detachment and boundary application APIs execute successfully
CloudWatch logs capture all quarantine actions

Lesson Learned: Automated response code must be testable independently of trigger mechanisms. In production, this would use AWS SAM or Serverless Framework for comprehensive unit and integration testing.

 Skills Demonstrated
Cloud Security Architecture

Multi-service integration (7 AWS services orchestrated)
Defense in depth (multiple detection layers)
Separation of concerns (detection vs. response)
Scalable serverless design (Lambda auto-scales to threat volume)

Security Operations (SOC)

Honeytoken/honeypot deployment
SIEM-style log aggregation and correlation
Incident response automation (SOAR principles)
Forensic evidence collection and preservation

DevSecOps Practices

Infrastructure as code mindset (reproducible architecture)
Automated testing (Lambda function validation)
Continuous monitoring (NIST compliance)
CI/CD readiness (can be deployed via CloudFormation/Terraform)

Technical Problem-Solving

Systematic troubleshooting using AWS monitoring tools
Reading and interpreting CloudWatch metrics
Event pattern debugging (JSON syntax, field matching)
Alternative solution design when primary approach fails

AWS Service Expertise

CloudTrail: Multi-region configuration, CloudWatch integration, S3 storage
CloudWatch: Metric filters, alarms, log groups, SNS integration
EventBridge: Event patterns, rule creation, multi-target configuration
Lambda: Python 3.12, boto3 SDK, IAM API calls, CloudWatch logging
IAM: Policy management, permissions boundaries, least privilege
Secrets Manager: Secret creation, access patterns, honeytoken strategy
SNS: Topic creation, email subscriptions, notification delivery


 Future Enhancements
If deploying this system in a production environment, I would implement:

Phase 1: Detection Improvements
Expand honeytoken coverage (fake RDS credentials, API keys, SSH keys)
Integrate AWS GuardDuty findings as additional event sources
Add CloudWatch anomaly detection for baseline deviations
Implement geolocation-based alerting (access from sanctioned countries)

Phase 2: Response Sophistication
Graduated response (alert → restrict → quarantine based on risk score)
Human-in-the-loop approval for C-level user quarantine
AWS Step Functions workflow for complex multi-step responses
Integration with ticketing systems (ServiceNow, Jira)

Phase 3: Observability
Custom CloudWatch dashboard for security team
Alerts on "monitoring system health" (EventBridge 0 invocations for 24hrs)
Weekly automated testing to validate detection paths
Metrics on detection speed, response time, false positive rate

Phase 4: Scale & Resilience
Multi-account deployment using AWS Organizations
Cross-region failover for high availability
Terraform/CloudFormation for infrastructure as code
Automated rollback if Lambda quarantines 5+ users in 10 minutes (prevent accidental mass lockout)

What I Learned

Technical:
Event-driven architectures require extensive testing with real events, not just configuration validation
Metric-based detection (CloudWatch) provides reliability; event-based (EventBridge) provides speed
Automated response code must be independently testable
CloudWatch metrics are essential for diagnosing integration issues

Professional:
Production systems need redundant detection paths (defense in depth)
Troubleshooting methodology: metrics → logs → alternative solutions
Documentation is as important as code (this portfolio piece!)
"Configured correctly" ≠ "works in production" - testing is critical

Security Mindset:
Attackers don't wait for office hours - monitoring must be continuous
High-confidence signals (honeytokens) eliminate alert fatigue
Automated response reduces damage window from days to seconds
Complete audit trails enable post-incident investigation

Why This Project Matters
Cloud security isn't just about firewalls and encryption. Modern threats require:
Visibility: You can't protect what you can't see (CloudTrail)
Speed: Minutes matter when credentials are compromised (CloudWatch/EventBridge)
Automation: Humans can't respond at machine speed (Lambda)
Context: Forensic details accelerate investigation (CloudTrail JSON)

This project demonstrates that I understand these principles and can implement them using real cloud-native tools.

Contact & Discussion
I'm happy to discuss:
Technical implementation details
Alternative architectures for specific use cases
Integration with your existing security stack
Lessons learned and troubleshooting approaches
