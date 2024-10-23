"""SQS Client."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import boto3
import pytest

from pytest_moto_fixtures.utils import randstr

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_sqs.type_defs import MessageTypeDef


@pytest.fixture
def sqs_client(aws_config: None) -> 'SQSClient':
    """SQS Client."""
    return boto3.client('sqs')


@dataclass(kw_only=True, frozen=True)
class SQSQueue:
    """Queue in SQS service."""

    client: 'SQSClient' = field(repr=False)
    """SQS Client."""
    name: str
    """Queue name."""
    arn: str
    """Queue ARN."""
    url: str
    """Queue URL."""

    def __len__(self) -> int:
        """Number of messages in queue.

        Returns:
            Number of messages in queue.
        """
        attributes = self.client.get_queue_attributes(
            QueueUrl=self.url, AttributeNames=['ApproximateNumberOfMessages']
        )['Attributes']
        return int(attributes['ApproximateNumberOfMessages'])

    def send_message(self, *, body: str) -> None:
        """Send message to queue.

        Args:
            body: Message body.
        """
        self.client.send_message(QueueUrl=self.url, MessageBody=body)

    def receive_message(self) -> 'MessageTypeDef | None':
        """Receives messages from the queue and removes them.

        Returns:
            Messages received from the queue, or `None` if the queue has no messages.
        """
        received = self.client.receive_message(QueueUrl=self.url, MaxNumberOfMessages=1)
        if not received.get('Messages'):
            return None
        message = received['Messages'][0]
        self.client.delete_message(QueueUrl=self.url, ReceiptHandle=message['ReceiptHandle'])
        return message

    def __iter__(self) -> Iterator['MessageTypeDef']:
        """Iterates over messages in queue, removing them after they are received.

        Returns:
            Iterator over messages.
        """
        return self

    def __next__(self) -> 'MessageTypeDef':
        """Receive the next message from queue and delete it.

        Returns:
            Message received from queue.
        """
        message = self.receive_message()
        if message is None:
            raise StopIteration
        return message


@contextmanager
def sqs_create_queue(
    *,
    sqs_client: 'SQSClient',
    name: str | None = None,
) -> Iterator[SQSQueue]:
    """Context for creating an SQS queue and removing it on exit.

    Args:
        sqs_client: SQS client where the queue will be created.
        name: Name of queue to be created. If it is `None` a random name will be used.

    Return:
        Queue created in SQS service.
    """
    if name is None:
        name = randstr()
    queue = sqs_client.create_queue(QueueName=name)
    attributes = sqs_client.get_queue_attributes(QueueUrl=queue['QueueUrl'], AttributeNames=['QueueArn'])['Attributes']
    yield SQSQueue(client=sqs_client, name=name, arn=attributes['QueueArn'], url=queue['QueueUrl'])
    sqs_client.delete_queue(QueueUrl=queue['QueueUrl'])


@pytest.fixture
def sqs_queue(sqs_client: 'SQSClient') -> Iterator[SQSQueue]:
    """A queue in the SQS service."""
    with sqs_create_queue(sqs_client=sqs_client) as queue:
        yield queue
