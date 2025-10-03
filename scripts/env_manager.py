#!/usr/bin/env python3
"""
Environment Configuration Manager
PATTERN: Centralized secrets management with validation
WHY: Prevents configuration drift and ensures security compliance
"""

import os
import secrets
import string
import sys
from pathlib import Path
from typing import Dict, Optional
import argparse
import shutil
from datetime import datetime


class EnvManager:
    """
    CONCEPT: Separation of concerns - environment management isolated from application
    PATTERN: Builder pattern for environment configuration
    """
    
    def __init__(self, root_path: Path = Path.cwd()):
        self.root_path = root_path
        self.env_file = root_path / ".env"
        self.template_file = root_path / ".env.template"
        
    def generate_password(self, length: int = 32, include_special: bool = True) -> str:
        """
        WHY: Cryptographically secure password generation
        PATTERN: Use secrets module, not random, for security
        """
        alphabet = string.ascii_letters + string.digits
        if include_special:
            alphabet += "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_secret_key(self, length: int = 64) -> str:
        """
        CONCEPT: URL-safe tokens for API keys and secrets
        """
        return secrets.token_urlsafe(length)
    
    def create_env_from_template(self, environment: str = "development") -> bool:
        """
        PATTERN: Template method pattern - customize for each environment
        """
        if not self.template_file.exists():
            print(f"Error: Template file {self.template_file} not found")
            return False
        
        if self.env_file.exists():
            backup_name = f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(self.env_file, self.root_path / backup_name)
            print(f"Backed up existing .env to {backup_name}")
        
        # Read template
        with open(self.template_file, 'r') as f:
            content = f.read()
        
        # Generate secure values
        replacements = {
            "CHANGE_ME_USE_STRONG_PASSWORD": self.generate_password(),
            "CHANGE_ME_ADMIN_USERNAME": f"admin_{environment}",
            "CHANGE_ME_GENERATE_WITH_OPENSSL": self.generate_secret_key(),
            "CHANGE_ME_USE_STRONG_SECRET": self.generate_secret_key(),
        }
        
        # Apply replacements
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        # Set environment-specific values
        content = content.replace("ENVIRONMENT=development", f"ENVIRONMENT={environment}")
        if environment == "production":
            content = content.replace("DEBUG=true", "DEBUG=false")
            content = content.replace("LOG_LEVEL=INFO", "LOG_LEVEL=WARNING")
            content = content.replace("SECURE_COOKIES=false", "SECURE_COOKIES=true")
        
        # Write new .env file
        with open(self.env_file, 'w') as f:
            f.write(content)
        
        # Set restrictive permissions (Unix-like systems)
        if os.name != 'nt':  # Not Windows
            os.chmod(self.env_file, 0o600)
        
        print(f"Created .env file for {environment} environment")
        print("Generated secure passwords for all services")
        return True
    
    def validate_env(self) -> Dict[str, bool]:
        """
        PATTERN: Validation pattern - ensure all required vars are set
        WHY: Fail fast principle - catch config errors early
        """
        required_vars = [
            "POSTGRES_PASSWORD",
            "REDIS_PASSWORD", 
            "MINIO_ROOT_USER",
            "MINIO_ROOT_PASSWORD",
            "SUPERSET_SECRET_KEY",
            "GRAFANA_PASSWORD",
            "JWT_SECRET_KEY"
        ]
        
        if not self.env_file.exists():
            print(f"Error: {self.env_file} not found")
            return {}
        
        # Load environment variables
        env_vars = {}
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # Check each required variable
        results = {}
        for var in required_vars:
            if var in env_vars:
                value = env_vars[var]
                # Check for placeholder values
                is_valid = (
                    value and 
                    "CHANGE_ME" not in value and
                    len(value) >= 8
                )
                results[var] = is_valid
            else:
                results[var] = False
        
        return results
    
    def switch_environment(self, target_env: str) -> bool:
        """
        CONCEPT: Environment switching for multi-stage deployments
        """
        env_file_path = self.root_path / f".env.{target_env}"
        
        if not env_file_path.exists():
            print(f"Error: Environment file {env_file_path} not found")
            return False
        
        # Backup current .env
        if self.env_file.exists():
            backup_name = f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(self.env_file, self.root_path / backup_name)
            print(f"Backed up current .env to {backup_name}")
        
        # Copy target environment
        shutil.copy(env_file_path, self.env_file)
        print(f"Switched to {target_env} environment")
        return True


def main():
    """
    CLI interface for environment management
    PATTERN: Command pattern for different operations
    """
    parser = argparse.ArgumentParser(description="Environment Configuration Manager")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize environment from template')
    init_parser.add_argument('--env', default='development', 
                            choices=['development', 'staging', 'production'],
                            help='Target environment')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate environment configuration')
    
    # Switch command
    switch_parser = subparsers.add_parser('switch', help='Switch to different environment')
    switch_parser.add_argument('environment', choices=['development', 'staging', 'production'])
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate secure passwords')
    gen_parser.add_argument('--length', type=int, default=32, help='Password length')
    gen_parser.add_argument('--count', type=int, default=1, help='Number of passwords')
    
    args = parser.parse_args()
    
    manager = EnvManager()
    
    if args.command == 'init':
        success = manager.create_env_from_template(args.env)
        sys.exit(0 if success else 1)
    
    elif args.command == 'validate':
        results = manager.validate_env()
        if not results:
            sys.exit(1)
        
        all_valid = True
        for var, is_valid in results.items():
            status = "✓" if is_valid else "✗"
            print(f"{status} {var}: {'Valid' if is_valid else 'Invalid or missing'}")
            if not is_valid:
                all_valid = False
        
        if all_valid:
            print("\n✓ All environment variables are properly configured")
        else:
            print("\n✗ Some environment variables need attention")
        
        sys.exit(0 if all_valid else 1)
    
    elif args.command == 'switch':
        success = manager.switch_environment(args.environment)
        sys.exit(0 if success else 1)
    
    elif args.command == 'generate':
        print("Generated secure passwords:")
        for i in range(args.count):
            pwd = manager.generate_password(args.length)
            print(f"  {i+1}. {pwd}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()