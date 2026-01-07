"""
文档加载模块
支持PDF、TXT、DOCX文件解析
"""
import os
from typing import List, Tuple, Optional
import pdfplumber
from docx import Document
import logging

logger = logging.getLogger(__name__)


class DocumentLoader:
    """文档加载器，支持多种格式"""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.md'}
    
    @staticmethod
    def load_file(file_path: str, filename: str) -> Tuple[str, dict]:
        """
        加载文件并提取文本
        
        Args:
            file_path: 文件路径
            filename: 文件名（用于判断类型）
            
        Returns:
            (文本内容, 元数据字典)
        
        Raises:
            ValueError: 文件类型不支持
            FileNotFoundError: 文件不存在
        """
        ext = os.path.splitext(filename.lower())[1]
        
        if ext not in DocumentLoader.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}。支持的格式: {', '.join(DocumentLoader.SUPPORTED_EXTENSIONS)}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        metadata = {
            'filename': filename,
            'file_type': ext[1:],  # 去掉点号
        }
        
        try:
            if ext == '.pdf':
                text, pdf_metadata = DocumentLoader._load_pdf(file_path)
                metadata.update(pdf_metadata)
            elif ext == '.txt':
                text = DocumentLoader._load_txt(file_path)
            elif ext == '.docx':
                text = DocumentLoader._load_docx(file_path)
            elif ext == '.md':
                text = DocumentLoader._load_txt(file_path)  # markdown按txt处理
                metadata['file_type'] = 'md'
            else:
                raise ValueError(f"未实现的文件类型: {ext}")
            
            logger.info(f"文件加载成功: {filename}, 文本长度: {len(text)}")
            return text, metadata
            
        except Exception as e:
            logger.error(f"加载文件失败 {filename}: {e}")
            raise
    
    @staticmethod
    def _load_pdf(file_path: str) -> Tuple[str, dict]:
        """
        加载PDF文件
        
        Returns:
            (文本内容, 包含页码等信息的元数据)
        """
        text_parts = []
        total_pages = 0
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        full_text = '\n\n'.join(text_parts)
        
        metadata = {
            'total_pages': total_pages,
        }
        
        return full_text, metadata
    
    @staticmethod
    def _load_txt(file_path: str) -> str:
        """加载TXT文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"无法解码文件: {file_path}")
    
    @staticmethod
    def _load_docx(file_path: str) -> str:
        """加载DOCX文件"""
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return '\n\n'.join(paragraphs)
    
    @staticmethod
    def is_supported(filename: str) -> bool:
        """检查文件类型是否支持"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in DocumentLoader.SUPPORTED_EXTENSIONS

