from random import randint
from typing import TYPE_CHECKING

from pytest_moto_fixtures.clients.sqs import SQSQueue, sqs_create_queue
from pytest_moto_fixtures.utils import randstr

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient


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

    def test_len(self, sqs_queue: 'SQSQueue') -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message)

            assert len(sqs_queue) == expected

        for expected in reversed(range(len(messages))):
            received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url)['Messages'][0]
            sqs_queue.client.delete_message(QueueUrl=sqs_queue.url, ReceiptHandle=received['ReceiptHandle'])

            assert len(sqs_queue) == expected

    def test_send_message(self, sqs_queue: 'SQSQueue') -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.send_message(body=message)

        received = sqs_queue.client.receive_message(QueueUrl=sqs_queue.url, MaxNumberOfMessages=10)
        assert [message['Body'] for message in received['Messages']] == messages

    def test_receive_message_without_message_in_queue(self, sqs_queue: 'SQSQueue') -> None:
        returned = sqs_queue.receive_message()

        assert returned is None

    def test_receive_message_with_message_in_queue(self, sqs_queue: 'SQSQueue') -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message)

        for message in messages:
            returned = sqs_queue.receive_message()

            assert returned is not None
            assert returned['Body'] == message

        returned = sqs_queue.receive_message()

        assert returned is None

    def test_iter_over_messages_in_queue(self, sqs_queue: 'SQSQueue') -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sqs_queue.client.send_message(QueueUrl=sqs_queue.url, MessageBody=message)

        for message, returned in zip(messages, sqs_queue, strict=True):
            assert returned['Body'] == message


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
