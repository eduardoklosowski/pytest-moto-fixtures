import os
from typing import TYPE_CHECKING

from pytest_moto_fixtures.services.sns import SNSTopic
from pytest_moto_fixtures.services.sqs import SQSQueue

if TYPE_CHECKING:
    from mypy_boto3_sns import SNSClient
    from mypy_boto3_sqs import SQSClient


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
