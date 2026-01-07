"""
Embedder抽象基类
定义统一的接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Embedder抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Embedder
        
        Args:
            config: 配置字典，包含api_key, model, base_url等
        """
        self.config = config
        self.provider = config.get('provider', 'unknown')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', '')
        self.base_url = config.get('base_url')
        
    @abstractmethod
    def embed(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """
        生成文本向量
        
        Args:
            texts: 文本列表
            batch_size: 批量大小（可选）
            
        Returns:
            向量列表，每个元素是一个float列表
        """
        pass
    
    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """
        生成查询向量（单条）
        
        Args:
            query: 查询文本
            
        Returns:
            向量（float列表）
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        测试API连接
        
        Returns:
            包含测试结果的字典，至少包含: success, dimension, message
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> Optional[int]:
        """
        获取向量维度
        
        Returns:
            向量维度，如果无法获取返回None
        """
        pass
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置（热更新）
        
        Args:
            config: 新的配置字典
        """
        self.config = config
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', '')
        self.base_url = config.get('base_url')

