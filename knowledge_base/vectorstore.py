"""
向量存储模块
封装Chroma DB操作
"""
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings
import os
import hashlib
import logging

from .utils import sanitize_collection_name, validate_collection_name
from .name_mapping import NameMapping

logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma向量存储管理器"""
    
    def __init__(self, persist_directory: str = "./data"):
        """
        初始化向量存储
        
        Args:
            persist_directory: 持久化目录路径
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # 创建PersistentClient
        # 禁用遥测以避免错误日志
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 禁用Chroma DB的遥测日志输出
        telemetry_logger = logging.getLogger("chromadb.telemetry")
        telemetry_logger.setLevel(logging.CRITICAL)
        
        # 初始化名称映射
        self.name_mapping = NameMapping(mapping_file=os.path.join(persist_directory, "name_mapping.json"))
        
        logger.info(f"Chroma向量存储初始化完成，目录: {persist_directory}")
    
    def create_collection(self, collection_name: str, original_name: Optional[str] = None) -> Tuple[chromadb.Collection, str, bool]:
        """
        创建或获取collection
        
        Args:
            collection_name: 知识库名称（可能是规范化后的）
            original_name: 原始名称（用于验证是否需要转换）
            
        Returns:
            (Collection对象, 实际使用的名称, 是否进行了转换)
        """
        # 验证原始名称
        if original_name:
            is_valid, error_msg = validate_collection_name(original_name)
            if not is_valid:
                # 名称不合法，进行规范化
                sanitized_name, converted = sanitize_collection_name(original_name)
                logger.info(f"名称不规范，已转换: '{original_name}' -> '{sanitized_name}'")
                actual_name = sanitized_name
            else:
                actual_name = original_name
                converted = False
        else:
            # 如果没有提供原始名称，使用传入的名称
            is_valid, error_msg = validate_collection_name(collection_name)
            if not is_valid:
                sanitized_name, converted = sanitize_collection_name(collection_name)
                actual_name = sanitized_name
            else:
                actual_name = collection_name
                converted = False
        
        try:
            # 尝试获取已存在的collection
            collection = self.client.get_collection(name=actual_name)
            logger.info(f"获取已存在的collection: {actual_name}")
            
            # 如果collection已存在，检查是否需要添加映射关系
            # 场景：collection已存在但没有映射（可能是之前创建的），现在通过原始名称创建
            if original_name and actual_name != original_name:
                # 检查是否已有映射
                existing_original = self.name_mapping.get_original_name(actual_name)
                if not existing_original:
                    # 没有映射，添加映射关系
                    self.name_mapping.add_mapping(actual_name, original_name)
                    logger.debug(f"为已存在的collection添加映射: {actual_name} -> {original_name}")
            
            return collection, actual_name, converted
        except Exception:
            # 不存在则创建
            collection = self.client.create_collection(name=actual_name)
            logger.info(f"创建新collection: {actual_name}")
            
            # 如果名称被转换了，保存映射关系
            # 或者如果提供了original_name且与实际名称不同，也保存映射
            if original_name and actual_name != original_name:
                self.name_mapping.add_mapping(actual_name, original_name)
                logger.debug(f"创建collection并添加映射: {actual_name} -> {original_name}")
            
            return collection, actual_name, converted
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        删除collection
        
        Args:
            collection_name: 知识库名称（可以是原始名称或实际名称）
            
        Returns:
            是否删除成功
        """
        try:
            # 尝试通过原始名称查找实际名称
            actual_name = self.name_mapping.get_actual_name(collection_name)
            
            self.client.delete_collection(name=actual_name)
            logger.info(f"删除collection: {actual_name}")
            
            # 删除映射
            self.name_mapping.remove_mapping(actual_name)
            
            return True
        except Exception as e:
            logger.error(f"删除collection失败 {collection_name}: {e}")
            return False
    
    def list_collections(self, return_original_names: bool = False) -> List[str]:
        """
        列出所有collection名称
        
        Args:
            return_original_names: 是否返回原始名称（如果有映射）
        
        Returns:
            collection名称列表（根据return_original_names返回实际名称或原始名称）
        """
        collections = self.client.list_collections()
        actual_names = [col.name for col in collections]
        
        if return_original_names:
            # 返回原始名称（如果存在映射）或实际名称
            result = []
            for actual_name in actual_names:
                original_name = self.name_mapping.get_original_name(actual_name)
                result.append(original_name if original_name else actual_name)
            return result
        else:
            return actual_names
    
    def get_collection_display_info(self) -> List[Dict[str, str]]:
        """
        获取所有collection的显示信息（包含原始名称和实际名称）
        
        Returns:
            collection信息列表，每个元素包含: actual_name, original_name, display_name
        """
        collections = self.client.list_collections()
        result = []
        
        for col in collections:
            actual_name = col.name
            original_name = self.name_mapping.get_original_name(actual_name)
            result.append({
                'actual_name': actual_name,
                'original_name': original_name,
                'display_name': original_name if original_name else actual_name
            })
        
        return result
    
    def add_documents(
        self,
        collection_name: str,
        texts: List[str],
        metadatas: List[Dict],
        embeddings: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档到collection
        
        Args:
            collection_name: 知识库名称（可以是原始名称或实际名称）
            texts: 文本列表
            metadatas: 元数据列表
            embeddings: 向量列表（可选，如果不提供则需外部调用embed）
            ids: 文档ID列表（可选，自动生成）
            
        Returns:
            插入的文档ID列表
        """
        # 先尝试通过名称映射查找实际名称
        actual_name_from_mapping = self.name_mapping.get_actual_name(collection_name)
        
        # 如果找到了映射（传入的是原始名称），直接使用实际名称获取collection
        if actual_name_from_mapping != collection_name:
            # 找到了映射，说明传入的是原始名称，使用实际名称
            actual_name = actual_name_from_mapping
            try:
                collection = self.client.get_collection(name=actual_name)
                logger.debug(f"使用映射的实际名称获取collection: {actual_name} (原始名称: {collection_name})")
            except Exception as e:
                # 如果获取失败，记录错误并重新创建（使用原始名称以便创建映射）
                logger.warning(f"使用映射名称获取collection失败: {e}，尝试重新创建")
                collection, actual_name, _ = self.create_collection(collection_name, original_name=collection_name)
        else:
            # 没有映射，传入的可能是实际名称，或者是需要创建的新知识库
            # 先尝试直接获取，如果失败再创建
            try:
                collection = self.client.get_collection(name=collection_name)
                actual_name = collection_name
                logger.debug(f"直接使用传入名称获取collection: {actual_name}")
            except Exception:
                # 获取失败，可能是新知识库，需要验证和创建
                # 传入original_name=collection_name，以便在名称转换时创建映射
                collection, actual_name, _ = self.create_collection(collection_name, original_name=collection_name)
        
        # 使用实际名称
        collection_name = actual_name
        
        # 如果没有提供ids，则自动生成（使用文本hash避免重复）
        # 同步过滤掉重复的文档，确保所有列表长度一致
        if ids is None:
            ids = []
            existing_ids = set()
            
            # 获取已有的所有ids（用于去重）
            try:
                existing_data = collection.get()
                if existing_data['ids']:
                    existing_ids = set(existing_data['ids'])
                    logger.debug(f"已有文档数量: {len(existing_ids)}")
            except Exception:
                pass
            
            # 同步过滤：同时过滤 texts, metadatas, embeddings 和生成的 ids
            valid_texts = []
            valid_metadatas = []
            valid_embeddings = []
            valid_ids = []
            
            # 为每个文本生成唯一ID（基于内容和元数据），同时过滤重复项
            embeddings_list = embeddings if embeddings else [None] * len(texts)
            for text, metadata, emb in zip(texts, metadatas, embeddings_list):
                # 使用文本、文件名、chunk_index、total_chunks和切分策略生成hash作为ID
                # 包含切分策略确保不同切分策略产生的chunk有不同的ID
                split_strategy = metadata.get('split_strategy', '')
                content = f"{text}{metadata.get('filename', '')}{metadata.get('chunk_index', '')}{metadata.get('total_chunks', '')}{split_strategy}"
                doc_id = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                # 如果已存在，跳过（去重）
                if doc_id in existing_ids:
                    logger.debug(f"文档已存在，跳过: {doc_id[:8]}... (文件: {metadata.get('filename', 'unknown')})")
                    continue
                
                # 添加到有效列表
                valid_texts.append(text)
                valid_metadatas.append(metadata)
                if embeddings:
                    valid_embeddings.append(emb)
                valid_ids.append(doc_id)
                existing_ids.add(doc_id)  # 添加到已存在集合，避免本次批量中的重复
            
            # 使用过滤后的列表
            texts = valid_texts
            metadatas = valid_metadatas
            ids = valid_ids
            if embeddings:
                embeddings = valid_embeddings
        
        # 存储向量维度到metadata（如果提供了embeddings）
        if embeddings and len(embeddings) > 0:
            dimension = len(embeddings[0])
            # 在metadata中记录维度信息（用于后续检查）
            if metadatas:
                for metadata in metadatas:
                    metadata['embedding_dimension'] = dimension
        
        # 如果没有提供ids，现在已经同步过滤过了
        # 如果提供了ids，需要再次检查去重
        if ids and len(ids) != len(texts):
            # 如果外部提供了ids但长度不匹配，需要同步过滤
            logger.warning(f"提供的ids长度({len(ids)})与texts长度({len(texts)})不匹配，将同步过滤")
            min_len = min(len(ids), len(texts), len(metadatas))
            texts = texts[:min_len]
            metadatas = metadatas[:min_len]
            ids = ids[:min_len]
            if embeddings:
                embeddings = embeddings[:min_len]
        
        # 最终验证：确保所有列表长度一致
        if not (len(texts) == len(metadatas) == len(ids)):
            raise ValueError(f"数据不一致: texts={len(texts)}, metadatas={len(metadatas)}, ids={len(ids)}")
        if embeddings and len(embeddings) != len(texts):
            raise ValueError(f"embeddings长度({len(embeddings)})与texts长度({len(texts)})不匹配")
        
        if not texts:
            logger.warning("没有新文档需要添加（可能全部重复）")
            return []
        
        # 添加文档
        try:
            if embeddings:
                collection.add(
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings,
                    ids=ids
                )
            else:
                collection.add(
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
            
            logger.info(f"成功添加 {len(ids)} 个文档到 collection: {collection_name}")
            
            # 验证文档是否真的添加成功
            try:
                verify_result = collection.get(ids=ids[:min(3, len(ids))])
                verify_count = len(verify_result.get('ids', []))
                logger.debug(f"验证: collection {collection_name} 中成功添加了 {verify_count} 个文档（验证前3个）")
            except Exception as e:
                logger.warning(f"验证添加的文档时出错: {e}")
            
            return ids
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise
    
    def query(
        self,
        collection_name: str,
        query_embeddings: List[float],
        top_k: int = 5,
        n_results: Optional[int] = None
    ) -> Dict:
        """
        查询向量
        
        Args:
            collection_name: 知识库名称（可以是原始名称或实际名称）
            query_embeddings: 查询向量
            top_k: 返回top-k结果（与n_results相同，提供兼容性）
            n_results: 返回结果数量
            
        Returns:
            查询结果字典，包含documents, metadatas, distances, ids
        """
        if n_results is None:
            n_results = top_k
        
        # 尝试通过原始名称查找实际名称
        actual_name = self.name_mapping.get_actual_name(collection_name)
        
        try:
            collection = self.client.get_collection(name=actual_name)
        except Exception:
            raise ValueError(f"知识库不存在: {collection_name}")
        
        try:
            results = collection.query(
                query_embeddings=[query_embeddings],
                n_results=n_results
            )
            
            # 转换格式，确保返回统一格式
            return {
                'documents': results['documents'][0] if results['documents'] else [],
                'metadatas': results['metadatas'][0] if results['metadatas'] else [],
                'distances': results['distances'][0] if results['distances'] else [],
                'ids': results['ids'][0] if results['ids'] else []
            }
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            raise
    
    def get_collection_documents(self, collection_name: str, limit: Optional[int] = None) -> Dict:
        """
        获取collection中的所有文档
        
        Args:
            collection_name: 知识库名称（可以是原始名称或实际名称）
            limit: 返回数量限制，None表示不限制（获取全部）
            
        Returns:
            包含documents, metadatas, ids的字典
        """
        # 尝试通过原始名称查找实际名称
        actual_name = self.name_mapping.get_actual_name(collection_name)
        logger.debug(f"获取文档: 传入名称={collection_name}, 实际名称={actual_name}")
        
        try:
            collection = self.client.get_collection(name=actual_name)
            
            # 获取总文档数量，用于日志
            total_count = collection.count()
            
            # 如果limit为None，使用总数量（获取全部）
            if limit is None:
                limit = total_count
                logger.info(f"Collection {actual_name} 总文档数: {total_count}, limit=None（获取全部）")
            else:
                logger.info(f"Collection {actual_name} 总文档数: {total_count}, limit: {limit}")
                # 如果limit小于总数量，记录警告
                if limit < total_count:
                    logger.warning(f"limit ({limit}) 小于总文档数 ({total_count})，可能会截断结果。建议使用 limit=None 或 limit={total_count}")
            
            results = collection.get(limit=limit)
            retrieved_count = len(results.get('ids', []))
            logger.info(f"成功获取文档: collection={actual_name}, 返回文档数量={retrieved_count}/{total_count}")
            
            return {
                'documents': results['documents'],
                'metadatas': results['metadatas'],
                'ids': results['ids']
            }
        except Exception as e:
            logger.error(f"获取文档失败: collection_name={collection_name}, actual_name={actual_name}, error={e}")
            raise ValueError(f"知识库不存在: {collection_name}")
    
    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        """
        删除指定ID的文档
        
        Args:
            collection_name: 知识库名称（可以是原始名称或实际名称）
            ids: 要删除的文档ID列表
            
        Returns:
            是否删除成功
        """
        # 尝试通过原始名称查找实际名称
        actual_name = self.name_mapping.get_actual_name(collection_name)
        
        try:
            collection = self.client.get_collection(name=actual_name)
            collection.delete(ids=ids)
            logger.info(f"从 {actual_name} 删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def get_document_count(self, collection_name: str) -> int:
        """
        获取知识库中的文档数量
        
        Args:
            collection_name: 知识库名称
            
        Returns:
            文档数量
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0
    
    def get_collection_dimension(self, collection_name: str) -> Optional[int]:
        """
        获取collection的向量维度
        
        Args:
            collection_name: 知识库名称（可以是原始名称或实际名称）
            
        Returns:
            向量维度，如果collection不存在或为空返回None
        """
        # 尝试通过原始名称查找实际名称
        actual_name = self.name_mapping.get_actual_name(collection_name)
        
        try:
            collection = self.client.get_collection(name=actual_name)
            
            # 尝试从collection中获取一个向量来推断维度
            results = collection.get(limit=1)
            
            if results.get('embeddings') and len(results['embeddings']) > 0:
                # 如果有embeddings，直接获取维度
                first_embedding = results['embeddings'][0]
                if first_embedding:
                    return len(first_embedding)
            
            # 如果没有embeddings，尝试从metadata中获取
            if results.get('metadatas') and len(results['metadatas']) > 0:
                metadata = results['metadatas'][0]
                if metadata and 'embedding_dimension' in metadata:
                    return metadata['embedding_dimension']
            
            return None
            
        except Exception as e:
            logger.warning(f"获取collection维度失败 {collection_name}: {e}")
            return None
    
    def set_collection_dimension(self, collection_name: str, dimension: int) -> bool:
        """
        在collection的metadata中存储维度信息
        注意：Chroma可能不支持直接设置collection级别的metadata
        这个方法主要用于在文档metadata中存储维度信息
        
        Args:
            collection_name: 知识库名称
            dimension: 向量维度
            
        Returns:
            是否设置成功
        """
        # 由于Chroma的限制，维度信息主要存储在文档的metadata中
        # 这里可以添加一些辅助逻辑，比如创建一个特殊的metadata文档
        # 或者仅用于验证目的
        logger.info(f"记录collection {collection_name} 的维度: {dimension}")
        return True

