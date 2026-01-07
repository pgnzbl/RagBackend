"""
知识库名称映射管理
保存原始名称和实际名称的对应关系
"""
import json
import os
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NameMapping:
    """名称映射管理器"""
    
    def __init__(self, mapping_file: str = "./data/name_mapping.json"):
        """
        初始化名称映射
        
        Args:
            mapping_file: 映射文件路径
        """
        self.mapping_file = Path(mapping_file)
        self.mapping_dir = self.mapping_file.parent
        
        # 确保目录存在
        self.mapping_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载映射
        self.mapping: Dict[str, str] = self._load_mapping()
        logger.info(f"名称映射初始化完成，已加载 {len(self.mapping)} 个映射")
    
    def _load_mapping(self) -> Dict[str, str]:
        """加载映射文件"""
        if not self.mapping_file.exists():
            return {}
        
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 映射格式：actual_name -> original_name
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"加载名称映射失败: {e}")
            return {}
    
    def _save_mapping(self) -> bool:
        """保存映射文件"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存名称映射失败: {e}")
            return False
    
    def add_mapping(self, actual_name: str, original_name: str) -> None:
        """
        添加名称映射
        
        Args:
            actual_name: 实际使用的名称（转换后的）
            original_name: 原始名称
        """
        if actual_name != original_name:
            self.mapping[actual_name] = original_name
            self._save_mapping()
            logger.debug(f"添加名称映射: {actual_name} -> {original_name}")
    
    def get_original_name(self, actual_name: str) -> Optional[str]:
        """
        获取原始名称
        
        Args:
            actual_name: 实际使用的名称
            
        Returns:
            原始名称，如果不存在映射则返回None
        """
        return self.mapping.get(actual_name)
    
    def get_actual_name(self, name: str) -> str:
        """
        获取实际使用的名称（支持通过原始名称查找）
        
        Args:
            name: 名称（可能是原始名称或实际名称）
            
        Returns:
            实际使用的名称
        """
        # 如果name在映射的值中（即它是原始名称），找到对应的key
        for actual, original in self.mapping.items():
            if original == name:
                return actual
        # 否则，name就是实际名称
        return name
    
    def remove_mapping(self, actual_name: str) -> None:
        """
        移除名称映射
        
        Args:
            actual_name: 实际使用的名称
        """
        if actual_name in self.mapping:
            del self.mapping[actual_name]
            self._save_mapping()
    
    def get_all_mappings(self) -> Dict[str, str]:
        """
        获取所有映射
        
        Returns:
            映射字典（actual_name -> original_name）
        """
        return self.mapping.copy()
    
    def get_all_original_names(self) -> Dict[str, str]:
        """
        获取反向映射（原始名称 -> 实际名称）
        
        Returns:
            反向映射字典（original_name -> actual_name）
        """
        return {v: k for k, v in self.mapping.items()}

