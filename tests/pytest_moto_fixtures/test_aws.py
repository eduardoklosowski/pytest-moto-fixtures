import os


def test_aws_config(aws_config: None) -> None:
    assert os.environ['AWS_DEFAULT_REGION'] == 'us-east-1'
