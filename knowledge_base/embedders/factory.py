"""
Embedder工厂类
根据配置创建对应的Embedder实例
"""
from typing import Dict, Any, Optional
import logging

from .base import BaseEmbedder
from .tongyi import TongyiEmbedder

logger = logging.getLogger(__name__)


class EmbedderFactory:
    """Embedder工厂类"""
    
    # 支持的提供商映射
    PROVIDERS = {
        'tongyi': TongyiEmbedder,
        # 可以扩展其他提供商
        # 'openai': OpenAIEmbedder,
        # 'custom': CustomEmbedder,
    }
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> BaseEmbedder:
        """
        创建Embedder实例
        
        Args:
            config: 配置字典，必须包含provider字段
            
        Returns:
            BaseEmbedder实例
            
        Raises:
            ValueError: 不支持的提供商
        """
        provider = config.get('provider', '').lower()
        
        if provider not in cls.PROVIDERS:
            supported = ', '.join(cls.PROVIDERS.keys())
            raise ValueError(f"不支持的embedding提供商: {provider}。支持的提供商: {supported}")
        
        embedder_class = cls.PROVIDERS[provider]
        
        try:
            embedder = embedder_class(config)
            logger.info(f"创建{provider} Embedder成功")
            return embedder
        except Exception as e:
            logger.error(f"创建{provider} Embedder失败: {e}")
            raise
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """
        获取支持的提供商列表
        
        Returns:
            提供商名称列表
        """
        return list(cls.PROVIDERS.keys())

