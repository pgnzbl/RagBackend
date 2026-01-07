"""
工具函数
"""
import re
import hashlib
import unicodedata
from typing import Tuple, Optional


def sanitize_collection_name(name: str) -> Tuple[str, bool]:
    """
    规范化collection名称，使其符合Chroma DB的要求
    
    Chroma DB要求：
    1. 3-63个字符
    2. 必须以字母数字开头和结尾
    3. 只能包含字母数字、下划线或连字符(-)
    4. 不能有两个连续的句点(..)
    5. 不能是有效的IPv4地址
    
    Args:
        name: 原始名称
        
    Returns:
        (规范化后的名称, 是否进行了转换)
    """
    if not name:
        raise ValueError("名称不能为空")
    
    original_name = name.strip()
    
    # 检查是否是IPv4地址
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, original_name):
        # 如果是IP地址，添加前缀
        original_name = f"kb_{original_name}"
    
    # 先尝试保留原始字符（如果都是ASCII）
    # 检查是否包含非ASCII字符
    has_non_ascii = any(ord(c) > 127 for c in original_name)
    
    if has_non_ascii:
        # 转换为ASCII字符（将中文等转换为ASCII）
        # 使用NFKD规范化，然后移除非ASCII字符
        normalized = unicodedata.normalize('NFKD', original_name)
        ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # 如果转换后为空或几乎为空，使用hash
        if not ascii_name or len(ascii_name.strip()) < 3:
            # 使用原始名称的hash作为基础
            name_hash = hashlib.md5(original_name.encode('utf-8')).hexdigest()[:12]
            ascii_name = f"kb_{name_hash}"
        else:
            # 保留转换后的ASCII字符，并添加hash后缀以保持唯一性
            name_hash = hashlib.md5(original_name.encode('utf-8')).hexdigest()[:8]
            ascii_name = f"{ascii_name}_{name_hash}"
    else:
        # 全部是ASCII字符，直接使用
        ascii_name = original_name
    
    # 替换不合法字符为下划线
    # 只保留字母数字、下划线和连字符
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', ascii_name)
    
    # 移除连续的句点
    sanitized = re.sub(r'\.{2,}', '_', sanitized)
    
    # 移除开头和结尾的非字母数字字符
    sanitized = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', sanitized)
    
    # 确保以字母或数字开头
    if not sanitized or not sanitized[0].isalnum():
        sanitized = f"kb_{sanitized}" if sanitized else "kb_default"
    
    # 确保以字母或数字结尾
    if not sanitized or not sanitized[-1].isalnum():
        sanitized = f"{sanitized}_kb" if sanitized else "kb_default"
    
    # 限制长度在3-63之间
    if len(sanitized) < 3:
        # 太短，使用hash补充
        name_hash = hashlib.md5(original_name.encode('utf-8')).hexdigest()[:8]
        sanitized = f"{sanitized}_{name_hash}"[:63]
    elif len(sanitized) > 63:
        # 太长，截断并使用hash后缀
        name_hash = hashlib.md5(original_name.encode('utf-8')).hexdigest()[:8]
        sanitized = f"{sanitized[:54]}_{name_hash}"
    
    # 检查是否需要转换
    needs_conversion = sanitized != original_name
    
    return sanitized, needs_conversion


def validate_collection_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    验证collection名称是否符合Chroma DB要求
    
    Args:
        name: 名称
        
    Returns:
        (是否合法, 错误信息)
    """
    if not name or not name.strip():
        return False, "名称不能为空"
    
    name = name.strip()
    
    # 检查长度
    if len(name) < 3:
        return False, "名称至少需要3个字符"
    if len(name) > 63:
        return False, "名称不能超过63个字符"
    
    # 检查是否以字母数字开头和结尾
    if not name[0].isalnum() or not name[-1].isalnum():
        return False, "名称必须以字母或数字开头和结尾"
    
    # 检查是否只包含合法字符（字母数字、下划线、连字符）
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "名称只能包含字母、数字、下划线和连字符(-)"
    
    # 检查是否有连续的句点
    if '..' in name:
        return False, "名称不能包含连续的句点(..)"
    
    # 检查是否是IPv4地址
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, name):
        return False, "名称不能是有效的IPv4地址"
    
    return True, None

