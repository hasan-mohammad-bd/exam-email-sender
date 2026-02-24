"""Email tracking module - queries AWS CloudWatch for SES email event metrics"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class EmailTracker:
    """Query SES email tracking metrics from CloudWatch"""

    # SES metric names published to CloudWatch
    METRICS = ['Send', 'Delivery', 'Bounce', 'Complaint', 'Open', 'Click', 'Reject']

    def __init__(self, ses_config: Dict):
        self.aws_access_key = ses_config['aws_access_key']
        self.aws_secret_key = ses_config['aws_secret_key']
        self.aws_region = ses_config.get('aws_region', 'ap-southeast-1')
        self.configuration_set = ses_config.get('configuration_set', 'CitybankEmailTracking')

        self.cloudwatch = boto3.client(
            'cloudwatch',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.aws_region,
        )

    def get_metric_data(
        self,
        metric_name: str,
        hours: int = 24,
        period: int = 3600,
    ) -> Tuple[bool, List[Dict]]:
        """
        Fetch a single SES metric from CloudWatch.

        Args:
            metric_name: One of Send, Delivery, Bounce, Complaint, Open, Click, Reject
            hours: How many hours of history to query (default 24)
            period: Aggregation period in seconds (default 3600 = 1 hour)

        Returns:
            (success, list of {timestamp, value} dicts sorted by time)
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/SES',
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'ses:configuration-set',
                        'Value': self.configuration_set,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Sum'],
            )

            datapoints = response.get('Datapoints', [])
            data = [
                {
                    'timestamp': dp['Timestamp'],
                    'value': int(dp['Sum']),
                }
                for dp in datapoints
            ]
            data.sort(key=lambda d: d['timestamp'])
            return True, data

        except ClientError as e:
            return False, []
        except Exception as e:
            return False, []

    def get_all_metrics(self, hours: int = 24, period: int = 3600) -> Dict[str, any]:
        """
        Fetch all SES metrics for the configuration set.

        Returns dict with:
            - totals: {metric_name: total_count}
            - timeseries: {metric_name: [{timestamp, value}, ...]}
            - success: bool
            - error: str or None
        """
        totals = {}
        timeseries = {}

        try:
            for metric in self.METRICS:
                ok, data = self.get_metric_data(metric, hours=hours, period=period)
                total = sum(d['value'] for d in data) if data else 0
                totals[metric] = total
                timeseries[metric] = data

            return {
                'success': True,
                'totals': totals,
                'timeseries': timeseries,
                'error': None,
            }

        except Exception as e:
            return {
                'success': False,
                'totals': totals,
                'timeseries': timeseries,
                'error': str(e),
            }

    def get_rates(self, totals: Dict[str, int]) -> Dict[str, float]:
        """Calculate delivery, open, click, bounce rates from totals."""
        sent = totals.get('Send', 0)
        if sent == 0:
            return {
                'delivery_rate': 0.0,
                'open_rate': 0.0,
                'click_rate': 0.0,
                'bounce_rate': 0.0,
                'complaint_rate': 0.0,
            }
        delivered = totals.get('Delivery', 0)
        return {
            'delivery_rate': (delivered / sent) * 100,
            'open_rate': (totals.get('Open', 0) / delivered * 100) if delivered else 0.0,
            'click_rate': (totals.get('Click', 0) / delivered * 100) if delivered else 0.0,
            'bounce_rate': (totals.get('Bounce', 0) / sent) * 100,
            'complaint_rate': (totals.get('Complaint', 0) / sent) * 100,
        }
