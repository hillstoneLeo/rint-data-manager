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
    def dvc(self) -> Dict[str, Any]:
        return self._config.get('dvc', {})
    
    @property
    def upload(self) -> Dict[str, Any]:
        return self._config.get('upload', {})
    
    @property
    def auth(self) -> Dict[str, Any]:
        return self._config.get('auth', {})
    
    @property
    def cors(self) -> Dict[str, Any]:
        return self._config.get('cors', {})
    
    @property
    def logging(self) -> Dict[str, Any]:
        return self._config.get('logging', {})

config = Config()