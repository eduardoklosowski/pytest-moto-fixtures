"""Access SQS service."""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypedDict

from pytest_moto_fixtures.utils import NoArgs, randstr

if TYPE_CHECKING:
    from types_boto3_sqs import SQSClient
    from types_boto3_sqs.literals import QueueAttributeNameType
    from types_boto3_sqs.type_defs import MessageTypeDef


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
            QueueUrl=self.url,
            AttributeNames=[
                'ApproximateNumberOfMessages',
                'ApproximateNumberOfMessagesDelayed',
                'ApproximateNumberOfMessagesNotVisible',
            ],
        )['Attributes']
        return sum(int(value) for value in attributes.values())

    def send_message(
        self,
        *,
        body: str | dict[Any, Any],
        delay_seconds: int | NoArgs = NoArgs.NO_ARG,
        deduplication_id: str | NoArgs = NoArgs.NO_ARG,
        group_id: str | NoArgs = NoArgs.NO_ARG,
    ) -> None:
        """Send message to queue.

        Args:
            body: Message body. If a dict is received, it will be converted to JSON string.
            delay_seconds: Message delivery delay in seconds.
            deduplication_id: Identifier to check for duplicate messages.
            group_id: Identifier to group messages that should be delivered sequentially.
        """
        if not isinstance(body, str):
            body = json.dumps(body)
        args = _SendMessageArgs(QueueUrl=self.url, MessageBody=body)
        if not isinstance(delay_seconds, NoArgs):
            args['DelaySeconds'] = delay_seconds
        if not isinstance(deduplication_id, NoArgs):
            args['MessageDeduplicationId'] = deduplication_id
        if not isinstance(group_id, NoArgs):
            args['MessageGroupId'] = group_id
        self.client.send_message(**args)

    def receive_message(self) -> 'MessageTypeDef | None':
        """Receives messages from the queue and removes them.

        Returns:
            Messages received from the queue, or ``None`` if the queue has no messages.
        """
        messages = self.client.receive_message(QueueUrl=self.url, MaxNumberOfMessages=1).get('Messages')
        if not messages:
            return None
        message = messages[0]
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

    def purge_queue(self) -> None:
        """Purge messages in queue."""
        self.client.purge_queue(QueueUrl=self.url)


@contextmanager
def sqs_create_queue(
    *,
    sqs_client: 'SQSClient',
    name: str | None = None,
    attributes: Mapping['QueueAttributeNameType', str] | NoArgs = NoArgs.NO_ARG,
    tags: Mapping[str, str] | NoArgs = NoArgs.NO_ARG,
) -> Iterator[SQSQueue]:
    """Context for creating an SQS queue and removing it on exit.

    Args:
        sqs_client: SQS client where the queue will be created.
        name: Name of queue to be created. If it is ``None`` a random name will be used.
        attributes: Attributes of queue to be created.
        tags: Tags of queue to be created.

    Return:
        Queue created in SQS service.
    """
    if name is None:
        name = randstr()
    args = _CreateQueueArgs(QueueName=name)
    if not isinstance(attributes, NoArgs):
        args['Attributes'] = attributes
    if not isinstance(tags, NoArgs):
        args['tags'] = tags

    queue = sqs_client.create_queue(**args)
    attributes = sqs_client.get_queue_attributes(QueueUrl=queue['QueueUrl'], AttributeNames=['QueueArn'])['Attributes']
    yield SQSQueue(client=sqs_client, name=name, arn=attributes['QueueArn'], url=queue['QueueUrl'])
    sqs_client.delete_queue(QueueUrl=queue['QueueUrl'])


@contextmanager
def sqs_create_fifo_queue(
    *,
    sqs_client: 'SQSClient',
    name: str | None = None,
    attributes: Mapping['QueueAttributeNameType', str] | NoArgs = NoArgs.NO_ARG,
    tags: Mapping[str, str] | NoArgs = NoArgs.NO_ARG,
) -> Iterator[SQSQueue]:
    """Context for creating an SQS fifo queue and removing it on exit.

    Args:
        sqs_client: SQS client where the queue will be created.
        name: Name of queue to be created. If it is ``None`` a random name will be used, and if it does not end with
            ``'.fifo'`` it will be appended.
        attributes: Attributes of queue to be created. If it does not have the ``'FifoQueue'`` attribute it will be
            added.
        tags: Tags of queue to be created.

    Return:
        Queue created in SQS service.
    """
    if name is None:
        name = randstr()
    if not name.endswith('.fifo'):
        name += '.fifo'
    attributes = dict(attributes.items()) if not isinstance(attributes, NoArgs) else {}
    if 'FifoQueue' not in attributes:
        attributes['FifoQueue'] = 'true'
    with sqs_create_queue(sqs_client=sqs_client, name=name, attributes=attributes, tags=tags) as queue:
        yield queue


class _CreateQueueArgs(TypedDict, total=False):
    """Arguments to create queue."""

    QueueName: str
    Attributes: Mapping['QueueAttributeNameType', str]
    tags: Mapping[str, str]


class _SendMessageArgs(TypedDict, total=False):
    """Arguments to send message."""

    QueueUrl: str
    MessageBody: str
    DelaySeconds: int
    MessageDeduplicationId: str
    MessageGroupId: str
