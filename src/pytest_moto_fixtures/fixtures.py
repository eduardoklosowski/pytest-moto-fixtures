"""Fixtures for pytest."""

from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from pytest_moto_fixtures.services.sqs import SQSQueue, sqs_create_fifo_queue, sqs_create_queue

if TYPE_CHECKING:
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
