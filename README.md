# pytest-moto-fixtures

[pytest](https://docs.pytest.org/) fixtures for testing code that integrates with [AWS](https://aws.amazon.com/) using [moto](https://docs.getmoto.org/) as a mock.

## Install

Install `pytest-moto-fixtures` package from [PyPI](https://pypi.org/project/pytest-moto-fixtures/):

```sh
pip install pytest-moto-fixtures[pytest]
```

## Examples of Use

**Code for test:**

```python
class Example:
    def __init__(self, sqs_client, queue_url):
        self._sqs_client = sqs_client
        self._queue_url = queue_url

    def run(self, values):
        total = 0
        for value in values:
            total += value
            self._sqs_client.send_message(QueueUrl=self._queue_url, MessageBody=f'Value processed: {value}')
        return total
```

**Test example using fixture:**

```python
from random import randint

def test_example_with_fixture(sqs_queue):
    values = [randint(1, 10) for _ in range(randint(3, 10))]
    expected = sum(values)

    sut = Example(sqs_client=sqs_queue.client, queue_url=sqs_queue.url)
    returned = sut.run(values)

    assert returned == expected
    assert len(sqs_queue) == len(values)
    for value, message in zip(values, sqs_queue):
        assert message['Body'] == f'Value processed: {value}'
```

**Test example using context:**

```python
from random import randint
from pytest_moto_fixtures.clients.sqs import sqs_create_queue

def test_example_with_context(sqs_client):
    values = [randint(1, 10) for _ in range(randint(3, 10))]
    expected = sum(values)

    with sqs_create_queue(sqs_client=sqs_client, name='my-queue') as sqs_queue:
        sut = Example(sqs_client=sqs_client, queue_url=sqs_queue.url)
        returned = sut.run(values)

        assert returned == expected
        assert len(sqs_queue) == len(values)
        for value, message in zip(values, sqs_queue):
            assert message['Body'] == f'Value processed: {value}'
```
