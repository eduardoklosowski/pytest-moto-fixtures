"""Fixtures for pytest."""

from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from pytest_moto_fixtures.services.eventbridge import EventBridgeBus, eventbridge_create_bus
from pytest_moto_fixtures.services.s3 import S3Bucket, s3_create_bucket
from pytest_moto_fixtures.services.sns import SNSTopic, sns_create_fifo_topic, sns_create_topic
from pytest_moto_fixtures.services.sqs import SQSQueue, sqs_create_fifo_queue, sqs_create_queue

if TYPE_CHECKING:
    from mypy_boto3_events import EventBridgeClient
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_sns import SNSClient
    from mypy_boto3_sqs import SQSClient


@pytest.fixture
def aws_config() -> Iterator[None]:
    """Configure AWS mock."""
    config = {
        'AWS_DEFAULT_REGION': 'us-east-1',
    }
    with patch.dict('os.environ', config), mock_aws():
        yield


@pytest.fixture
def sqs_client(aws_config: None) -> 'SQSClient':
    """SQS Client."""
    return boto3.client('sqs')


@pytest.fixture
def sqs_queue(sqs_client: 'SQSClient') -> Iterator[SQSQueue]:
    """A queue in the SQS service."""
    with sqs_create_queue(sqs_client=sqs_client) as queue:
        yield queue


@pytest.fixture
def sqs_fifo_queue(sqs_client: 'SQSClient') -> Iterator[SQSQueue]:
    """A fifo queue in the SQS service."""
    with sqs_create_fifo_queue(sqs_client=sqs_client) as queue:
        yield queue


@pytest.fixture
def sns_client(aws_config: None) -> 'SNSClient':
    """SNS Client."""
    return boto3.client('sns')


@pytest.fixture
def sns_topic(sns_client: 'SNSClient', sqs_client: 'SQSClient') -> Iterator[SNSTopic]:
    """A topic in the SNS service."""
    with sns_create_topic(sns_client=sns_client, sqs_client=sqs_client) as topic:
        yield topic


@pytest.fixture
def sns_fifo_topic(sns_client: 'SNSClient', sqs_client: 'SQSClient') -> Iterator[SNSTopic]:
    """A fifo topic in the SNS service."""
    with sns_create_fifo_topic(sns_client=sns_client, sqs_client=sqs_client) as topic:
        yield topic


@pytest.fixture
def s3_client(aws_config: None) -> 'S3Client':
    """S3 Client."""
    return boto3.client('s3')


@pytest.fixture
def s3_bucket(s3_client: 'S3Client') -> Iterator[S3Bucket]:
    """A bucket in S3 service."""
    with s3_create_bucket(s3_client=s3_client) as bucket:
        yield bucket


@pytest.fixture
def eventbridge_client(aws_config: None) -> 'EventBridgeClient':
    """Event Bridge client."""
    return boto3.client('events')


@pytest.fixture
def eventbridge_bus(eventbridge_client: 'EventBridgeClient', sqs_client: 'SQSClient') -> Iterator[EventBridgeBus]:
    """A bus in the Event Bridge service."""
    with eventbridge_create_bus(eventbridge_client=eventbridge_client, sqs_client=sqs_client) as bus:
        yield bus
