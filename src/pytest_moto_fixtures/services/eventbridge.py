"""Access Event Bridge service."""

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict, cast

from pytest_moto_fixtures.utils import NoArgs, randstr

from .sqs import SQSQueue, sqs_create_queue

if TYPE_CHECKING:
    from types_boto3_events import EventBridgeClient
    from types_boto3_events.type_defs import PutEventsRequestEntryTypeDef, TagTypeDef
    from types_boto3_sqs import SQSClient

    EventTypeDef = TypedDict(
        'EventTypeDef',
        {
            'id': str,
            'time': str,
            'version': str,
            'detail-type': str,
            'source': str,
            'region': str,
            'resources': list[str],
            'detail': Any,
        },
    )


@dataclass(kw_only=True, frozen=True)
class EventBridgeBus:
    """Bus in Event Bridge service.

    An SQS queue is used to receive messages sent to the bus.
    """

    client: 'EventBridgeClient' = field(repr=False)
    """Event Bridge Client."""
    name: str
    """Bus name."""
    arn: str
    """Bus ARN."""
    queue: SQSQueue
    """Queu to bus messages."""

    def __len__(self) -> int:
        """Numter of messages in queue of bus.

        Returns:
            Number of messages.
        """
        return len(self.queue)

    def put_event(
        self,
        *,
        source: str,
        detail_type: str,
        detail: str | dict[Any, Any],
        resources: list[str] | NoArgs = NoArgs.NO_ARG,
        time: datetime | NoArgs = NoArgs.NO_ARG,
    ) -> None:
        """Put event to bus.

        Args:
            source: Source of event.
            detail_type: Event detail type.
            detail: Event details. Receives a string in JSON format or a dict.
            resources: List of resources associated with the event.
            time: Date and time of the event. If not provided, the current time will be used.
        """
        if not isinstance(detail, str):
            detail = json.dumps(detail)
        entry: PutEventsRequestEntryTypeDef = {
            'Source': source,
            'DetailType': detail_type,
            'Detail': detail,
            'EventBusName': self.name,
        }
        if resources is not NoArgs.NO_ARG:
            entry['Resources'] = resources
        if time is not NoArgs.NO_ARG:
            entry['Time'] = time
        self.client.put_events(Entries=[entry])

    def receive_event(self) -> 'EventTypeDef | None':
        """Receive event from the queue of bus and removes them.

        Returns:
            Event received, or ``None`` if the queue has no events.
        """
        message = self.queue.receive_message()
        if not message:
            return None
        return cast('EventTypeDef', json.loads(message['Body']))

    def __iter__(self) -> Iterator['EventTypeDef']:
        """Iterates over events in queue of bus, removing them after they are received.

        Returns:
            Iterator over messages.
        """
        return self

    def __next__(self) -> 'EventTypeDef':
        """Receive the next event from queue of bus and delete it.

        Returns:
            Message received.
        """
        message = self.receive_event()
        if message is None:
            raise StopIteration
        return message

    def purge_bus_events(self) -> None:
        """Purge events in queue of topic."""
        self.queue.purge_queue()


@contextmanager
def eventbridge_create_bus(
    *,
    eventbridge_client: 'EventBridgeClient',
    sqs_client: 'SQSClient',
    name: str | None = None,
    tags: Sequence['TagTypeDef'] | NoArgs = NoArgs.NO_ARG,
) -> Iterator[EventBridgeBus]:
    """Context for creating an Event Bridge bus with SQS queue targeted and removing it on exit.

    Args:
        eventbridge_client: Event Bridge client where the bus will be created.
        sqs_client: SQS client where the queue will be created.
        name: Name of bus and queue to be created. If it is ``None`` a random name will be used.
        tags: Tags of bus to be created.

    Return:
        Bus created in Event Bridge service.
    """
    if name is None:
        name = randstr()
    args = _CreateBusArgs(Name=name)
    if tags is not NoArgs.NO_ARG:
        args['Tags'] = tags

    with sqs_create_queue(sqs_client=sqs_client, name=name) as queue:
        bus = eventbridge_client.create_event_bus(**args)
        eventbridge_client.put_rule(Name='all', EventPattern='{}', EventBusName=name)
        eventbridge_client.put_targets(Rule='all', Targets=[{'Id': 'queue', 'Arn': queue.arn}], EventBusName=name)
        yield EventBridgeBus(client=eventbridge_client, name=name, arn=bus['EventBusArn'], queue=queue)
        eventbridge_client.remove_targets(Rule='all', Ids=['queue'], EventBusName=name)
        eventbridge_client.delete_rule(Name='all', EventBusName=name)
        eventbridge_client.delete_event_bus(Name=name)


class _CreateBusArgs(TypedDict, total=False):
    """Arguments to create bus."""

    Name: str
    Tags: Sequence['TagTypeDef']
