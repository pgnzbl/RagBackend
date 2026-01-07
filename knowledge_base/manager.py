"""
知识库管理模块
整合文档加载、切分、embedding和向量存储
"""
from typing import List, Dict, Optional, Any, Tuple
import os
import tempfile
from pathlib import Path
import logging

from .loader import DocumentLoader
from .splitter import TextSplitter
from .embedder import Embedder
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器，统一管理所有操作"""
    
    def __init__(self, persist_directory: str = "./data"):
        """
        初始化知识库管理器
        
        Args:
            persist_directory: 向量库持久化目录
        """
        self.vectorstore = VectorStore(persist_directory=persist_directory)
        
        # 从环境变量初始化embedder（固定使用通义千问）
        try:
            self.embedder = Embedder()
        except RuntimeError as e:
            # API key未配置
            self.embedder = None
            logger.error(f"Embedding模型初始化失败: {e}")
        
        self.splitter = TextSplitter(chunk_size=400, chunk_overlap=50)
        self.loader = DocumentLoader()
        logger.info("知识库管理器初始化完成")
    
    def create_knowledge_base(self, name: str) -> Tuple[bool, str, bool]:
        """
        创建知识库
        
        Args:
            name: 知识库名称
            
        Returns:
            (是否创建成功, 实际使用的名称, 是否进行了名称转换)
        """
        try:
            collection, actual_name, converted = self.vectorstore.create_collection(name, original_name=name)
            return True, actual_name, converted
        except Exception as e:
            logger.error(f"创建知识库失败 {name}: {e}")
            return False, name, False
    
    def list_knowledge_bases(self) -> List[Dict[str, any]]:
        """
        列出所有知识库（包含原始名称和实际名称）
        
        Returns:
            知识库信息列表，每个元素包含: name (显示名称), actual_name, original_name
        """
        collections_info = self.vectorstore.get_collection_display_info()
        result = []
        
        for info in collections_info:
            kb_info = {
                'name': info['display_name'],  # 显示名称（优先使用原始名称）
                'actual_name': info['actual_name'],  # 实际名称（用于API操作）
            }
            if info['original_name']:
                kb_info['original_name'] = info['original_name']
            
            # 获取文档数量
            try:
                count = self.vectorstore.get_document_count(info['actual_name'])
                kb_info['document_count'] = count
                
                # 获取维度
                dimension = self.vectorstore.get_collection_dimension(info['actual_name'])
                if dimension:
                    kb_info['embedding_dimension'] = dimension
            except Exception:
                kb_info['document_count'] = 0
            
            result.append(kb_info)
        
        return result
    
    def upload_file(
        self,
        kb_name: str,
        file_path: str,
        filename: str,
        split_strategy: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> Dict:
        """
        上传文件到知识库
        
        Args:
            kb_name: 知识库名称
            file_path: 文件路径（临时文件）
            filename: 原始文件名
            split_strategy: 切分策略（可选，如果提供则使用指定策略）
            chunk_size: chunk大小（可选，如果提供则使用指定大小）
            chunk_overlap: chunk重叠大小（可选，如果提供则使用指定重叠）
            
        Returns:
            包含文档信息的字典（chunks数量、文档ID等）
        """
        if self.embedder is None:
            raise RuntimeError("Embedding模型未配置，请先配置embedding模型")
        
        try:
            # 1. 加载文件
            text, file_metadata = self.loader.load_file(file_path, filename)
            
            if not text or not text.strip():
                raise ValueError("文件内容为空")
            
            # 2. 切分文本（如果提供了切分参数，创建临时切分器）
            if split_strategy is not None:
                # 使用传入的参数，如果没有传入则使用默认值
                splitter = TextSplitter(
                    strategy=split_strategy,
                    chunk_size=chunk_size if chunk_size is not None else self.splitter.chunk_size,
                    chunk_overlap=chunk_overlap if chunk_overlap is not None else self.splitter.chunk_overlap
                )
                chunks = splitter.split_text(text)
            else:
                # 使用默认切分器
                chunks = self.splitter.split_text(text)
            
            if not chunks:
                raise ValueError("文本切分后为空")
            
            # 3. 生成embeddings
            logger.info(f"正在为 {len(chunks)} 个chunks生成向量...")
            embeddings = self.embedder.embed(chunks)
            
            # 4. 准备元数据
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadata = file_metadata.copy()
                metadata['chunk_index'] = i
                metadata['total_chunks'] = len(chunks)
                # 记录切分策略，用于ID生成（确保不同策略产生不同的ID）
                if split_strategy:
                    metadata['split_strategy'] = split_strategy
                # 如果是PDF，可以添加页码信息（简化版本）
                metadatas.append(metadata)
            
            # 5. 添加到向量库
            doc_ids = self.vectorstore.add_documents(
                collection_name=kb_name,
                texts=chunks,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            logger.info(f"文件上传成功: {filename}, chunks: {len(chunks)}, IDs: {len(doc_ids)}")
            
            return {
                'filename': filename,
                'chunks_count': len(chunks),
                'doc_ids': doc_ids,
                'file_metadata': file_metadata
            }
            
        except Exception as e:
            logger.error(f"上传文件失败 {filename}: {e}")
            raise
    
    def query(
        self,
        kb_name: str,
        query_text: str,
        top_k: int = 5
    ) -> Dict:
        """
        查询知识库
        
        Args:
            kb_name: 知识库名称
            query_text: 查询文本
            top_k: 返回top-k结果
            
        Returns:
            查询结果字典
        """
        if self.embedder is None:
            raise RuntimeError("Embedding模型未配置，请先配置embedding模型")
        
        try:
            # 1. 生成查询向量
            query_embedding = self.embedder.embed_query(query_text)
            
            # 2. 向量检索
            results = self.vectorstore.query(
                collection_name=kb_name,
                query_embeddings=query_embedding,
                top_k=top_k
            )
            
            # 3. 格式化结果
            formatted_results = []
            for i in range(len(results['documents'])):
                formatted_results.append({
                    'text': results['documents'][i],
                    'score': 1.0 - results['distances'][i] if results['distances'] else 0.0,  # 距离转相似度
                    'distance': results['distances'][i] if results['distances'] else 0.0,
                    'metadata': results['metadatas'][i] if results['metadatas'] else {},
                    'id': results['ids'][i] if results['ids'] else None
                })
            
            return {
                'query': query_text,
                'results': formatted_results,
                'count': len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"查询失败 {kb_name}: {e}")
            raise
    
    def get_knowledge_base_docs(self, kb_name: str, limit: Optional[int] = None, include_preview: bool = True, max_preview_chunks: int = 5) -> Dict:
        """
        获取知识库中的文档列表
        
        Args:
            kb_name: 知识库名称（可以是原始名称或实际名称）
            limit: 返回数量限制，None表示不限制（获取全部）
            include_preview: 是否包含chunks预览，False时只返回文件列表和统计信息
            max_preview_chunks: 每个文件最多返回的chunk预览数量（仅在include_preview=True时生效）
            
        Returns:
            包含文档信息的字典
        """
        try:
            # 支持通过原始名称查找
            results = self.vectorstore.get_collection_documents(kb_name, limit=limit)
            logger.debug(f"获取知识库文档: kb_name={kb_name}, 返回文档数量={len(results.get('documents', []))}")
            
            # 按文件名分组
            files = {}
            total_chunks = len(results['documents'])
            logger.info(f"获取到 {total_chunks} 个文档chunks，开始按文件名分组...")
            
            # 第一遍遍历：统计每个文件的信息
            for doc, metadata, doc_id in zip(
                results['documents'],
                results['metadatas'],
                results['ids']
            ):
                filename = metadata.get('filename', 'unknown')
                if filename not in files:
                    files[filename] = {
                        'filename': filename,
                        'chunks': [],
                        'chunks_count': 0,  # 总chunks数量
                        'file_metadata': {k: v for k, v in metadata.items() 
                                        if k not in ['chunk_index', 'total_chunks']}
                    }
                files[filename]['chunks_count'] += 1
                
                # 如果包含预览，添加chunk信息（但限制每个文件的预览数量）
                if include_preview:
                    current_preview_count = len([c for c in files[filename]['chunks'] if 'id' in c])
                    if current_preview_count < max_preview_chunks:
                        files[filename]['chunks'].append({
                            'id': doc_id,
                            'chunk_index': metadata.get('chunk_index', 0),
                            'text_preview': doc[:100] + '...' if len(doc) > 100 else doc
                        })
            
            logger.info(f"文件分组完成，共 {len(files)} 个文件: {list(files.keys())}")
            for filename, file_info in files.items():
                preview_count = len(file_info['chunks']) if include_preview else 0
                logger.debug(f"  - {filename}: {file_info['chunks_count']} chunks (预览: {preview_count})")
            
            # 返回原始名称（如果存在映射），以便前端显示
            display_name = kb_name
            actual_name = self.vectorstore.name_mapping.get_actual_name(kb_name)
            original_name = self.vectorstore.name_mapping.get_original_name(actual_name)
            if original_name:
                display_name = original_name
            
            return {
                'kb_name': display_name,  # 返回显示名称（原始名称）
                'total_documents': len(results['documents']),
                'files': list(files.values())
            }
            
        except Exception as e:
            logger.error(f"获取文档列表失败 {kb_name}: {e}")
            raise
    
    def delete_knowledge_base(self, kb_name: str) -> bool:
        """
        删除知识库
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            是否删除成功
        """
        return self.vectorstore.delete_collection(kb_name)
    
    def delete_documents(self, kb_name: str, doc_ids: List[str]) -> bool:
        """
        删除知识库中的指定文档
        
        Args:
            kb_name: 知识库名称
            doc_ids: 文档ID列表
            
        Returns:
            是否删除成功
        """
        return self.vectorstore.delete_documents(kb_name, doc_ids)
    
    def get_kb_info(self, kb_name: str) -> Dict:
        """
        获取知识库信息
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            知识库信息字典
        """
        try:
            count = self.vectorstore.get_document_count(kb_name)
            dimension = self.vectorstore.get_collection_dimension(kb_name)
            
            info = {
                'name': kb_name,
                'document_count': count
            }
            
            if dimension:
                info['embedding_dimension'] = dimension
            
            return info
        except Exception:
            raise ValueError(f"知识库不存在: {kb_name}")
    

