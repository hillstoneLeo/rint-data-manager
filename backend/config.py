import yaml
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = "config.yml"):
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)
    
    def get(self, key: str, default=None):
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
        return self._config.get('server', {})
    
    @property
    def database(self) -> Dict[str, Any]:
        return self._config.get('database', {})
    
    @property
    def dvc_config(self) -> Dict[str, Any]:
        """Get DVC configuration"""
        return self._config.get('dvc', {})
    
    @property
    def dvc_remote(self) -> Dict[str, Any]:
        """Backward compatibility - access remote server config through dvc section"""
        return self._config.get('dvc', {}).get('remote_server', {})
    
    @property
    def auth(self) -> Dict[str, Any]:
        return self._config.get('auth', {})
    
    @property
    def cors(self) -> Dict[str, Any]:
        return self._config.get('cors', {})
    
    @property
    def logging(self) -> Dict[str, Any]:
        return self._config.get('logging', {})
    
    def get_dvc_storage_path(self) -> str:
        """Get DVC storage path with backward compatibility"""
        # Try new unified structure first
        dvc_config = self._config.get('dvc', {})
        if 'storage_path' in dvc_config:
            return dvc_config['storage_path']
        
        # Fall back to old structure for backward compatibility
        if 'dvc_remote' in self._config:
            return self._config['dvc_remote'].get('storage_path', '/opt/dvc_storage')
        
        return '/opt/dvc_storage'

config = Config()