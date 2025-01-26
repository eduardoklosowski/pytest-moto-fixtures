import json
from random import randint
from typing import TYPE_CHECKING
from unittest.mock import ANY

from pytest_moto_fixtures.services.sns import SNSTopic, sns_create_fifo_topic, sns_create_topic
from pytest_moto_fixtures.services.sqs import SQSQueue
from pytest_moto_fixtures.utils import randstr

if TYPE_CHECKING:
    from types_boto3_sns import SNSClient
    from types_boto3_sns.type_defs import TagTypeDef
    from types_boto3_sqs import SQSClient


class TestSNSTopic:
    def test_attributes(self, sns_client: 'SNSClient', sqs_queue: SQSQueue) -> None:
        name = randstr()
        arn = randstr()

        sut = SNSTopic(client=sns_client, name=name, arn=arn, queue=sqs_queue)

        assert sut.client == sns_client
        assert sut.name == name
        assert sut.arn == arn
        assert sut.queue == sqs_queue

    def test_len(self, sns_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            sns_topic.queue.send_message(body=message)

            assert len(sns_topic) == expected

        for expected in reversed(range(len(messages))):
            sns_topic.queue.receive_message()

            assert len(sns_topic) == expected

    def test_publish_message_with_str(self, sns_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sns_topic.publish_message(message=message)

        received = list(sns_topic.queue)
        assert [json.loads(message['Body'])['Message'] for message in received] == messages

    def test_publish_message_with_dict(self, sns_topic: SNSTopic) -> None:
        messages = [{randstr(): randstr() for _ in range(randint(1, 3))} for _ in range(randint(3, 10))]

        for message in messages:
            sns_topic.publish_message(message=message)

        received = list(sns_topic.queue)
        assert [json.loads(json.loads(message['Body'])['Message']) for message in received] == messages

    def test_publish_message_with_attributes(self, sns_topic: SNSTopic) -> None:
        messages = [
            {
                'Type': 'Notification',
                'MessageId': ANY,
                'TopicArn': sns_topic.arn,
                'Message': randstr(),
                'MessageAttributes': {randstr(): {'Type': 'String', 'Value': randstr()} for _ in range(randint(1, 3))},
                'Timestamp': ANY,
                'SignatureVersion': ANY,
                'Signature': ANY,
                'SigningCertURL': ANY,
                'UnsubscribeURL': ANY,
            }
            for _ in range(randint(3, 10))
        ]

        for message in messages:
            sns_topic.publish_message(
                message=message['Message'],
                attributes={
                    name: {'DataType': 'String', 'StringValue': value['Value']}
                    for name, value in message['MessageAttributes'].items()
                },
            )

        received = list(sns_topic.queue)
        assert [json.loads(message['Body']) for message in received] == messages

    def test_receive_message_without_message_in_topic(self, sns_topic: SNSTopic) -> None:
        returned = sns_topic.receive_message()

        assert returned is None

    def test_receive_message_with_message_in_topic(self, sns_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sns_topic.client.publish(TopicArn=sns_topic.arn, Message=message)

        for message in messages:
            returned = sns_topic.receive_message()

            assert returned is not None
            assert returned['Message'] == message

        returned = sns_topic.receive_message()

        assert returned is None

    def test_iter_over_messages_in_topic(self, sns_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sns_topic.client.publish(TopicArn=sns_topic.arn, Message=message)

        for message, returned in zip(messages, sns_topic, strict=True):
            assert returned['Message'] == message

    def test_purge_topic_messages(self, sns_topic: SNSTopic) -> None:
        for _ in range(randint(3, 10)):
            sns_topic.client.publish(TargetArn=sns_topic.arn, Message=randstr())
        assert len(sns_topic) != 0

        sns_topic.purge_topic_messages()

        assert len(sns_topic) == 0


class TestSNSFifoTopic:
    def test_len(self, sns_fifo_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for expected, message in enumerate(messages, start=1):
            sns_fifo_topic.queue.send_message(body=message, deduplication_id=message, group_id=message)

            assert len(sns_fifo_topic) == expected

        for expected in reversed(range(len(messages))):
            sns_fifo_topic.queue.receive_message()

            assert len(sns_fifo_topic) == expected

    def test_send_message(self, sns_fifo_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sns_fifo_topic.publish_message(message=message, deduplication_id=message, group_id=message)

        received = list(sns_fifo_topic.queue)
        assert [json.loads(message['Body'])['Message'] for message in received] == messages

    def test_receive_message_without_message_in_topic(self, sns_fifo_topic: SNSTopic) -> None:
        returned = sns_fifo_topic.receive_message()

        assert returned is None

    def test_receive_message_with_message_in_topic(self, sns_fifo_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sns_fifo_topic.client.publish(
                TopicArn=sns_fifo_topic.arn,
                Message=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )

        for message in messages:
            returned = sns_fifo_topic.receive_message()

            assert returned is not None
            assert returned['Message'] == message

        returned = sns_fifo_topic.receive_message()

        assert returned is None

    def test_iter_over_messages_in_topic(self, sns_fifo_topic: SNSTopic) -> None:
        messages = [randstr() for _ in range(randint(3, 10))]

        for message in messages:
            sns_fifo_topic.client.publish(
                TopicArn=sns_fifo_topic.arn,
                Message=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )

        for message, returned in zip(messages, sns_fifo_topic, strict=True):
            assert returned['Message'] == message

    def test_purge_topic_messages(self, sns_fifo_topic: SNSTopic) -> None:
        for message in (randstr() for _ in range(randint(3, 10))):
            sns_fifo_topic.client.publish(
                TargetArn=sns_fifo_topic.arn,
                Message=message,
                MessageDeduplicationId=message,
                MessageGroupId=message,
            )
        assert len(sns_fifo_topic) != 0

        sns_fifo_topic.purge_topic_messages()

        assert len(sns_fifo_topic) == 0


class TestSnsCreateTopic:
    def test_default_args(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        with sns_create_topic(sns_client=sns_client, sqs_client=sqs_client) as sut:
            result = sns_client.list_topics()
            assert sut.arn in [topic['TopicArn'] for topic in result['Topics']]
        result = sns_client.list_topics()
        assert sut.arn not in [topic['TopicArn'] for topic in result.get('Topics', [])]

    def test_name_arg(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        name = randstr()

        with sns_create_topic(sns_client=sns_client, sqs_client=sqs_client, name=name) as sut:
            assert sut.name == name
            assert sut.arn.endswith(f':{name}')

    def test_attributes_arg(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        attributes = {
            'DisplayName': randstr(),
        }

        with sns_create_topic(sns_client=sns_client, sqs_client=sqs_client, attributes=attributes) as sut:
            returned = sns_client.get_topic_attributes(TopicArn=sut.arn)['Attributes']

            for name, value in attributes.items():
                assert returned[name] == value

    def test_tags_arg(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        tags: list[TagTypeDef] = [{'Key': randstr(), 'Value': randstr()} for _ in range(randint(3, 10))]

        with sns_create_topic(sns_client=sns_client, sqs_client=sqs_client, tags=tags) as sut:
            returned = sns_client.list_tags_for_resource(ResourceArn=sut.arn)['Tags']

            assert returned == tags


class TestSnsCreateFifoTopic:
    def test_default_args(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        with sns_create_fifo_topic(sns_client=sns_client, sqs_client=sqs_client) as sut:
            assert sut.name.endswith('.fifo')

            topics = sns_client.list_topics()
            assert sut.arn in [topic['TopicArn'] for topic in topics['Topics']]

            attributes = sns_client.get_topic_attributes(TopicArn=sut.arn)['Attributes']
            assert attributes['FifoTopic'] == 'true'

        topics = sns_client.list_topics()
        assert sut.arn not in [topic['TopicArn'] for topic in topics['Topics']]

    def test_name_arg_with_fifo(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        name = f'{randstr()}.fifo'

        with sns_create_fifo_topic(sns_client=sns_client, sqs_client=sqs_client, name=name) as sut:
            assert sut.name == name

    def test_name_arg_without_fifo(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        name = randstr()

        with sns_create_fifo_topic(sns_client=sns_client, sqs_client=sqs_client, name=name) as sut:
            assert sut.name == f'{name}.fifo'

    def test_attributes_arg_with_fifo_topic(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        with sns_create_fifo_topic(
            sns_client=sns_client, sqs_client=sqs_client, attributes={'FifoTopic': 'true'}
        ) as sut:
            returned = sns_client.get_topic_attributes(TopicArn=sut.arn)['Attributes']

            assert returned['FifoTopic'] == 'true'

    def test_attributes_arg_append_fifo(self, sns_client: 'SNSClient', sqs_client: 'SQSClient') -> None:
        attributes: dict[str, str] = {'DisplayName': randstr()}

        with sns_create_fifo_topic(sns_client=sns_client, sqs_client=sqs_client, attributes=attributes) as sut:
            returned = sns_client.get_topic_attributes(TopicArn=sut.arn)['Attributes']

            for name, value in attributes.items():
                assert returned[name] == value
            assert returned['FifoTopic'] == 'true'
