import json
from random import randint
from typing import TYPE_CHECKING

from pytest_moto_fixtures.services.sqs import SQSQueue, sqs_create_fifo_queue, sqs_create_queue
from pytest_moto_fixtures.utils import randstr

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_sqs.literals import QueueAttributeNameType


class TestSQSQueue:
    def test_attributes(self, sqs_client: 'SQSClient') -> None:
        name = randstr()
        arn = randstr()
        url = randstr()

        sut = SQSQueue(client=sqs_client, name=name, arn=arn, url=url)

        assert sut.client == sqs_client
        assert sut.name == name
        assert sut.arn == arn
        assert sut.url == url

    def test_len(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message)

            assert len(sqs_queue) == expected

        for expected in reversed(range(len(messages))):
            received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url)['Messages'][0]
            sqs_queue.client.delete_message(QueueUrl=sqs_queue.url, ReceiptHandle=received['ReceiptHandle'])

            assert len(sqs_queue) == expected

    def test_len_delayed(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message, DelaySeconds=10)

            assert len(sqs_queue) == expected

    def test_len_not_visible(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        sqs_queue.client.send_message_batch(
            QueueUrl=sqs_queue.url,
            Entries=[{'Id': str(i), 'MessageBody': message} for i, message in enumerate(messages)],
        )

        for _ in messages:
            sqs_queue.client.receive_message(QueueUrl=sqs_queue.url, MaxNumberOfMessages=1, VisibilityTimeout=10)

            assert len(sqs_queue) == len(messages)

    def test_send_message_with_str(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.send_message(body=message)

        received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url, MaxNumberOfMessages=10)['Messages']
        assert [message['Body'] for message in received] == messages

    def test_send_message_with_dict(self, sqs_queue: SQSQueue) -> None:
        messages = [{randstr(): randstr() for _ in range(randint(1, 3))} for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.send_message(body=message)

        received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url, MaxNumberOfMessages=10)['Messages']
        assert [json.loads(message['Body']) for message in received] == messages

    def test_send_message_with_args(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.send_message(body=message, deduplication_id=randstr())

        received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url, MaxNumberOfMessages=10)['Messages']
        assert [message['Body'] for message in received] == messages

    def test_send_message_with_delay(self, sqs_queue: SQSQueue) -> None:
        message = randstr()

        sqs_queue.send_message(body=message, delay_seconds=1)

        received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url, MaxNumberOfMessages=1, WaitTimeSeconds=2)[
            'Messages'
        ][0]
        assert received['Body'] == message

    def test_receive_message_without_message_in_queue(self, sqs_queue: SQSQueue) -> None:
        returned = sqs_queue.receive_message()

        assert returned is None

    def test_receive_message_with_message_in_queue(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message)

        for message in messages:
            returned = sqs_queue.receive_message()

            assert returned is not None
            assert returned['Body'] == message

        returned = sqs_queue.receive_message()

        assert returned is None

    def test_iter_over_messages_in_queue(self, sqs_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message)

        for message, returned in zip(messages, sqs_queue, strict=True):
            assert returned['Body'] == message

    def test_purge_queue(self, sqs_queue: SQSQueue) -> None:
        for _ in range(randint(3, 10)):
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=randstr())
        assert len(sqs_queue) != 0

        sqs_queue.purge_queue()

        assert len(sqs_queue) == 0


class TestSQSFifoQueue:
    def test_len(self, sqs_fifo_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            sqs_fifo_queue.client.send_message(
                QueueUrl=sqs_fifo_queue.url,
                MessageBody=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )

            assert len(sqs_fifo_queue) == expected

        for expected in reversed(range(len(messages))):
            received = sqs_fifo_queue.client.receive_message(QueueUrl=sqs_fifo_queue.url)['Messages'][0]
            sqs_fifo_queue.client.delete_message(QueueUrl=sqs_fifo_queue.url, ReceiptHandle=received['ReceiptHandle'])

            assert len(sqs_fifo_queue) == expected

    def test_send_message(self, sqs_fifo_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_fifo_queue.send_message(body=message, deduplication_id=message, group_id=message)

        received = sqs_fifo_queue.client.receive_message(QueueUrl=sqs_fifo_queue.url, MaxNumberOfMessages=10)[
            'Messages'
        ]
        assert [message['Body'] for message in received] == messages

    def test_receive_message_without_message_in_queue(self, sqs_fifo_queue: SQSQueue) -> None:
        returned = sqs_fifo_queue.receive_message()

        assert returned is None

    def test_receive_message_with_message_in_queue(self, sqs_fifo_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_fifo_queue.client.send_message(
                QueueUrl=sqs_fifo_queue.url,
                MessageBody=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )

        for message in messages:
            returned = sqs_fifo_queue.receive_message()

            assert returned is not None
            assert returned['Body'] == message

        returned = sqs_fifo_queue.receive_message()

        assert returned is None

    def test_iter_over_messages_in_queue(self, sqs_fifo_queue: SQSQueue) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_fifo_queue.client.send_message(
                QueueUrl=sqs_fifo_queue.url,
                MessageBody=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )

        for message, returned in zip(messages, sqs_fifo_queue, strict=True):
            assert returned['Body'] == message

    def test_purge_queue(self, sqs_fifo_queue: SQSQueue) -> None:
        for message in (randstr() for _ in range(randint(3, 10))):
            sqs_fifo_queue.client.send_message(
                QueueUrl=sqs_fifo_queue.url,
                MessageBody=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )
        assert len(sqs_fifo_queue) != 0

        sqs_fifo_queue.purge_queue()

        assert len(sqs_fifo_queue) == 0


class TestSqsCreateQueue:
    def test_default_args(self, sqs_client: 'SQSClient') -> None:
        with sqs_create_queue(sqs_client=sqs_client) as sut:
            result = sqs_client.list_queues()
            assert sut.url in result['QueueUrls']
        result = sqs_client.list_queues()
        assert sut.url not in result.get('QueueUrls', [])

    def test_name_arg(self, sqs_client: 'SQSClient') -> None:
        name = randstr()

        with sqs_create_queue(sqs_client=sqs_client, name=name) as sut:
            assert sut.name == name
            assert sut.arn.endswith(f':{name}')
            assert sut.url.endswith(f'/{name}')

    def test_attributes_arg(self, sqs_client: 'SQSClient') -> None:
        attributes: dict[QueueAttributeNameType, str] = {
            'DelaySeconds': '30',
            'MaximumMessageSize': '1024',
            'MessageRetentionPeriod': '3600',
            'ReceiveMessageWaitTimeSeconds': '10',
            'VisibilityTimeout': '60',
        }

        with sqs_create_queue(sqs_client=sqs_client, attributes=attributes) as sut:
            returned = sqs_client.get_queue_attributes(QueueUrl=sut.url, AttributeNames=['All'])['Attributes']

            for name, value in attributes.items():
                assert returned[name] == value

    def test_tags_arg(self, sqs_client: 'SQSClient') -> None:
        tags = {randstr(): randstr() for _ in range(randint(3, 10))}

        with sqs_create_queue(sqs_client=sqs_client, tags=tags) as sut:
            returned = sqs_client.list_queue_tags(QueueUrl=sut.url)['Tags']

            assert returned == tags


class TestSqsCreateFifoQueue:
    def test_default_args(self, sqs_client: 'SQSClient') -> None:
        with sqs_create_fifo_queue(sqs_client=sqs_client) as sut:
            assert sut.name.endswith('.fifo')

            queues = sqs_client.list_queues()
            assert sut.url in queues['QueueUrls']

            attributes = sqs_client.get_queue_attributes(QueueUrl=sut.url, AttributeNames=['FifoQueue'])['Attributes']
            assert attributes['FifoQueue'] == 'true'

        queues = sqs_client.list_queues()
        assert sut.url not in queues.get('QueueUrls', [])

    def test_name_arg_with_fifo(self, sqs_client: 'SQSClient') -> None:
        name = f'{randstr()}.fifo'

        with sqs_create_fifo_queue(sqs_client=sqs_client, name=name) as sut:
            assert sut.name == name

    def test_name_arg_without_fifo(self, sqs_client: 'SQSClient') -> None:
        name = randstr()

        with sqs_create_fifo_queue(sqs_client=sqs_client, name=name) as sut:
            assert sut.name == f'{name}.fifo'

    def test_attributes_arg_with_fifo_queue(self, sqs_client: 'SQSClient') -> None:
        with sqs_create_fifo_queue(sqs_client=sqs_client, attributes={'FifoQueue': 'true'}) as sut:
            returned = sqs_client.get_queue_attributes(QueueUrl=sut.url, AttributeNames=['FifoQueue'])['Attributes']

            assert returned['FifoQueue'] == 'true'

    def test_attributes_arg_append_fifo(self, sqs_client: 'SQSClient') -> None:
        attributes: dict[QueueAttributeNameType, str] = {'DelaySeconds': str(randint(10, 60))}

        with sqs_create_fifo_queue(sqs_client=sqs_client, attributes=attributes) as sut:
            returned = sqs_client.get_queue_attributes(
                QueueUrl=sut.url, AttributeNames=[*attributes.keys(), 'FifoQueue']
            )['Attributes']

            for name, value in attributes.items():
                assert returned[name] == value
            assert returned['FifoQueue'] == 'true'
