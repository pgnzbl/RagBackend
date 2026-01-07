"""
通义千问Embedding实现
使用OpenAI兼容的API接口
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI
import logging
import os

from .base import BaseEmbedder

logger = logging.getLogger(__name__)


class TongyiEmbedder(BaseEmbedder):
    """通义千问Embedding实现（使用OpenAI兼容接口）"""
    
    # 通义千问默认API地址（北京地域）
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化通义千问Embedder
        
        Args:
            config: 配置字典，包含api_key, model, base_url(可选)
        """
        super().__init__(config)
        
        # 使用配置的base_url或默认地址
        if not self.base_url:
            self.base_url = os.getenv("TONGYI_API_BASE_URL", self.DEFAULT_BASE_URL)
        
        # 默认模型（使用最新的v4版本）
        if not self.model:
            self.model = "text-embedding-v4"
        
        # 创建OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        logger.info(f"通义千问Embedder初始化: model={self.model}, base_url={self.base_url}")
    
    def _call_api(self, texts: List[str]) -> List[List[float]]:
        """
        调用通义千问Embedding API
        
        Args:
            texts: 文本列表（单个或多个）
            
        Returns:
            向量列表
        """
        try:
            # 根据文本数量选择调用方式
            if len(texts) == 1:
                # 单个文本
                input_data = texts[0]
            else:
                # 多个文本
                input_data = texts
            
            # 调用OpenAI兼容的embeddings API
            response = self.client.embeddings.create(
                model=self.model,
                input=input_data
            )
            
            # 解析返回结果
            # OpenAI兼容格式:
            # {
            #   "data": [
            #     {"embedding": [0.1, 0.2, ...], "index": 0},
            #     ...
            #   ],
            #   "model": "text-embedding-v4",
            #   "usage": {...}
            # }
            
            if hasattr(response, 'data') and response.data:
                embeddings = []
                # 确保按index排序
                sorted_data = sorted(response.data, key=lambda x: x.index)
                for item in sorted_data:
                    if hasattr(item, 'embedding'):
                        embeddings.append(item.embedding)
                    else:
                        # 兼容字典格式
                        embeddings.append(item.get('embedding', []))
                return embeddings
            else:
                raise ValueError(f"API返回格式异常: {response}")
                
        except Exception as e:
            error_msg = f"调用通义千问API失败: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def embed(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """
        生成文本向量（批量处理，支持API批量限制）
        
        Args:
            texts: 文本列表
            batch_size: 每批处理的文本数量（默认10，通义千问API限制）
            
        Returns:
            向量列表，每个元素是一个float列表
        """
        if not texts:
            return []
        
        if batch_size is None:
            batch_size = 10  # 通义千问API限制：每批最多10个文本
        
        all_embeddings = []
        
        # 分批处理，避免超过API限制
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"正在生成向量: 批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}, 文本数: {len(batch)}")
            
            try:
                batch_embeddings = self._call_api(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"批次 {i//batch_size + 1} 处理失败: {e}")
                raise
        
        logger.info(f"成功生成 {len(all_embeddings)} 个向量")
        return all_embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        生成查询向量（单条）
        
        Args:
            query: 查询文本
            
        Returns:
            向量（float列表）
        """
        return self.embed([query])[0]
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试API连接
        
        Returns:
            包含测试结果的字典: {success: bool, dimension: int, message: str}
        """
        try:
            test_text = "测试连接"
            embeddings = self._call_api([test_text])
            
            if not embeddings or not embeddings[0]:
                return {
                    "success": False,
                    "dimension": None,
                    "message": "API返回空向量"
                }
            
            dimension = len(embeddings[0])
            
            return {
                "success": True,
                "dimension": dimension,
                "message": f"连接成功，向量维度: {dimension}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "dimension": None,
                "message": f"连接失败: {str(e)}"
            }
    
    def get_dimension(self) -> Optional[int]:
        """
        获取向量维度（通过测试连接获取）
        
        Returns:
            向量维度，如果无法获取返回None
        """
        result = self.test_connection()
        return result.get("dimension") if result.get("success") else None
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置（热更新）
        
        Args:
            config: 新的配置字典
        """
        super().update_config(config)
        
        # 更新base_url
        if not self.base_url:
            self.base_url = os.getenv("TONGYI_API_BASE_URL", self.DEFAULT_BASE_URL)
        
        # 重新创建OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
