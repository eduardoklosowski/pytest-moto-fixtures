"""Access S3 service."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pytest_moto_fixtures.utils import NoArgs, randstr

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import BlobTypeDef, GetObjectOutputTypeDef, ObjectTypeDef


@dataclass(kw_only=True, frozen=True)
class S3Bucket:
    """Bucket in S3 service."""

    client: 'S3Client' = field(repr=False)
    """S3 Client."""
    name: str
    """Bucket name."""

    def __len__(self) -> int:
        """Number of objects in bucket.

        Returns:
            Number of objects in bucket.
        """
        response = self.client.list_objects_v2(Bucket=self.name)
        size = response['KeyCount']
        while response['IsTruncated']:
            response = self.client.list_objects_v2(
                Bucket=self.name, ContinuationToken=response['NextContinuationToken']
            )
            size += response['KeyCount']
        return size

    def __getitem__(self, key: str, /) -> 'GetObjectOutputTypeDef':
        """Get object in bucket.

        Args:
            key: Key of object.

        Returns:
            Object in bucket.
        """
        return self.client.get_object(Bucket=self.name, Key=key)

    def __setitem__(self, key: str, value: 'BlobTypeDef', /) -> None:
        """Put object in bucket.

        Args:
            key: Key of object.
            value: Content of object.
        """
        self.client.put_object(Bucket=self.name, Key=key, Body=value)

    def __delitem__(self, key: str, /) -> None:
        """Delete object in bucket.

        Args:
            key: Key of object.
        """
        self.client.delete_object(Bucket=self.name, Key=key)

    def __iter__(self) -> Iterator['ObjectTypeDef']:
        """Iterates over objects in bucket.

        Returns:
            Iterator over objects.
        """
        response = self.client.list_objects_v2(Bucket=self.name)
        yield from response.get('Contents', [])
        while response['IsTruncated']:
            response = self.client.list_objects_v2(
                Bucket=self.name, ContinuationToken=response['NextContinuationToken']
            )
            yield from response.get('Contents', [])

    def prune(self) -> None:
        """Prune objects in bucket."""
        for obj in self:
            del self[obj['Key']]


@contextmanager
def s3_create_bucket(*, s3_client: 'S3Client', name: str | NoArgs = NoArgs.NO_ARG) -> Iterator[S3Bucket]:
    """Context for creating an S3 bucket and removing it on exit.

    Args:
        s3_client: S3 client where bucket will be created.
        name: Name of bucket to be created. If it is ``None`` a random name will be used.

    Return:
        Bucket created in S3 service.
    """
    if isinstance(name, NoArgs):
        name = randstr()

    s3_client.create_bucket(Bucket=name)
    yield S3Bucket(client=s3_client, name=name)
    for bucket_object in s3_client.list_objects_v2(Bucket=name).get('Contents', []):
        s3_client.delete_object(Bucket=name, Key=bucket_object['Key'])
    s3_client.delete_bucket(Bucket=name)
