# Soldering Station Authentication System

An automated student access control system for the Texas Inventionworks (TIW) engineering makerspace. This system verifies student eligibility and manages checkout permissions for soldering equipment using student ID scanning.

## Overview

Students at TIW can scan their student ID to check out soldering kits and equipment. This system:
- Validates student identity and enrollment status
- Checks authorization through the Fabman equipment management system
- Tracks active sessions in DynamoDB
- Grants or denies access based on member eligibility

## Architecture

### Core Components

- **Lambda Function**: AWS Lambda handler that processes authentication requests
- **Fabman Integration**: Connects to Fabman's bridge API to authorize access and manage equipment sessions
- **DynamoDB**: SessionTracker table stores student enrollment status and active session IDs
- **AWS Secrets Manager**: Securely stores Fabman API credentials

### Technology Stack

- **Runtime**: Python
- **Cloud Platform**: AWS (Lambda, DynamoDB, Secrets Manager)
- **Equipment Management**: Fabman API
- **Authentication**: Student EID (Engineering ID) + Fabman member verification

## Deployment

This system is deployed as an AWS Lambda function. The function is triggered via HTTP requests with query parameters specifying:
- `machine`: Equipment type (e.g., `FAKE_TEST_EQUIPMENT`)
- `eid`: Student's Engineering ID
- `action` (optional): Special actions like `status` to check machine availability

## API Usage

### Check Machine Status
```
GET /function?machine=FAKE_TEST_EQUIPMENT&action=status
```
Returns whether the machine is idle or currently in use.

**Response (Idle):**
```json
{
  "status": "idle"
}
```

**Response (Active):**
```json
{
  "status": "active",
  "eid": "A00123456"
}
```

### Start/Stop Session
```
GET /function?machine=FAKE_TEST_EQUIPMENT&eid=A00123456
```
Toggles the student's session. If no active session exists, starts one. If a session is active, stops it.

**Response (Success):**
```json
{
  "session_id": 12345
}
```

**Response (Error):**
```json
{
  "message": "Member not registered with Fabman"
}
```

## How It Works

### Authentication Flow

1. **Student scans ID** → System extracts student EID
2. **Lookup in Fabman** → Verify student is registered with Fabman system
3. **Check DynamoDB** → Look up student's current session status
4. **Start or Stop Session**:
   - **No Active Session**: Request access from Fabman API
     - If authorized: Create session in Fabman and update DynamoDB
     - If not authorized: Deny access
   - **Active Session**: Stop the session and clear from DynamoDB
5. **Return Status** → Confirm success or error to the requesting station

### Session Tracking

Each student-machine pair is tracked in the SessionTracker DynamoDB table:
```
{
  "eid": "A00123456",
  "memberID": 5350,
  "FAKE_TEST_EQUIPMENT": 0  // 0 = no active session, otherwise = session ID
}
```

## Configuration

### Machine Mapping
Update `machine_id` dictionary in the Lambda function to add new equipment:
```python
machine_id = {
    "FAKE_TEST_EQUIPMENT": 5350,
    "SOLDERING_STATION_1": 5351,
    # Add more machines here
}
```

### Required AWS Resources

- **DynamoDB Table**: `SessionTracker` with `eid` as primary key
- **Secrets Manager**: Store Fabman API keys for each machine type
- **Lambda Execution Role**: Permissions for DynamoDB and Secrets Manager access

### Environment Setup

1. Install Python dependencies (included in Lambda package):
   - `boto3` - AWS SDK
   - `requests` - HTTP requests
   - `aws-secretsmanager-caching` - Secrets caching

2. Configure AWS credentials with appropriate permissions

3. Set Fabman API credentials in AWS Secrets Manager

## Security Considerations

- **API Keys**: Stored securely in AWS Secrets Manager, never committed to version control
- **Student Data**: EIDs are verified against Fabman before processing
- **Session IDs**: Unique identifiers prevent unauthorized access to other students' sessions
- **Access Control**: Only authorized Fabman members can start sessions

## Error Handling

The system returns appropriate HTTP status codes and error messages:

| Status | Scenario |
|--------|----------|
| 200 | Successful operation |
| 400 | Invalid input (missing EID, invalid machine, unauthorized member, API failures) |

## Development

### Testing

Update the machine mapping to use a test equipment ID:
```python
machine_id = {
    "FAKE_TEST_EQUIPMENT": 5350  # Test machine for development
}
```

### Logging

The Lambda function prints detailed logs for debugging. Check CloudWatch Logs for:
- Incoming request parameters
- Fabman API responses
- DynamoDB operations
- Error details

## Support

For issues or questions:
- Check DynamoDB SessionTracker table for session state
- Verify Fabman API credentials in Secrets Manager
- Review CloudWatch Logs for detailed error messages
- Ensure machine type parameter is in UPPERCASE

## License

Texas Inventionworks Engineering Makerspace
