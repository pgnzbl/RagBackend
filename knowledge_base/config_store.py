"""
配置持久化存储
使用JSON文件存储配置
"""
import json
import os
import logging
from typing import Optional
from pathlib import Path
import tempfile
import shutil

from .config import Config, EmbeddingConfig

logger = logging.getLogger(__name__)


class ConfigStore:
    """配置存储管理器"""
    
    def __init__(self, config_path: str = "./data/config.json"):
        """
        初始化配置存储
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"配置存储初始化，路径: {self.config_path}")
    
    def load(self) -> Config:
        """
        加载配置
        
        Returns:
            Config对象
        """
        if not self.config_path.exists():
            logger.info("配置文件不存在，返回空配置")
            return Config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析配置
            config = Config()
            if 'embedding' in data and data['embedding']:
                config.embedding = EmbeddingConfig(**data['embedding'])
            
            logger.info("配置加载成功")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON格式错误: {e}")
            # 备份损坏的配置文件
            backup_path = self.config_path.with_suffix('.json.bak')
            shutil.copy(self.config_path, backup_path)
            logger.warning(f"已备份损坏的配置文件到: {backup_path}")
            return Config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return Config()
    
    def save(self, config: Config) -> bool:
        """
        保存配置（原子性写入）
        
        Args:
            config: Config对象
            
        Returns:
            是否保存成功
        """
        try:
            # 更新时间戳
            if config.embedding:
                from datetime import datetime
                config.embedding.updated_at = datetime.now().isoformat()
            
            # 准备数据（不掩码API密钥）
            data = {
                'embedding': config.embedding.dict() if config.embedding else None
            }
            
            # 原子性写入：先写入临时文件，再重命名
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.config_dir,
                delete=False,
                suffix='.tmp'
            )
            
            try:
                json.dump(data, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_file.close()
                
                # 原子性替换
                shutil.move(temp_file.name, self.config_path)
                
                logger.info("配置保存成功")
                return True
                
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                raise e
                
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def update_embedding_config(self, embedding_config: EmbeddingConfig) -> bool:
        """
        更新Embedding配置
        
        Args:
            embedding_config: EmbeddingConfig对象
            
        Returns:
            是否更新成功
        """
        config = self.load()
        config.embedding = embedding_config
        return self.save(config)
    
    def get_embedding_config(self) -> Optional[EmbeddingConfig]:
        """
        获取Embedding配置
        
        Returns:
            EmbeddingConfig对象，如果不存在返回None
        """
        config = self.load()
        return config.embedding

