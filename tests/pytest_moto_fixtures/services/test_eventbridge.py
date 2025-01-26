import json
from datetime import datetime, timezone
from random import randint
from typing import TYPE_CHECKING

from pytest_moto_fixtures.services.eventbridge import EventBridgeBus, eventbridge_create_bus
from pytest_moto_fixtures.services.sqs import SQSQueue
from pytest_moto_fixtures.utils import randstr

if TYPE_CHECKING:
    from mypy_boto3_events import EventBridgeClient
    from mypy_boto3_events.type_defs import TagTypeDef
    from mypy_boto3_sqs import SQSClient


class TestEventBridgeBus:
    def test_attributes(self, eventbridge_client: 'EventBridgeClient', sqs_queue: SQSQueue) -> None:
        name = randstr()
        arn = randstr()

        sut = EventBridgeBus(client=eventbridge_client, name=name, arn=arn, queue=sqs_queue)

        assert sut.client == eventbridge_client
        assert sut.name == name
        assert sut.arn == arn
        assert sut.queue == sqs_queue

    def test_len(self, eventbridge_bus: EventBridgeBus) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            eventbridge_bus.queue.send_message(body=message)

            assert len(eventbridge_bus) == expected

        for expected in reversed(range(len(messages))):
            eventbridge_bus.queue.receive_message()

            assert len(eventbridge_bus) == expected

    def test_put_event_with_str(self, eventbridge_bus: EventBridgeBus) -> None:
        events = [
            (randstr(), randstr(), {randstr(): randstr() for _ in range(randint(1, 3))}) for _ in range(randint(3, 10))
        ]

        for source, detail_type, detail in events:
            eventbridge_bus.put_event(source=source, detail_type=detail_type, detail=json.dumps(detail))

        received = list(eventbridge_bus.queue)
        assert [
            (event['source'], event['detail-type'], event['detail'])
            for event in (json.loads(event['Body']) for event in received)
        ] == events

    def test_put_event_with_dict(self, eventbridge_bus: EventBridgeBus) -> None:
        events = [
            (randstr(), randstr(), {randstr(): randstr() for _ in range(randint(1, 3))}) for _ in range(randint(3, 10))
        ]

        for source, detail_type, detail in events:
            eventbridge_bus.put_event(source=source, detail_type=detail_type, detail=detail)

        received = list(eventbridge_bus.queue)
        assert [
            (event['source'], event['detail-type'], event['detail'])
            for event in (json.loads(event['Body']) for event in received)
        ] == events

    def test_put_event_with_resources(self, eventbridge_bus: EventBridgeBus) -> None:
        source = randstr()
        detail_type = randstr()
        detail = {randstr(): randstr()}
        resources = [[randstr() for _ in range(randint(1, 3))] for _ in range(3, 10)]

        for resource in resources:
            eventbridge_bus.put_event(source=source, detail_type=detail_type, detail=detail, resources=resource)

        received = list(eventbridge_bus.queue)
        assert [event['resources'] for event in (json.loads(event['Body']) for event in received)] == resources

    def test_put_event_with_time(self, eventbridge_bus: EventBridgeBus) -> None:
        source = randstr()
        detail_type = randstr()
        detail = {randstr(): randstr()}
        times = [datetime.fromtimestamp(randint(946692000, 1577847600), tz=timezone.utc) for _ in range(3, 10)]

        for time in times:
            eventbridge_bus.put_event(source=source, detail_type=detail_type, detail=detail, time=time)

        received = list(eventbridge_bus.queue)

        assert [
            datetime.strptime(event['time'], '%Y-%m-%dT%H:%M:%S%z')
            for event in (json.loads(event['Body']) for event in received)
        ] == times

    def test_receive_event_without_event_in_bus(self, eventbridge_bus: EventBridgeBus) -> None:
        returned = eventbridge_bus.receive_event()

        assert returned is None

    def test_receive_event_with_event_in_topic(self, eventbridge_bus: EventBridgeBus) -> None:
        events = [{randstr(): randstr() for _ in range(randint(1, 3))} for _ in range(randint(3, 10))]

        eventbridge_bus.client.put_events(
            Entries=[
                {
                    'Source': randstr(),
                    'DetailType': randstr(),
                    'Detail': json.dumps(event),
                    'EventBusName': eventbridge_bus.name,
                }
                for event in events
            ]
        )

        for event in events:
            returned = eventbridge_bus.receive_event()

            assert returned is not None
            assert returned['detail'] == event

        returned = eventbridge_bus.receive_event()

        assert returned is None

    def test_iter_over_events_in_bus(self, eventbridge_bus: EventBridgeBus) -> None:
        events = [{randstr(): randstr() for _ in range(randint(1, 3))} for _ in range(randint(3, 10))]

        eventbridge_bus.client.put_events(
            Entries=[
                {
                    'Source': randstr(),
                    'DetailType': randstr(),
                    'Detail': json.dumps(event),
                    'EventBusName': eventbridge_bus.name,
                }
                for event in events
            ]
        )

        for event, returned in zip(events, eventbridge_bus, strict=True):
            assert returned['detail'] == event

    def test_purge_bus_events(self, eventbridge_bus: EventBridgeBus) -> None:
        events = randint(3, 10)
        eventbridge_bus.client.put_events(
            Entries=[
                {
                    'Source': randstr(),
                    'DetailType': randstr(),
                    'Detail': json.dumps({randstr(): randstr()}),
                    'EventBusName': eventbridge_bus.name,
                }
                for _ in range(events)
            ]
        )
        assert len(eventbridge_bus) == events

        eventbridge_bus.purge_bus_events()

        assert len(eventbridge_bus) == 0


class TestEventBridgeCreateBus:
    def test_default_args(self, eventbridge_client: 'EventBridgeClient', sqs_client: 'SQSClient') -> None:
        with eventbridge_create_bus(eventbridge_client=eventbridge_client, sqs_client=sqs_client) as sut:
            result = eventbridge_client.list_event_buses()
            assert sut.arn in [bus['Arn'] for bus in result['EventBuses']]
        result = eventbridge_client.list_event_buses()
        assert sut.arn not in [bus['Arn'] for bus in result['EventBuses']]

    def test_name_arg(self, eventbridge_client: 'EventBridgeClient', sqs_client: 'SQSClient') -> None:
        name = randstr()

        with eventbridge_create_bus(eventbridge_client=eventbridge_client, sqs_client=sqs_client, name=name) as sut:
            assert sut.name == name
            assert sut.arn.endswith(f':event-bus/{name}')

    def test_tags_arg(self, eventbridge_client: 'EventBridgeClient', sqs_client: 'SQSClient') -> None:
        tags: list[TagTypeDef] = [{'Key': randstr(), 'Value': randstr()} for _ in range(randint(3, 5))]

        with eventbridge_create_bus(eventbridge_client=eventbridge_client, sqs_client=sqs_client, tags=tags) as sut:
            assert eventbridge_client.list_tags_for_resource(ResourceARN=sut.arn)['Tags'] == tags
