from random import randint
from typing import TYPE_CHECKING

import pytest
from botocore.errorfactory import ClientError

from pytest_moto_fixtures.services.s3 import S3Bucket, s3_create_bucket
from pytest_moto_fixtures.utils import randstr

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class TestS3Bucket:
    def test_attributes(self, s3_client: 'S3Client') -> None:
        name = randstr()

        sut = S3Bucket(client=s3_client, name=name)

        assert sut.client == s3_client
        assert sut.name == name

    def test_len(self, s3_bucket: S3Bucket) -> None:
        files = [randstr() for _ in range(randint(3, 10))]

        for expected, filename in enumerate(files, start=1):
            s3_bucket.client.put_object(Bucket=s3_bucket.name, Key=filename, Body=b'')

            assert len(s3_bucket) == expected

        for expected, filename in zip(reversed(range(len(files))), files, strict=True):
            s3_bucket.client.delete_object(Bucket=s3_bucket.name, Key=filename)

            assert len(s3_bucket) == expected

    def test_getitem(self, s3_bucket: S3Bucket) -> None:
        files = [(randstr(), randstr().encode()) for _ in range(randint(3, 10))]

        for filename, content in files:
            s3_bucket.client.put_object(Bucket=s3_bucket.name, Key=filename, Body=content)

            received = s3_bucket[filename]

            assert received['Body'].read() == content

    def test_setitem(self, s3_bucket: S3Bucket) -> None:
        files = [(randstr(), randstr().encode()) for _ in range(randint(3, 10))]

        for filename, content in files:
            s3_bucket[filename] = content

            assert s3_bucket.client.get_object(Bucket=s3_bucket.name, Key=filename)['Body'].read() == content

    def test_delitem(self, s3_bucket: S3Bucket) -> None:
        files = [randstr() for _ in range(randint(3, 10))]

        for filename in files:
            s3_bucket.client.put_object(Bucket=s3_bucket.name, Key=filename, Body='')

            del s3_bucket[filename]

            with pytest.raises(ClientError):
                s3_bucket.client.get_object(Bucket=s3_bucket.name, Key=filename)

    def test_iter(self, s3_bucket: S3Bucket) -> None:
        files = {randstr() for _ in range(randint(3, 10))}

        for filename in files:
            s3_bucket.client.put_object(Bucket=s3_bucket.name, Key=filename, Body='')

        assert {obj['Key'] for obj in s3_bucket} == files

    def test_prune(self, s3_bucket: S3Bucket) -> None:
        files = [randstr() for _ in range(randint(3, 10))]

        for filename in files:
            s3_bucket.client.put_object(Bucket=s3_bucket.name, Key=filename, Body='')

        s3_bucket.prune()

        assert 'Content' not in s3_bucket.client.list_objects_v2(Bucket=s3_bucket.name)


class TestS3CreateBucket:
    def test_default_args(self, s3_client: 'S3Client') -> None:
        with s3_create_bucket(s3_client=s3_client) as sut:
            result = s3_client.list_buckets()
            assert sut.name in [bucket['Name'] for bucket in result['Buckets']]

        result = s3_client.list_buckets()
        assert sut.name not in [bucket['Name'] for bucket in result['Buckets']]

    def test_name_arg(self, s3_client: 'S3Client') -> None:
        name = randstr()

        with s3_create_bucket(s3_client=s3_client, name=name) as sut:
            assert sut.name == name
