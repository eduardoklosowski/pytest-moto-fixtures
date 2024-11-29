"""Access SNS service."""

import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from typing_extensions import NotRequired

from pytest_moto_fixtures.utils import NoArgs, randstr

from .sqs import SQSQueue, sqs_create_queue

if TYPE_CHECKING:
    from mypy_boto3_sns import SNSClient
    from mypy_boto3_sns.type_defs import MessageAttributeValueTypeDef, TagTypeDef
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_sqs.literals import QueueAttributeNameType

    class MessageAttributeTypeDef(TypedDict):
        """Type of message attribute in SNS."""

        Type: str
        Value: str

    class MessageTypeDef(TypedDict):
        """Type of message in SNS."""

        Type: Literal['Notification']
        MessageId: str
        TopicArn: str
        Subject: NotRequired[str]
        Message: str
        MessageAttributes: NotRequired[dict[str, MessageAttributeTypeDef]]
        Timestamp: str
        SignatureVersion: str
        Signature: str
        SigningCertURL: str
        UnsubscribeURL: str


@dataclass(kw_only=True, frozen=True)
class SNSTopic:
    """Topic in SNS service.

    An SQS queue is used to receive messages sent to the topic.
    """

    client: 'SNSClient' = field(repr=False)
    """SNS Client."""
    name: str
    """Topic name."""
    arn: str
    """Topic ARN."""
    queue: SQSQueue
    """Queue to topic messages."""

    def __len__(self) -> int:
        """Numter of messages in queue of topic.

        Returns:
            Number of messages.
        """
        return len(self.queue)

    def publish_message(
        self,
        *,
        message: str | dict[Any, Any],
        attributes: Mapping[str, 'MessageAttributeValueTypeDef'] | NoArgs = NoArgs.NO_ARG,
        deduplication_id: str | NoArgs = NoArgs.NO_ARG,
        group_id: str | NoArgs = NoArgs.NO_ARG,
    ) -> None:
        """Send message to topic.

        Args:
            message: Message body. If a dict is received, it will be converted to JSON string.
            attributes: Attributes of message.
            deduplication_id: Identifier to check for duplicate messages.
            group_id: Identifier to group messages that should be delivered sequentially.
        """
        if not isinstance(message, str):
            message = json.dumps(message)
        args = _PublishArgs(TopicArn=self.arn, Message=message)
        if not isinstance(attributes, NoArgs):
            args['MessageAttributes'] = attributes
        if not isinstance(deduplication_id, NoArgs):
            args['MessageDeduplicationId'] = deduplication_id
        if not isinstance(group_id, NoArgs):
            args['MessageGroupId'] = group_id
        self.client.publish(**args)

    def receive_message(self) -> 'MessageTypeDef | None':
        """Receive message from the queue of topic and removes them.

        Returns:
            Message received, or ``None`` if the queue has no messages.
        """
        message = self.queue.receive_message()
        if not message:
            return None
        return cast('MessageTypeDef', json.loads(message['Body']))

    def __iter__(self) -> Iterator['MessageTypeDef']:
        """Iterates over messages in queue of topic, removing them after they are received.

        Returns:
            Iterator over messages.
        """
        return self

    def __next__(self) -> 'MessageTypeDef':
        """Receive the next message from queue of topic and delete it.

        Returns:
            Message received.
        """
        message = self.receive_message()
        if message is None:
            raise StopIteration
        return message

    def purge_topic_messages(self) -> None:
        """Purge messages in queue of topic."""
        self.queue.purge_queue()


@contextmanager
def sns_create_topic(
    *,
    sns_client: 'SNSClient',
    sqs_client: 'SQSClient',
    name: str | None = None,
    attributes: Mapping[str, str] | NoArgs = NoArgs.NO_ARG,
    tags: Sequence['TagTypeDef'] | NoArgs = NoArgs.NO_ARG,
) -> Iterator[SNSTopic]:
    """Context for creating an SNS topic with SQS queue subscribed and removing it on exit.

    Args:
        sns_client: SNS client where the topic will be created.
        sqs_client: SQS client where the queue will be created.
        name: Name of topic and queue to be created. If it is ``None`` a random name will be used.
        attributes: Attributes of topic to be created.
        tags: Tags of topic to be created.

    Return:
        Topic created in SNS service.
    """
    if name is None:
        name = randstr()
    args = _CreateTopicArgs(Name=name)
    if not isinstance(attributes, NoArgs):
        args['Attributes'] = attributes
    if not isinstance(tags, NoArgs):
        args['Tags'] = tags

    queue_attributes: Mapping[QueueAttributeNameType, str] = {
        'FifoQueue': args.get('Attributes', {}).get('FifoTopic', 'false'),
    }
    with sqs_create_queue(sqs_client=sqs_client, name=name, attributes=queue_attributes) as queue:
        topic = sns_client.create_topic(**args)
        subscription = sns_client.subscribe(
            TopicArn=topic['TopicArn'], Protocol='sqs', Endpoint=queue.arn, ReturnSubscriptionArn=True
        )
        yield SNSTopic(client=sns_client, name=name, arn=topic['TopicArn'], queue=queue)
        sns_client.unsubscribe(SubscriptionArn=subscription['SubscriptionArn'])
        sns_client.delete_topic(TopicArn=topic['TopicArn'])


@contextmanager
def sns_create_fifo_topic(
    *,
    sns_client: 'SNSClient',
    sqs_client: 'SQSClient',
    name: str | None = None,
    attributes: Mapping[str, str] | NoArgs = NoArgs.NO_ARG,
    tags: Sequence['TagTypeDef'] | NoArgs = NoArgs.NO_ARG,
) -> Iterator[SNSTopic]:
    """Context for creating an SNS fifo topic with SQS fifo queue subscribed and removing it on exit.

    Args:
        sns_client: SNS client where the topic will be created.
        sqs_client: SQS client where the queue will be created.
        name: Name of topic and queue to be created. If it is ``None`` a random name will be used, and if it does not
            end with ``'.fifo'`` it will be appended.
        attributes: Attributes of topic to be created. If it does not have the ``'FifoTopic'`` attribute it will be
            added.
        tags: Tags of topic to be created.

    Return:
        Topic created in SNS service.
    """
    if name is None:
        name = randstr()
    if not name.endswith('.fifo'):
        name += '.fifo'
    attributes = dict(attributes.items()) if not isinstance(attributes, NoArgs) else {}
    if 'FifoTopic' not in attributes:
        attributes['FifoTopic'] = 'true'
    with sns_create_topic(
        sns_client=sns_client, sqs_client=sqs_client, name=name, attributes=attributes, tags=tags
    ) as topic:
        yield topic


class _CreateTopicArgs(TypedDict, total=False):
    """Arguments to create topic."""

    Name: str
    Attributes: Mapping[str, str]
    Tags: Sequence['TagTypeDef']


class _PublishArgs(TypedDict, total=False):
    """Arguments to publish a message."""

    TopicArn: str
    Message: str
    MessageAttributes: Mapping[str, 'MessageAttributeValueTypeDef']
    MessageDeduplicationId: str
    MessageGroupId: str
