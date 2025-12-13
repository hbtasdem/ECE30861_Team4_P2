# Add these imports at the top of your file
import os
from datetime import datetime, timedelta
from typing import Dict, List

import boto3
from fastapi import HTTPException

# Initialize CloudWatch Logs client (add this after your app = FastAPI() line)
cloudwatch_logs = boto3.client('logs', region_name=os.getenv('AWS_REGION', 'us-east-2'))

# IMPORTANT: Set your actual CloudWatch log group name
LOG_GROUP_NAME = os.getenv('CLOUDWATCH_LOG_GROUP', '/aws/ec2/fastapi-logs')

# Add this helper function


def fetch_cloudwatch_logs(hours: int = 1, limit: int = 100) -> List[Dict]:
    """Fetch recent logs from CloudWatch"""
    try:
        start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)

        response = cloudwatch_logs.filter_log_events(
            logGroupName=LOG_GROUP_NAME,
            startTime=start_time,
            endTime=end_time,
            limit=limit
        )

        logs = []
        for event in response.get('events', []):
            ts = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()

            # Determine log level
            level = 'INFO'
            if 'ERROR' in message.upper() or 'EXCEPTION' in message.upper():
                level = 'ERROR'
            elif 'WARNING' in message.upper() or 'WARN' in message.upper():
                level = 'WARNING'
            elif 'DEBUG' in message.upper():
                level = 'DEBUG'

            logs.append({
                'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                'level': level,
                'message': message,
                'stream': event.get('logStreamName', 'unknown')
            })

        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")
