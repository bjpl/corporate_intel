"""
HashiCorp Vault Integration for Secrets Management

This module provides integration with HashiCorp Vault for secure secrets management.
Supports both KV v1 and KV v2 secret engines.

Usage:
    # Initialize and load secrets
    vault = VaultSecretsManager()
    vault.load_secrets_to_env('secret/corporate-intel/production')

    # Or get specific secret
    password = vault.get_secret('secret/data/db', 'postgres_password')
"""

import os
import sys
from typing import Any, Dict, Optional
from pathlib import Path

try:
    import hvac
    from hvac.exceptions import VaultError, InvalidPath
except ImportError:
    print("ERROR: hvac library not installed. Install with: pip install hvac")
    sys.exit(1)


class VaultSecretsManager:
    """Manages secrets retrieval from HashiCorp Vault."""

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        vault_role_id: Optional[str] = None,
        vault_secret_id: Optional[str] = None,
    ):
        """
        Initialize Vault client.

        Args:
            vault_addr: Vault server address (default: VAULT_ADDR env var)
            vault_token: Vault token (default: VAULT_TOKEN env var)
            vault_role_id: AppRole role ID for authentication
            vault_secret_id: AppRole secret ID for authentication
        """
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR', 'http://127.0.0.1:8200')
        self.client = hvac.Client(url=self.vault_addr)

        # Authenticate using token or AppRole
        if vault_token or os.getenv('VAULT_TOKEN'):
            token = vault_token or os.getenv('VAULT_TOKEN')
            self.client.token = token
        elif vault_role_id or os.getenv('VAULT_ROLE_ID'):
            self._authenticate_approle(
                vault_role_id or os.getenv('VAULT_ROLE_ID'),
                vault_secret_id or os.getenv('VAULT_SECRET_ID')
            )
        else:
            raise ValueError(
                "No authentication method provided. Set VAULT_TOKEN or "
                "VAULT_ROLE_ID/VAULT_SECRET_ID environment variables."
            )

        # Verify authentication
        if not self.client.is_authenticated():
            raise VaultError("Failed to authenticate with Vault")

    def _authenticate_approle(self, role_id: str, secret_id: str) -> None:
        """Authenticate using AppRole method."""
        try:
            response = self.client.auth.approle.login(
                role_id=role_id,
                secret_id=secret_id,
            )
            self.client.token = response['auth']['client_token']
        except Exception as e:
            raise VaultError(f"AppRole authentication failed: {e}")

    def get_secret(
        self,
        secret_path: str,
        secret_key: Optional[str] = None,
        mount_point: str = 'secret',
    ) -> Any:
        """
        Retrieve a secret from Vault.

        Args:
            secret_path: Path to the secret (e.g., 'corporate-intel/production')
            secret_key: Specific key to retrieve (returns all if None)
            mount_point: Vault mount point (default: 'secret')

        Returns:
            Secret value or dictionary of all secrets at path
        """
        try:
            # Try KV v2 first (most common)
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=mount_point,
            )
            data = response['data']['data']
        except (InvalidPath, KeyError):
            try:
                # Fall back to KV v1
                response = self.client.secrets.kv.v1.read_secret(
                    path=secret_path,
                    mount_point=mount_point,
                )
                data = response['data']
            except Exception as e:
                raise VaultError(f"Failed to read secret from {secret_path}: {e}")

        if secret_key:
            if secret_key not in data:
                raise KeyError(f"Secret key '{secret_key}' not found at {secret_path}")
            return data[secret_key]
        return data

    def set_secret(
        self,
        secret_path: str,
        secrets: Dict[str, Any],
        mount_point: str = 'secret',
    ) -> None:
        """
        Store secrets in Vault.

        Args:
            secret_path: Path where secrets will be stored
            secrets: Dictionary of key-value pairs to store
            mount_point: Vault mount point (default: 'secret')
        """
        try:
            # Try KV v2
            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_path,
                secret=secrets,
                mount_point=mount_point,
            )
        except Exception:
            try:
                # Fall back to KV v1
                self.client.secrets.kv.v1.create_or_update_secret(
                    path=secret_path,
                    secret=secrets,
                    mount_point=mount_point,
                )
            except Exception as e:
                raise VaultError(f"Failed to write secret to {secret_path}: {e}")

    def load_secrets_to_env(
        self,
        secret_path: str,
        mount_point: str = 'secret',
        prefix: str = '',
    ) -> Dict[str, str]:
        """
        Load secrets from Vault into environment variables.

        Args:
            secret_path: Path to secrets in Vault
            mount_point: Vault mount point
            prefix: Optional prefix for environment variables

        Returns:
            Dictionary of loaded secrets
        """
        secrets = self.get_secret(secret_path, mount_point=mount_point)

        loaded = {}
        for key, value in secrets.items():
            env_var = f"{prefix}{key.upper()}" if prefix else key.upper()
            os.environ[env_var] = str(value)
            loaded[env_var] = str(value)

        return loaded

    def rotate_secret(
        self,
        secret_path: str,
        secret_key: str,
        new_value: str,
        mount_point: str = 'secret',
    ) -> None:
        """
        Rotate a specific secret value.

        Args:
            secret_path: Path to the secret
            secret_key: Key to rotate
            new_value: New secret value
            mount_point: Vault mount point
        """
        # Get current secrets
        current_secrets = self.get_secret(secret_path, mount_point=mount_point)

        # Update specific key
        current_secrets[secret_key] = new_value

        # Write back to Vault
        self.set_secret(secret_path, current_secrets, mount_point=mount_point)

    def get_database_url(
        self,
        secret_path: str = 'corporate-intel/production',
        mount_point: str = 'secret',
    ) -> str:
        """
        Construct database URL from Vault secrets.

        Args:
            secret_path: Path to database secrets
            mount_point: Vault mount point

        Returns:
            Database connection URL
        """
        secrets = self.get_secret(secret_path, mount_point=mount_point)

        user = secrets.get('postgres_user', 'intel_user')
        password = secrets.get('postgres_password')
        host = secrets.get('postgres_host', 'localhost')
        port = secrets.get('postgres_port', '5432')
        database = secrets.get('postgres_db', 'corporate_intel')

        if not password:
            raise ValueError("postgres_password not found in Vault")

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def main():
    """CLI for Vault integration."""
    import argparse

    parser = argparse.ArgumentParser(description='Vault Secrets Manager')
    parser.add_argument('action', choices=['load', 'get', 'set', 'rotate'],
                       help='Action to perform')
    parser.add_argument('--path', default='corporate-intel/production',
                       help='Secret path in Vault')
    parser.add_argument('--key', help='Specific secret key')
    parser.add_argument('--value', help='Secret value (for set/rotate)')
    parser.add_argument('--mount', default='secret', help='Vault mount point')

    args = parser.parse_args()

    try:
        vault = VaultSecretsManager()

        if args.action == 'load':
            secrets = vault.load_secrets_to_env(args.path, mount_point=args.mount)
            print(f"Loaded {len(secrets)} secrets to environment variables")
            for key in secrets:
                print(f"  - {key}")

        elif args.action == 'get':
            if args.key:
                value = vault.get_secret(args.path, args.key, mount_point=args.mount)
                print(f"{args.key}: {value}")
            else:
                secrets = vault.get_secret(args.path, mount_point=args.mount)
                print(f"Secrets at {args.path}:")
                for key in secrets:
                    print(f"  - {key}")

        elif args.action == 'set':
            if not args.key or not args.value:
                print("ERROR: --key and --value required for set action")
                sys.exit(1)
            vault.set_secret(args.path, {args.key: args.value}, mount_point=args.mount)
            print(f"Secret {args.key} set at {args.path}")

        elif args.action == 'rotate':
            if not args.key or not args.value:
                print("ERROR: --key and --value required for rotate action")
                sys.exit(1)
            vault.rotate_secret(args.path, args.key, args.value, mount_point=args.mount)
            print(f"Secret {args.key} rotated at {args.path}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
