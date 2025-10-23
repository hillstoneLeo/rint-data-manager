import yaml
import os
from pathlib import Path
from typing import Dict, Any, Union
from dotenv import load_dotenv


class Config:

    def __init__(self, config_path: str = "config.yml"):
        self.config_path = config_path
        # Load .env file if it exists
        load_dotenv()
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

    def _get_env_override(self, key: str) -> Union[str, None]:
        """Get environment variable override for a configuration key.
        
        Environment variables follow the pattern: RINT_{SECTION}_{KEY}
        For nested keys like 'server.host', the env var is RINT_SERVER_HOST
        """
        # Convert dot notation to env var format
        env_key = f"RINT_{key.upper().replace('.', '_')}"
        return os.getenv(env_key)

    def get(self, key: str, default=None):
        """Get configuration value with environment variable override.
        
        Priority:
        1. Environment variable (RINT_SECTION_KEY)
        2. Configuration file value
        3. Default value
        """
        # Check environment variable first
        env_value = self._get_env_override(key)
        if env_value is not None:
            # Try to convert to appropriate type
            if isinstance(default, bool):
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default, int):
                try:
                    return int(env_value)
                except ValueError:
                    return default
            elif isinstance(default, float):
                try:
                    return float(env_value)
                except ValueError:
                    return default
            elif isinstance(default, list):
                # Split comma-separated values for lists
                return [item.strip() for item in env_value.split(',') if item.strip()]
            return env_value

        # Fall back to config file
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def server(self) -> Dict[str, Any]:
        """Get server configuration with environment variable overrides"""
        config = self._config.get('server', {})
        return {
            'host': self.get('server.host', config.get('host', '0.0.0.0')),
            'port': self.get('server.port', config.get('port', 8000)),
            'debug': self.get('server.debug', config.get('debug', True)),
            'reload': self.get('server.reload', config.get('reload', True)),
        }

    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration with environment variable overrides"""
        config = self._config.get('database', {})
        return {
            'url': self.get('database.url', config.get('url', 'sqlite:///rint_data_manager.db')),
            'echo': self.get('database.echo', config.get('echo', False)),
        }

    @property
    def dvc_config(self) -> Dict[str, Any]:
        """Get DVC configuration with environment variable overrides"""
        config = self._config.get('dvc', {})
        return {
            'storage_path': self.get('dvc.storage_path', config.get('storage_path', 'dvc_storage')),
            'remote_name': self.get('dvc.remote_name', config.get('remote_name', 'local_storage')),
            'uploads_dvc_project': self.get('dvc.uploads_dvc_project', config.get('uploads_dvc_project', '/tmp/rdm/uploads')),
            'upload_directory': self.get('dvc.upload_directory', config.get('upload_directory', '/tmp/rdm/uploads')),
            'max_file_size': self.get('dvc.max_file_size', config.get('max_file_size', 104857600)),
            'allowed_extensions': self.get('dvc.allowed_extensions', config.get('allowed_extensions', [".csv", ".json", ".txt", ".xlsx", ".parquet", ".h5", ".pkl", ".py", ".ipynb"])),
            'remote_server': self.dvc_remote,
        }

    @property
    def dvc_remote(self) -> Dict[str, Any]:
        """Get DVC remote server configuration with environment variable overrides"""
        config = self._config.get('dvc', {}).get('remote_server', {})
        return {
            'enabled': self.get('dvc.remote_server.enabled', config.get('enabled', True)),
            'auth': {
                'enabled': self.get('dvc.remote_server.auth.enabled', config.get('auth', {}).get('enabled', True)),
                'method': self.get('dvc.remote_server.auth.method', config.get('auth', {}).get('method', 'database')),
                'database_auth': {
                    'require_admin': self.get('dvc.remote_server.auth.database_auth.require_admin', config.get('auth', {}).get('database_auth', {}).get('require_admin', False)),
                    'allowed_users': self.get('dvc.remote_server.auth.database_auth.allowed_users', config.get('auth', {}).get('database_auth', {}).get('allowed_users', [])),
                },
                'basic_auth': {
                    'username': self.get('dvc.remote_server.auth.basic_auth.username', config.get('auth', {}).get('basic_auth', {}).get('username', 'dvc_user')),
                    'password': self.get('dvc.remote_server.auth.basic_auth.password', config.get('auth', {}).get('basic_auth', {}).get('password', 'dvc_password')),
                },
                'custom_auth': {
                    'header_name': self.get('dvc.remote_server.auth.custom_auth.header_name', config.get('auth', {}).get('custom_auth', {}).get('header_name', 'X-DVC-Token')),
                    'token': self.get('dvc.remote_server.auth.custom_auth.token', config.get('auth', {}).get('custom_auth', {}).get('token', 'your-custom-token-here')),
                },
            },
            'ssl_verify': self.get('dvc.remote_server.ssl_verify', config.get('ssl_verify', True)),
            'read_timeout': self.get('dvc.remote_server.read_timeout', config.get('read_timeout', 300)),
            'connect_timeout': self.get('dvc.remote_server.connect_timeout', config.get('connect_timeout', 300)),
        }

    @property
    def auth(self) -> Dict[str, Any]:
        """Get authentication configuration with environment variable overrides"""
        config = self._config.get('auth', {})
        return {
            'jwt_secret_key': self.get('auth.jwt_secret_key', config.get('jwt_secret_key', 'your-secret-key-here-change-in-production')),
            'jwt_algorithm': self.get('auth.jwt_algorithm', config.get('jwt_algorithm', 'HS256')),
            'jwt_expiration_minutes': self.get('auth.jwt_expiration_minutes', config.get('jwt_expiration_minutes', 1440)),
            'password_min_length': self.get('auth.password_min_length', config.get('password_min_length', 8)),
            'email_suffix_regex': self.get('auth.email_suffix_regex', config.get('email_suffix_regex', '.*@hillstonenet\\.com$|.*@Hillstonenet\\.com$')),
        }

    @property
    def cors(self) -> Dict[str, Any]:
        """Get CORS configuration with environment variable overrides"""
        config = self._config.get('cors', {})
        return {
            'allowed_origins': self.get('cors.allowed_origins', config.get('allowed_origins', ["http://localhost:8000", "http://127.0.0.1:8000"])),
            'allowed_methods': self.get('cors.allowed_methods', config.get('allowed_methods', ["GET", "POST", "PUT", "DELETE", "OPTIONS"])),
            'allowed_headers': self.get('cors.allowed_headers', config.get('allowed_headers', ["*"])),
        }

    @property
    def logging(self) -> Dict[str, Any]:
        """Get logging configuration with environment variable overrides"""
        config = self._config.get('logging', {})
        return {
            'level': self.get('logging.level', config.get('level', 'INFO')),
            'format': self.get('logging.format', config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')),
            'file': self.get('logging.file', config.get('file', 'log/app.log')),
        }

    @property
    def timing_debug(self) -> Dict[str, Any]:
        """Get timing debug configuration with environment variable overrides"""
        config = self._config.get('timing_debug', {})
        return {
            'enabled': self.get('timing_debug.enabled', config.get('enabled', False)),
            'log_level': self.get('timing_debug.log_level', config.get('log_level', 'INFO')),
            'include_frontend': self.get('timing_debug.include_frontend', config.get('include_frontend', False)),
        }

    def get_timing_debug_enabled(self) -> bool:
        """Get timing debug enabled setting with environment variable override"""
        return bool(self.get('timing_debug.enabled', False))

    def get_timing_debug_log_level(self) -> str:
        """Get timing debug log level with environment variable override"""
        return str(self.get('timing_debug.log_level', 'INFO')).upper()

    def get_timing_debug_include_frontend(self) -> bool:
        """Get timing debug include frontend setting with environment variable override"""
        return bool(self.get('timing_debug.include_frontend', False))

    def get_dvc_storage_path(self) -> str:
        """Get DVC storage path with backward compatibility"""
        # Try new unified structure first
        dvc_config = self._config.get('dvc', {})
        if 'storage_path' in dvc_config:
            return dvc_config['storage_path']

        # Fall back to old structure for backward compatibility
        if 'dvc_remote' in self._config:
            return self._config['dvc_remote'].get('storage_path',
                                                  '/opt/dvc_storage')

        return '/opt/dvc_storage'


config = Config()