"""
FastAPI主应用
提供知识库管理的REST API
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import tempfile
import logging
from pydantic import BaseModel

from knowledge_base import KnowledgeBaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 禁用Chroma DB的遥测日志（避免错误信息）
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

# 创建FastAPI应用
app = FastAPI(
    title="知识库管理后端",
    description="基于Chroma和FastAPI的轻量级知识库管理系统",
    version="1.0.0"
)

# 配置CORS（允许Chrome插件跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化知识库管理器
kb_manager = KnowledgeBaseManager(persist_directory="./data")

# ============= API密钥鉴权 =============

# API Key配置（从环境变量读取）
API_KEY = os.getenv("API_KEY", "").strip()

def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    验证API密钥
    
    Args:
        x_api_key: 请求头中的API密钥
        
    Raises:
        HTTPException: 如果API密钥无效
    """
    # 如果未配置API_KEY环境变量，跳过验证（开发模式）
    if not API_KEY:
        logger.debug("API_KEY未配置，跳过API密钥验证（仅用于开发环境）")
        return
    
    # 如果配置了API_KEY，必须验证
    if not x_api_key:
        logger.warning("请求缺少API密钥")
        raise HTTPException(
            status_code=401,
            detail="缺少API密钥。请在请求头中添加: X-API-Key"
        )
    
    if x_api_key != API_KEY:
        logger.warning(f"API密钥验证失败")
        raise HTTPException(
            status_code=403,
            detail="无效的API密钥"
        )
    
    logger.debug("API密钥验证成功")


# 鉴权依赖（用于需要保护的端点）
require_api_key = Depends(verify_api_key)


# ============= 请求模型 =============

class CreateKBRequest(BaseModel):
    """创建知识库请求"""
    name: str


class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    top_k: int = 5


class DeleteDocsRequest(BaseModel):
    """删除文档请求"""
    doc_ids: List[str]


# ============= API路由 =============

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "知识库管理后端API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.get("/kb/split-strategies")
async def get_split_strategies():
    """
    获取支持的切分策略列表
    
    GET /kb/split-strategies
    
    返回所有支持的切分策略及其描述
    """
    from knowledge_base.splitter import TextSplitter
    return {
        "success": True,
        "strategies": TextSplitter.STRATEGIES
    }


@app.post("/kb/create")
async def create_knowledge_base(request: CreateKBRequest, _: bool = require_api_key):
    """
    创建知识库
    
    POST /kb/create
    {
        "name": "my_kb"
    }
    
    注意：如果名称包含中文字符或特殊字符，系统会自动转换为符合规范的格式
    """
    try:
        if not request.name or not request.name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        
        kb_name = request.name.strip()
        original_name = kb_name
        
        # 创建知识库（内部会处理名称规范化）
        success, actual_name, converted = kb_manager.create_knowledge_base(kb_name)
        
        if success:
            response = {
                "success": True,
                "message": f"知识库创建成功: {actual_name}",
                "kb_name": actual_name,
                "original_name": original_name if converted else None,
                "name_converted": converted
            }
            if converted:
                response["message"] += f"（原名称：{original_name}）"
            return response
        else:
            raise HTTPException(status_code=500, detail="创建知识库失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建知识库异常: {e}")
        # 检查是否是名称验证错误
        error_str = str(e)
        if "Expected collection name" in error_str or "collection name" in error_str.lower():
            raise HTTPException(
                status_code=400,
                detail=f"知识库名称不符合规范: {error_str}。系统已自动转换，请重试。"
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/kb/{name}/upload")
async def upload_file(
    name: str, 
    file: UploadFile = File(...),
    split_strategy: str = 'fixed',
    chunk_size: int = 400,
    chunk_overlap: int = 50,
    _: bool = require_api_key
):
    """
    上传文件到知识库
    
    POST /kb/{name}/upload?split_strategy=newline&chunk_size=500&chunk_overlap=50
    Content-Type: multipart/form-data
    
    查询参数：
    - split_strategy: 切分策略 (fixed/newline/paragraph/sentence/smart)，默认 'fixed'
    - chunk_size: chunk大小（字符数），默认 400
    - chunk_overlap: chunk重叠大小，默认 50
    """
    try:
        # 验证切分策略
        from knowledge_base.splitter import TextSplitter
        if split_strategy not in TextSplitter.STRATEGIES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的切分策略: {split_strategy}。支持: {', '.join(TextSplitter.STRATEGIES.keys())}"
            )
        
        # 验证参数范围
        if chunk_size <= 0:
            raise HTTPException(status_code=400, detail="chunk_size 必须大于0")
        if chunk_overlap < 0:
            raise HTTPException(status_code=400, detail="chunk_overlap 不能为负数")
        if chunk_overlap >= chunk_size:
            raise HTTPException(status_code=400, detail="chunk_overlap 必须小于 chunk_size")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=f"参数验证失败: {str(e)}")
    
    try:
        # 检查知识库是否存在（支持通过原始名称查找）
        existing_kbs_info = kb_manager.list_knowledge_bases()
        existing_actual_names = [kb['actual_name'] for kb in existing_kbs_info]
        existing_display_names = [kb['name'] for kb in existing_kbs_info]
        
        actual_name = kb_manager.vectorstore.name_mapping.get_actual_name(name)
        if actual_name not in existing_actual_names and name not in existing_display_names:
            # 自动创建知识库
            kb_manager.create_knowledge_base(name)
            logger.info(f"自动创建知识库: {name}")
        
        # 检查文件类型
        if not kb_manager.loader.is_supported(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持格式: PDF, TXT, DOCX, MD"
            )
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # 上传文件（传递切分策略参数）
            result = kb_manager.upload_file(
                kb_name=name,
                file_path=tmp_path,
                filename=file.filename,
                split_strategy=split_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            return {
                "success": True,
                "message": "文件上传成功",
                "kb_name": name,
                "filename": result['filename'],
                "chunks_count": result['chunks_count'],
                "file_metadata": result['file_metadata']
            }
        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/kb/{name}/query")
async def query_knowledge_base(name: str, request: QueryRequest, _: bool = require_api_key):
    """
    查询知识库
    
    POST /kb/{name}/query
    {
        "query": "你的问题",
        "top_k": 5
    }
    """
    try:
        # 检查知识库是否存在（支持通过原始名称查找）
        existing_kbs_info = kb_manager.list_knowledge_bases()
        existing_actual_names = [kb['actual_name'] for kb in existing_kbs_info]
        existing_display_names = [kb['name'] for kb in existing_kbs_info]
        
        actual_name = kb_manager.vectorstore.name_mapping.get_actual_name(name)
        if actual_name not in existing_actual_names and name not in existing_display_names:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {name}")
        
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")
        
        result = kb_manager.query(
            kb_name=name,
            query_text=request.query,
            top_k=request.top_k
        )
        
        return {
            "success": True,
            "kb_name": name,
            "query": result['query'],
            "results": result['results'],
            "count": result['count']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kb/list")
async def list_knowledge_bases(_: bool = require_api_key):
    """
    获取所有知识库列表
    
    GET /kb/list
    
    返回的知识库列表中，name字段为显示名称（优先使用原始名称）
    """
    try:
        kb_info_list = kb_manager.list_knowledge_bases()
        
        return {
            "success": True,
            "knowledge_bases": kb_info_list,
            "count": len(kb_info_list)
        }
        
    except Exception as e:
        logger.error(f"获取知识库列表异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kb/{name}/docs")
async def get_knowledge_base_docs(
    name: str, 
    limit: Optional[int] = None,
    include_preview: bool = True,
    max_preview_chunks: int = 5,
    _: bool = require_api_key
):
    """
    获取知识库中的文档列表
    
    GET /kb/{name}/docs?limit=None&include_preview=true&max_preview_chunks=5
    
    参数说明：
    - limit: 返回数量限制，None表示不限制（获取全部文档），默认None
    - include_preview: 是否包含chunks预览，False时只返回文件列表和统计信息，默认True
    - max_preview_chunks: 每个文件最多返回的chunk预览数量，默认5
    """
    try:
        # 检查知识库是否存在（支持通过原始名称查找）
        existing_kbs_info = kb_manager.list_knowledge_bases()
        existing_actual_names = [kb['actual_name'] for kb in existing_kbs_info]
        existing_display_names = [kb['name'] for kb in existing_kbs_info]
        
        actual_name = kb_manager.vectorstore.name_mapping.get_actual_name(name)
        if actual_name not in existing_actual_names and name not in existing_display_names:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {name}")
        
        result = kb_manager.get_knowledge_base_docs(
            name, 
            limit=limit,
            include_preview=include_preview,
            max_preview_chunks=max_preview_chunks
        )
        
        return {
            "success": True,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档列表异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/kb/{name}")
async def delete_knowledge_base(name: str, _: bool = require_api_key):
    """
    删除知识库
    
    DELETE /kb/{name}
    """
    try:
        # 检查知识库是否存在（支持通过原始名称查找）
        existing_kbs_info = kb_manager.list_knowledge_bases()
        existing_actual_names = [kb['actual_name'] for kb in existing_kbs_info]
        existing_display_names = [kb['name'] for kb in existing_kbs_info]
        
        actual_name = kb_manager.vectorstore.name_mapping.get_actual_name(name)
        if actual_name not in existing_actual_names and name not in existing_display_names:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {name}")
        
        success = kb_manager.delete_knowledge_base(name)
        
        if success:
            return {
                "success": True,
                "message": f"知识库删除成功: {name}",
                "kb_name": name
            }
        else:
            raise HTTPException(status_code=500, detail="删除知识库失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/kb/{name}/docs")
async def delete_documents(name: str, request: DeleteDocsRequest, _: bool = require_api_key):
    """
    删除知识库中的文档
    
    DELETE /kb/{name}/docs
    {
        "doc_ids": ["id1", "id2"]
    }
    """
    try:
        # 检查知识库是否存在（支持通过原始名称查找）
        existing_kbs_info = kb_manager.list_knowledge_bases()
        existing_actual_names = [kb['actual_name'] for kb in existing_kbs_info]
        existing_display_names = [kb['name'] for kb in existing_kbs_info]
        
        actual_name = kb_manager.vectorstore.name_mapping.get_actual_name(name)
        if actual_name not in existing_actual_names and name not in existing_display_names:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {name}")
        
        if not request.doc_ids:
            raise HTTPException(status_code=400, detail="doc_ids不能为空")
        
        success = kb_manager.delete_documents(name, request.doc_ids)
        
        if success:
            return {
                "success": True,
                "message": f"成功删除 {len(request.doc_ids)} 个文档",
                "kb_name": name,
                "deleted_count": len(request.doc_ids)
            }
        else:
            raise HTTPException(status_code=500, detail="删除文档失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

