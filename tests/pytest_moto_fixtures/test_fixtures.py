import os
from typing import TYPE_CHECKING

from pytest_moto_fixtures.services.eventbridge import EventBridgeBus
from pytest_moto_fixtures.services.s3 import S3Bucket
from pytest_moto_fixtures.services.sns import SNSTopic
from pytest_moto_fixtures.services.sqs import SQSQueue

if TYPE_CHECKING:
    from types_boto3_events import EventBridgeClient
    from types_boto3_s3 import S3Client
    from types_boto3_sns import SNSClient
    from types_boto3_sqs import SQSClient


def test_aws_config(aws_config: None) -> None:
    assert 'AWS_ACCESS_KEY_ID' in os.environ
    assert 'AWS_SECRET_ACCESS_KEY' in os.environ
    assert os.environ['AWS_DEFAULT_REGION'] == 'us-east-1'


def test_sqs_queue(sqs_client: 'SQSClient', sqs_queue: SQSQueue) -> None:
    assert not sqs_queue.name.endswith('.fifo')
    queues = sqs_client.list_queues(QueueNamePrefix=sqs_queue.name)['QueueUrls']
    assert sqs_queue.url in queues


def test_sqs_fifo_queue(sqs_client: 'SQSClient', sqs_fifo_queue: SQSQueue) -> None:
    assert sqs_fifo_queue.name.endswith('.fifo')
    queues = sqs_client.list_queues(QueueNamePrefix=sqs_fifo_queue.name)['QueueUrls']
    assert sqs_fifo_queue.url in queues


def test_sns_topic(sns_client: 'SNSClient', sns_topic: SNSTopic) -> None:
    assert not sns_topic.name.endswith('.fifo')
    topics = sns_client.list_topics()['Topics']
    assert sns_topic.arn in [topic['TopicArn'] for topic in topics]


def test_sns_fifo_topic(sns_client: 'SNSClient', sns_fifo_topic: SNSTopic) -> None:
    assert sns_fifo_topic.name.endswith('.fifo')
    topics = sns_client.list_topics()['Topics']
    assert sns_fifo_topic.arn in [topic['TopicArn'] for topic in topics]


def test_s3_bucket(s3_client: 'S3Client', s3_bucket: S3Bucket) -> None:
    buckets = s3_client.list_buckets(Prefix=s3_bucket.name)['Buckets']
    assert s3_bucket.name in [bucket['Name'] for bucket in buckets]


def test_eventbridge_bus(eventbridge_client: 'EventBridgeClient', eventbridge_bus: EventBridgeBus) -> None:
    buses = eventbridge_client.list_event_buses(NamePrefix=eventbridge_bus.name)['EventBuses']
    assert eventbridge_bus.arn in [bus['Arn'] for bus in buses]
