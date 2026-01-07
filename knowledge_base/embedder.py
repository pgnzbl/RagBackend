"""
Embedding模型封装
固定使用通义千问模型，从环境变量读取配置
"""
from typing import List, Optional, Dict, Any
import logging
import os

# 导入新的embedder系统
from .embedders.factory import EmbedderFactory
from .embedders.base import BaseEmbedder

logger = logging.getLogger(__name__)


class Embedder:
    """Embedding模型封装（固定使用通义千问）"""
    
    _instance = None
    _embedder: Optional[BaseEmbedder] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化Embedder（从环境变量加载）"""
        if Embedder._embedder is None:
            self._load_embedder()
    
    def _load_embedder(self):
        """从环境变量加载embedder"""
        try:
            # 从环境变量读取API key
            api_key = os.getenv("DASHSCOPE_API_KEY","sk-9c911e9558404bd4b83ebb61302fc8e3")
            if not api_key:
                raise RuntimeError(
                    "未设置DASHSCOPE_API_KEY环境变量。"
                    "请设置环境变量: export DASHSCOPE_API_KEY=your_api_key"
                )
            
            # 从环境变量读取可选配置
            base_url = os.getenv(
                "TONGYI_API_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            model = os.getenv("TONGYI_EMBEDDING_MODEL", "text-embedding-v4")
            
            # 创建embedder实例（固定使用通义千问）
            embedder_config = {
                'provider': 'tongyi',
                'api_key': api_key,
                'model': model,
                'base_url': base_url
            }
            
            Embedder._embedder = EmbedderFactory.create(embedder_config)
            
            logger.info(f"Embedding模型加载成功: tongyi/{model}")
            
        except Exception as e:
            logger.error(f"加载embedding模型失败: {e}")
            raise
    
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表，每个元素是一个float列表
        """
        if Embedder._embedder is None:
            raise RuntimeError("Embedding模型未初始化")
        
        try:
            return Embedder._embedder.embed(texts)
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            raise
    
    def embed_query(self, query: str) -> List[float]:
        """
        生成查询向量（单条）
        
        Args:
            query: 查询文本
            
        Returns:
            向量（float列表）
        """
        return self.embed([query])[0]
    
    def get_dimension(self) -> Optional[int]:
        """
        获取向量维度
        
        Returns:
            向量维度
        """
        if Embedder._embedder:
            return Embedder._embedder.get_dimension()
        return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接
        
        Returns:
            测试结果
        """
        if Embedder._embedder:
            return Embedder._embedder.test_connection()
        return {"success": False, "message": "Embedder未初始化"}
