import os
from typing import TYPE_CHECKING

from pytest_moto_fixtures.services.sqs import SQSQueue

if TYPE_CHECKING:
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
