"""
配置数据模型和验证
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmbeddingConfig(BaseModel):
    """Embedding配置模型"""
    provider: str = Field(..., description="提供商名称: tongyi, openai, custom")
    api_key: str = Field(..., description="API密钥")
    model: str = Field(..., description="模型名称")
    base_url: Optional[str] = Field(None, description="自定义API地址（可选）")
    dimension: Optional[int] = Field(None, description="向量维度（自动获取或手动配置）")
    updated_at: Optional[str] = Field(None, description="更新时间")
    
    @validator('provider')
    def validate_provider(cls, v):
        """验证提供商"""
        valid_providers = ['tongyi', 'openai', 'custom']
        if v not in valid_providers:
            raise ValueError(f"不支持的提供商: {v}。支持: {', '.join(valid_providers)}")
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """验证API密钥不为空"""
        if not v or not v.strip():
            raise ValueError("API密钥不能为空")
        return v.strip()
    
    @validator('model')
    def validate_model(cls, v):
        """验证模型名称不为空"""
        if not v or not v.strip():
            raise ValueError("模型名称不能为空")
        return v.strip()
    
    def to_dict(self, mask_api_key: bool = True) -> Dict[str, Any]:
        """
        转换为字典
        
        Args:
            mask_api_key: 是否掩码API密钥
        """
        data = self.dict()
        if mask_api_key and self.api_key:
            # 只显示前4位和后4位
            masked = self.api_key[:4] + '*' * (len(self.api_key) - 8) + self.api_key[-4:] if len(self.api_key) > 8 else '****'
            data['api_key'] = masked
        return data


class Config(BaseModel):
    """完整配置模型"""
    embedding: Optional[EmbeddingConfig] = Field(None, description="Embedding配置")
    
    def to_dict(self, mask_api_key: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'embedding': self.embedding.to_dict(mask_api_key=mask_api_key) if self.embedding else None
        }

