"""Email tracking module — query AWS CloudWatch for SES delivery and engagement metrics."""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class EmailTracker:

    # Metrics published by SES to CloudWatch
    METRICS = ['Send', 'Delivery', 'Bounce', 'Complaint', 'Open', 'Click', 'Reject']

    def __init__(self, aws_access_key: str, aws_secret_key: str, aws_region: str,
                 configuration_set: str):
        self.configuration_set = configuration_set
        self.client = boto3.client(
            'cloudwatch',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
        )

    def get_metric_data(
        self,
        metric_name: str,
        hours: int = 24,
        period: int = 3600,
    ) -> List[Dict]:
        """Fetch a single SES metric from CloudWatch.

        Args:
            metric_name: One of Send, Delivery, Bounce, Complaint, Open, Click, Reject.
            hours: How far back to look (in hours).
            period: Aggregation period in seconds (default 1 hour).

        Returns:
            List of {'timestamp': datetime, 'value': float} sorted by timestamp.
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        try:
            response = self.client.get_metric_statistics(
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
            result = [
                {
                    'timestamp': dp['Timestamp'],
                    'value': dp['Sum'],
                }
                for dp in datapoints
            ]
            result.sort(key=lambda x: x['timestamp'])
            return result

        except (ClientError, NoCredentialsError) as e:
            return []

    def get_all_metrics(self, hours: int = 24, period: int = 3600) -> Dict:
        """Fetch all SES metrics at once.

        Returns:
            {
                'totals': {'Send': 100, 'Delivery': 95, ...},
                'timeseries': {'Send': [...], 'Delivery': [...], ...},
                'error': None or str,
            }
        """
        totals = {}
        timeseries = {}
        error = None

        try:
            for metric in self.METRICS:
                data = self.get_metric_data(metric, hours=hours, period=period)
                timeseries[metric] = data
                totals[metric] = sum(dp['value'] for dp in data)
        except Exception as e:
            error = str(e)

        return {
            'totals': totals,
            'timeseries': timeseries,
            'error': error,
        }

    @staticmethod
    def get_rates(totals: Dict) -> Dict:
        """Calculate delivery and engagement rates from totals.

        Returns dict with keys: delivery_rate, open_rate, click_rate,
        bounce_rate, complaint_rate (all as percentages, 0-100).
        """
        sent = totals.get('Send', 0)
        delivered = totals.get('Delivery', 0)

        def safe_pct(numerator, denominator):
            return (numerator / denominator * 100) if denominator > 0 else 0.0

        return {
            'delivery_rate': safe_pct(delivered, sent),
            'open_rate': safe_pct(totals.get('Open', 0), delivered),
            'click_rate': safe_pct(totals.get('Click', 0), delivered),
            'bounce_rate': safe_pct(totals.get('Bounce', 0), sent),
            'complaint_rate': safe_pct(totals.get('Complaint', 0), sent),
        }
