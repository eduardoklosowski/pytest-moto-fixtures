"""AWS settings."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from moto import mock_aws


@pytest.fixture
def aws_config() -> Iterator[None]:
    """Configure AWS mock."""
    config = {
        'AWS_DEFAULT_REGION': 'us-east-1',
    }
    with patch.dict('os.environ', config), mock_aws():
        yield
