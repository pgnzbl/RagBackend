"""
文本切分模块
支持多种切分策略：固定长度、按换行、按段落、按句子等
"""
from typing import List, Optional
import re
import logging

logger = logging.getLogger(__name__)


class TextSplitter:
    """文本切分器，支持多种切分策略"""
    
    # 支持的切分策略
    STRATEGIES = {
        'fixed': '固定长度切分',
        'newline': '按换行符切分',
        'paragraph': '按段落切分（双换行）',
        'sentence': '按句子切分',
        'smart': '智能切分（优先段落，然后句子，最后固定长度）'
    }
    
    def __init__(
        self,
        strategy: str = 'fixed',
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
        max_chunk_size: Optional[int] = None
    ):
        """
        初始化文本切分器
        
        Args:
            strategy: 切分策略 ('fixed', 'newline', 'paragraph', 'sentence', 'smart')
            chunk_size: 每个chunk的目标大小（字符数，用于fixed和smart策略）
            chunk_overlap: chunk之间的重叠字符数
            min_chunk_size: 最小chunk大小（避免过小的chunk）
            max_chunk_size: 最大chunk大小（超过会强制切分）
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(f"不支持的切分策略: {strategy}。支持: {', '.join(self.STRATEGIES.keys())}")
        
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size or chunk_size * 2
    
    def split_text(self, text: str) -> List[str]:
        """
        根据策略切分文本
        
        Args:
            text: 要切分的文本
            
        Returns:
            chunk列表
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        # 根据策略选择切分方法
        if self.strategy == 'fixed':
            chunks = self._split_fixed(text)
        elif self.strategy == 'newline':
            chunks = self._split_by_newline(text)
        elif self.strategy == 'paragraph':
            chunks = self._split_by_paragraph(text)
        elif self.strategy == 'sentence':
            chunks = self._split_by_sentence(text)
        elif self.strategy == 'smart':
            chunks = self._split_smart(text)
        else:
            raise ValueError(f"未知的切分策略: {self.strategy}")
        
        # 过滤空chunk，根据策略决定是否合并过小的chunk
        chunks = self._filter_and_merge_chunks(chunks)
        
        logger.info(f"文本切分完成: 策略={self.strategy}, 总长度={len(text)}, chunks数量={len(chunks)}")
        return chunks
    
    def _split_fixed(self, text: str) -> List[str]:
        """固定长度切分（原有逻辑）"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
            
            # 尝试在句号、换行符等位置切分
            split_pos = end
            for delimiter in ['\n\n', '。\n', '。', '\n', '！', '？', '. ', '! ', '? ']:
                last_pos = text.rfind(delimiter, start, end)
                if last_pos != -1:
                    split_pos = last_pos + len(delimiter)
                    break
            
            chunk = text[start:split_pos].strip()
            if chunk:
                chunks.append(chunk)
            
            start = max(start + 1, split_pos - self.chunk_overlap)
        
        return chunks
    
    def _split_by_newline(self, text: str) -> List[str]:
        """按换行符切分（每行作为一个chunk，除非单行超过max_chunk_size）"""
        lines = text.split('\n')
        chunks = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # 跳过空行
                continue
            
            # 如果单行超过最大长度，使用固定长度切分
            if len(line) > self.max_chunk_size:
                # 对超长行使用固定长度切分
                fixed_chunks = self._split_fixed(line)
                chunks.extend(fixed_chunks)
            else:
                # 每行作为一个独立的chunk
                chunks.append(line)
        
        return chunks
    
    def _split_by_paragraph(self, text: str) -> List[str]:
        """按段落切分（双换行符）- 每个段落作为一个独立的chunk"""
        # 按双换行符或更多换行符分割段落
        paragraphs = re.split(r'\n{2,}', text)
        
        chunks = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果段落超过最大长度，使用固定长度切分（作为后备）
            if len(para) > self.max_chunk_size:
                # 对于超长段落，使用固定长度切分
                fixed_chunks = self._split_fixed(para)
                chunks.extend(fixed_chunks)
            else:
                # 每个段落作为一个独立的chunk
                chunks.append(para)
        
        return chunks
    
    def _split_by_sentence(self, text: str) -> List[str]:
        """按句子切分 - 每个句子作为一个独立的chunk"""
        # 中英文句子分隔符
        sentence_endings = r'[。！？.!?]+\s*'
        sentences = re.split(sentence_endings, text)
        
        chunks = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 如果句子超过最大长度，使用固定长度切分（作为后备）
            if len(sentence) > self.max_chunk_size:
                # 对于超长句子，使用固定长度切分
                fixed_chunks = self._split_fixed(sentence)
                chunks.extend(fixed_chunks)
            else:
                # 每个句子作为一个独立的chunk
                chunks.append(sentence)
        
        return chunks
    
    def _split_smart(self, text: str) -> List[str]:
        """智能切分：优先按段落，然后按句子，最后按固定长度"""
        # 先尝试按段落切分
        paragraphs = re.split(r'\n{2,}', text)
        
        chunks = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果段落小于chunk_size，直接作为chunk
            if len(para) <= self.chunk_size:
                chunks.append(para)
            # 如果段落大于chunk_size但小于max_chunk_size，尝试按句子切分
            elif len(para) <= self.max_chunk_size:
                sentence_chunks = self._split_by_sentence(para)
                chunks.extend(sentence_chunks)
            # 如果段落太大，使用固定长度切分
            else:
                fixed_chunks = self._split_fixed(para)
                chunks.extend(fixed_chunks)
        
        return chunks
    
    def _filter_and_merge_chunks(self, chunks: List[str]) -> List[str]:
        """
        过滤空chunk，根据策略决定是否合并过小的chunk
        
        注意：
        - 对于 newline, sentence, paragraph 策略：严格按策略切分，不合并，只过滤空chunk
        - 对于 fixed, smart 策略：可以合并过小的chunk
        """
        if not chunks:
            return []
        
        # 严格按策略切分的模式：只过滤空chunk，不合并
        strict_strategies = ['newline', 'sentence', 'paragraph']
        if self.strategy in strict_strategies:
            # 只过滤空chunk，保持原始切分结果
            filtered = [chunk.strip() for chunk in chunks if chunk.strip()]
            return filtered
        
        # fixed 和 smart 策略：可以合并过小的chunk
        result = []
        current_chunk = ""
        
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # 如果chunk太大，需要切分（这种情况不应该发生，但作为保险）
            if len(chunk) > self.max_chunk_size:
                # 使用固定长度切分
                fixed_chunks = self._split_fixed(chunk)
                result.extend(fixed_chunks)
                continue
            
            # 如果chunk太小，尝试与下一个合并
            if len(chunk) < self.min_chunk_size:
                if current_chunk:
                    merged = current_chunk + '\n' + chunk
                    # 如果合并后不超过最大长度，合并
                    if len(merged) <= self.max_chunk_size:
                        current_chunk = merged
                    else:
                        # 否则保存当前chunk，开始新的chunk
                        result.append(current_chunk)
                        current_chunk = chunk
                else:
                    current_chunk = chunk
            else:
                # chunk大小合适，如果当前有积累的小chunk，先保存
                if current_chunk:
                    result.append(current_chunk)
                    current_chunk = ""
                
                result.append(chunk)
        
        # 保存最后一个chunk
        if current_chunk:
            result.append(current_chunk)
        
        return result
    
    def split_documents(self, documents: List[str]) -> List[str]:
        """
        批量切分文档
        
        Args:
            documents: 文档列表
            
        Returns:
            所有文档的chunk列表
        """
        all_chunks = []
        for doc in documents:
            chunks = self.split_text(doc)
            all_chunks.extend(chunks)
        return all_chunks
