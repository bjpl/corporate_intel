"""
AWS Secrets Manager Integration

This module provides integration with AWS Secrets Manager for secure secrets management.
Supports automatic secret rotation and fine-grained IAM permissions.

Usage:
    # Initialize and load secrets
    aws_secrets = AWSSecretsManager(region_name='us-east-1')
    aws_secrets.load_secrets_to_env('corporate-intel/production')

    # Or get specific secret
    password = aws_secrets.get_secret('corporate-intel/production/postgres-password')
"""

import os
import sys
import json
from typing import Any, Dict, Optional
from base64 import b64decode

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("ERROR: boto3 library not installed. Install with: pip install boto3")
    sys.exit(1)


class AWSSecretsManager:
    """Manages secrets retrieval from AWS Secrets Manager."""

    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        profile_name: Optional[str] = None,
    ):
        """
        Initialize AWS Secrets Manager client.

        Args:
            region_name: AWS region (default: AWS_DEFAULT_REGION env var or us-east-1)
            aws_access_key_id: AWS access key (optional, uses AWS credentials chain)
            aws_secret_access_key: AWS secret key (optional)
            profile_name: AWS profile name (optional)
        """
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

        session_kwargs = {'region_name': self.region_name}
        if profile_name:
            session_kwargs['profile_name'] = profile_name
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs['aws_access_key_id'] = aws_access_key_id
            session_kwargs['aws_secret_access_key'] = aws_secret_access_key

        try:
            session = boto3.session.Session(**session_kwargs)
            self.client = session.client('secretsmanager')
        except NoCredentialsError:
            raise ValueError(
                "No AWS credentials found. Configure AWS credentials using:\n"
                "  - AWS CLI: aws configure\n"
                "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                "  - IAM role (if running on EC2/ECS/Lambda)\n"
                "  - AWS profile: specify profile_name parameter"
            )

    def get_secret(self, secret_name: str, version_stage: str = 'AWSCURRENT') -> Any:
        """
        Retrieve a secret from AWS Secrets Manager.

        Args:
            secret_name: Name or ARN of the secret
            version_stage: Version stage (default: AWSCURRENT)

        Returns:
            Secret value (string or dict if JSON)

        Raises:
            ClientError: If secret not found or access denied
        """
        try:
            response = self.client.get_secret_value(
                SecretId=secret_name,
                VersionStage=version_stage
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ValueError(f"Secret '{secret_name}' not found")
            elif error_code == 'InvalidRequestException':
                raise ValueError(f"Invalid request for secret '{secret_name}'")
            elif error_code == 'InvalidParameterException':
                raise ValueError(f"Invalid parameter for secret '{secret_name}'")
            elif error_code == 'DecryptionFailure':
                raise RuntimeError(f"Failed to decrypt secret '{secret_name}'")
            elif error_code == 'AccessDeniedException':
                raise PermissionError(f"Access denied to secret '{secret_name}'")
            else:
                raise

        # Decrypt secret
        if 'SecretString' in response:
            secret = response['SecretString']
            # Try to parse as JSON
            try:
                return json.loads(secret)
            except json.JSONDecodeError:
                return secret
        else:
            # Binary secret
            return b64decode(response['SecretBinary'])

    def set_secret(
        self,
        secret_name: str,
        secret_value: Any,
        description: Optional[str] = None,
        kms_key_id: Optional[str] = None,
    ) -> str:
        """
        Create or update a secret in AWS Secrets Manager.

        Args:
            secret_name: Name of the secret
            secret_value: Value to store (string or dict)
            description: Optional description
            kms_key_id: Optional KMS key ID for encryption

        Returns:
            Secret ARN
        """
        # Convert dict to JSON string
        if isinstance(secret_value, dict):
            secret_string = json.dumps(secret_value)
        else:
            secret_string = str(secret_value)

        create_kwargs = {
            'Name': secret_name,
            'SecretString': secret_string,
        }
        if description:
            create_kwargs['Description'] = description
        if kms_key_id:
            create_kwargs['KmsKeyId'] = kms_key_id

        try:
            # Try to create new secret
            response = self.client.create_secret(**create_kwargs)
            return response['ARN']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                # Secret exists, update it
                response = self.client.update_secret(
                    SecretId=secret_name,
                    SecretString=secret_string,
                )
                return response['ARN']
            else:
                raise

    def load_secrets_to_env(
        self,
        secret_prefix: str,
        mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Load secrets from AWS Secrets Manager into environment variables.

        Args:
            secret_prefix: Common prefix for secret names (e.g., 'corporate-intel/production')
            mapping: Optional dict mapping secret names to env var names
                    If None, uses default mapping for common secrets

        Returns:
            Dictionary of loaded secrets (keys are env var names)
        """
        default_mapping = {
            f'{secret_prefix}/postgres-password': 'POSTGRES_PASSWORD',
            f'{secret_prefix}/redis-password': 'REDIS_PASSWORD',
            f'{secret_prefix}/minio-access-key': 'MINIO_ACCESS_KEY',
            f'{secret_prefix}/minio-secret-key': 'MINIO_SECRET_KEY',
            f'{secret_prefix}/secret-key': 'SECRET_KEY',
            f'{secret_prefix}/superset-secret': 'SUPERSET_SECRET_KEY',
            f'{secret_prefix}/grafana-password': 'GRAFANA_PASSWORD',
        }

        secret_mapping = mapping or default_mapping
        loaded = {}

        for secret_name, env_var in secret_mapping.items():
            try:
                secret_value = self.get_secret(secret_name)

                # Handle JSON secrets
                if isinstance(secret_value, dict):
                    # For JSON secrets, load each key as separate env var
                    for key, value in secret_value.items():
                        env_key = f"{env_var}_{key.upper()}"
                        os.environ[env_key] = str(value)
                        loaded[env_key] = str(value)
                else:
                    os.environ[env_var] = str(secret_value)
                    loaded[env_var] = str(secret_value)

            except ValueError as e:
                # Secret not found - skip and continue
                print(f"Warning: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"Error loading secret {secret_name}: {e}", file=sys.stderr)
                raise

        if not loaded:
            raise ValueError(f"No secrets found with prefix '{secret_prefix}'")

        return loaded

    def rotate_secret(
        self,
        secret_name: str,
        new_value: Any,
    ) -> str:
        """
        Rotate a secret value.

        Args:
            secret_name: Name of the secret
            new_value: New secret value

        Returns:
            Secret version ID
        """
        secret_string = json.dumps(new_value) if isinstance(new_value, dict) else str(new_value)

        response = self.client.update_secret(
            SecretId=secret_name,
            SecretString=secret_string,
        )
        return response['VersionId']

    def enable_rotation(
        self,
        secret_name: str,
        lambda_arn: str,
        rotation_days: int = 30,
    ) -> None:
        """
        Enable automatic rotation for a secret.

        Args:
            secret_name: Name of the secret
            lambda_arn: ARN of Lambda function to perform rotation
            rotation_days: Number of days between rotations
        """
        self.client.rotate_secret(
            SecretId=secret_name,
            RotationLambdaARN=lambda_arn,
            RotationRules={
                'AutomaticallyAfterDays': rotation_days,
            }
        )

    def list_secrets(self, prefix: Optional[str] = None) -> list:
        """
        List all secrets, optionally filtered by prefix.

        Args:
            prefix: Optional name prefix to filter

        Returns:
            List of secret metadata dicts
        """
        kwargs = {}
        if prefix:
            kwargs['Filters'] = [{'Key': 'name', 'Values': [prefix]}]

        secrets = []
        paginator = self.client.get_paginator('list_secrets')

        for page in paginator.paginate(**kwargs):
            secrets.extend(page['SecretList'])

        return secrets

    def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int = 30,
        force: bool = False,
    ) -> None:
        """
        Delete a secret.

        Args:
            secret_name: Name of the secret
            recovery_window_days: Days before permanent deletion (7-30)
            force: If True, delete immediately without recovery
        """
        kwargs = {'SecretId': secret_name}

        if force:
            kwargs['ForceDeleteWithoutRecovery'] = True
        else:
            kwargs['RecoveryWindowInDays'] = recovery_window_days

        self.client.delete_secret(**kwargs)


def main():
    """CLI for AWS Secrets Manager integration."""
    import argparse

    parser = argparse.ArgumentParser(description='AWS Secrets Manager Integration')
    parser.add_argument('action', choices=['load', 'get', 'set', 'list', 'rotate'],
                       help='Action to perform')
    parser.add_argument('--name', help='Secret name')
    parser.add_argument('--prefix', help='Secret name prefix (for load/list)')
    parser.add_argument('--value', help='Secret value (for set/rotate)')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')

    args = parser.parse_args()

    try:
        aws_secrets = AWSSecretsManager(
            region_name=args.region,
            profile_name=args.profile,
        )

        if args.action == 'load':
            if not args.prefix:
                print("ERROR: --prefix required for load action")
                sys.exit(1)
            secrets = aws_secrets.load_secrets_to_env(args.prefix)
            print(f"Loaded {len(secrets)} secrets to environment variables:")
            for key in secrets:
                print(f"  - {key}")

        elif args.action == 'get':
            if not args.name:
                print("ERROR: --name required for get action")
                sys.exit(1)
            value = aws_secrets.get_secret(args.name)
            if isinstance(value, dict):
                print(f"Secret '{args.name}':")
                for key, val in value.items():
                    print(f"  {key}: {val}")
            else:
                print(f"{args.name}: {value}")

        elif args.action == 'set':
            if not args.name or not args.value:
                print("ERROR: --name and --value required for set action")
                sys.exit(1)
            arn = aws_secrets.set_secret(args.name, args.value)
            print(f"Secret set: {arn}")

        elif args.action == 'list':
            secrets = aws_secrets.list_secrets(prefix=args.prefix)
            print(f"Found {len(secrets)} secrets:")
            for secret in secrets:
                print(f"  - {secret['Name']}")
                if 'Description' in secret:
                    print(f"    Description: {secret['Description']}")

        elif args.action == 'rotate':
            if not args.name or not args.value:
                print("ERROR: --name and --value required for rotate action")
                sys.exit(1)
            version_id = aws_secrets.rotate_secret(args.name, args.value)
            print(f"Secret rotated: {version_id}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
