# 📚 RAGBackend - 轻量级知识库管理后端

基于 **FastAPI** + **Chroma DB** + **通义千问** 的轻量级知识库管理系统，专为 RAG（检索增强生成）场景设计，支持 Chrome 插件等前端应用集成。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 功能特性

- ✅ **多知识库管理** - 支持创建多个独立的知识库（Chroma collections）
- ✅ **文件上传与解析** - 支持 PDF、TXT、DOCX、MD 文件自动解析和提取
- ✅ **智能文本切分** - 提供5种切分策略（固定长度、按行、按段落、按句子、智能切分）
- ✅ **自动向量化** - 集成通义千问 text-embedding-v4 模型，自动生成文档向量
- ✅ **向量检索** - 支持自然语言查询，返回 top-k 相关文档片段
- ✅ **持久化存储** - 使用 Chroma PersistentClient 持久化向量数据
- ✅ **文档去重** - 自动检测并跳过重复文档，支持不同切分策略的去重
- ✅ **API 密钥认证** - 支持 API 密钥保护，防止未授权访问
- ✅ **名称映射管理** - 自动处理中文和特殊字符的知识库名称
- ✅ **灵活的查询接口** - 支持按需加载文档列表，优化性能

## 🛠️ 技术栈

- **FastAPI** - 现代、高性能的 Python Web 框架
- **Chroma DB** - 开源向量数据库，支持持久化存储
- **通义千问** - 阿里云 embedding 模型（text-embedding-v4，OpenAI 兼容 API）
- **pdfplumber** - PDF 文件解析
- **python-docx** - DOCX 文件解析
- **sentence-transformers** - 文本处理（可选，当前使用通义千问）

## 📦 快速开始

### 1. 环境要求

- Python 3.8+
- pip 或 conda

### 2. 克隆项目

```bash
git clone https://github.com/pgnzbl/RagBackend.git
cd RagBackend
```

### 3. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 配置环境变量

#### 必需配置

**通义千问 API Key**（用于文档向量化）：

```bash
# Windows (CMD)
set DASHSCOPE_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:DASHSCOPE_API_KEY="your_api_key_here"

# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key_here
```

**获取 API Key**: https://help.aliyun.com/zh/model-studio/get-api-key

#### 可选配置

**API 密钥认证**（保护 API 端点，防止未授权访问）：

```bash
# Windows
set API_KEY=your_secret_api_key_here

# Linux/Mac
export API_KEY=your_secret_api_key_here
```

> **⚠️ 重要**：如果未设置 `API_KEY`，API 将跳过鉴权验证（仅用于开发环境）。**生产环境部署到公网时，强烈建议设置 `API_KEY`！**

**其他可选环境变量**：
- `TONGYI_API_BASE_URL`: API 地址（默认：`https://dashscope.aliyuncs.com/compatible-mode/v1`）
- `TONGYI_EMBEDDING_MODEL`: 模型名称（默认：`text-embedding-v4`）

### 6. 运行服务

```bash
uvicorn app:app --reload
```

服务将在 `http://localhost:8000` 启动。

访问以下地址查看 API 文档：
- 交互式文档：http://localhost:8000/docs
- OpenAPI JSON：http://localhost:8000/openapi.json

## 🔒 API 认证

### 配置 API 密钥

设置环境变量 `API_KEY` 后，所有业务 API 都需要在请求头中包含该密钥：

```bash
X-API-Key: your_secret_api_key_here
```

### 不需要认证的端点

- `GET /` - API 信息
- `GET /health` - 健康检查

### 前端集成示例

```javascript
// JavaScript/Chrome插件
async function apiRequest(endpoint, options = {}) {
  const apiKey = await getApiKey(); // 从配置中获取
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,  // 添加API密钥
      ...options.headers,
    },
  });
  
  if (response.status === 401) {
    throw new Error('缺少API密钥');
  }
  if (response.status === 403) {
    throw new Error('API密钥无效');
  }
  
  return response.json();
}
```

## 📖 API 使用示例

### 1. 创建知识库

```bash
curl -X POST "http://localhost:8000/kb/create" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"name": "my_knowledge_base"}'
```

**响应**：
```json
{
  "success": true,
  "message": "知识库创建成功: kb_xxxxx",
  "kb_name": "kb_xxxxx",
  "original_name": "my_knowledge_base",
  "name_converted": true
}
```

### 2. 上传文件

```bash
curl -X POST "http://localhost:8000/kb/my_kb/upload?split_strategy=newline" \
  -H "X-API-Key: your_api_key" \
  -F "file=@document.pdf"
```

**参数说明**：
- `split_strategy`: 切分策略（`fixed`/`newline`/`paragraph`/`sentence`/`smart`），默认 `fixed`
- `chunk_size`: chunk 大小（字符数），默认 400
- `chunk_overlap`: chunk 重叠大小，默认 50

### 3. 查询知识库

```bash
curl -X POST "http://localhost:8000/kb/my_kb/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "query": "人工智能的应用场景",
    "top_k": 5
  }'
```

**响应**：
```json
{
  "success": true,
  "kb_name": "my_kb",
  "query": "人工智能的应用场景",
  "results": [
    {
      "text": "文档片段内容...",
      "score": 0.85,
      "distance": 0.15,
      "metadata": {
        "filename": "document.pdf",
        "chunk_index": 3
      },
      "id": "doc_id_xxx"
    }
  ],
  "count": 5
}
```

### 4. 获取文档列表

```bash
# 获取完整列表（包含预览）
curl "http://localhost:8000/kb/my_kb/docs?include_preview=true&max_preview_chunks=5" \
  -H "X-API-Key: your_api_key"

# 只获取文件列表（轻量级）
curl "http://localhost:8000/kb/my_kb/docs?include_preview=false" \
  -H "X-API-Key: your_api_key"
```

**参数说明**：
- `limit`: 文档数量限制（默认：不限制）
- `include_preview`: 是否包含 chunk 预览（默认：`true`）
- `max_preview_chunks`: 每个文件最多返回的预览数量（默认：`5`）

### 5. 删除文档

```bash
curl -X DELETE "http://localhost:8000/kb/my_kb/docs" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"doc_ids": ["id1", "id2"]}'
```

### 6. 删除知识库

```bash
curl -X DELETE "http://localhost:8000/kb/my_kb" \
  -H "X-API-Key: your_api_key"
```

## 📁 项目结构

```
RAGBackend/
├── app.py                      # FastAPI 主应用
├── requirements.txt            # Python 依赖
├── README.md                   # 项目文档
├── .gitignore                  # Git 忽略规则
│
├── knowledge_base/             # 核心模块
│   ├── __init__.py
│   ├── manager.py              # 知识库管理器（核心逻辑）
│   ├── vectorstore.py          # Chroma 向量存储封装
│   ├── embedder.py             # Embedding 模型封装
│   ├── loader.py               # 文档加载器（PDF/TXT/DOCX/MD）
│   ├── splitter.py             # 文本切分器（5种策略）
│   ├── name_mapping.py         # 名称映射管理
│   ├── utils.py                # 工具函数
│   ├── config.py               # 配置模型
│   ├── config_store.py         # 配置存储
│   │
│   └── embedders/              # Embedding 实现
│       ├── __init__.py
│       ├── base.py             # 抽象基类
│       ├── factory.py          # 工厂类
│       └── tongyi.py           # 通义千问实现
│
└── data/                       # 数据目录（自动创建）
    ├── .gitkeep
    ├── name_mapping.json       # 名称映射（运行时生成）
    ├── name_mapping.json.example
    └── chroma.sqlite3          # Chroma 数据库（运行时生成）
```

## ⚙️ 配置说明

### 文本切分策略

系统支持 5 种文本切分策略：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `fixed` | 固定长度切分 | 通用场景，保证chunk大小均匀 |
| `newline` | 按换行符切分 | 代码、结构化文本 |
| `paragraph` | 按段落切分（双换行） | 文章、文档 |
| `sentence` | 按句子切分 | 需要保持语义完整性 |
| `smart` | 智能切分 | 优先段落，然后句子，最后固定长度 |

**配置方式**：上传文件时通过 `split_strategy` 参数指定。

### Embedding 模型配置

**固定使用**：通义千问 `text-embedding-v4` 模型

- **向量维度**：1024
- **API 地址**：可通过 `TONGYI_API_BASE_URL` 环境变量配置
  - 北京地域（默认）：`https://dashscope.aliyuncs.com/compatible-mode/v1`
  - 新加坡地域：`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

### 持久化存储

向量库数据默认存储在 `./data` 目录：

- 数据库文件：`data/chroma.sqlite3`
- 向量索引：`data/{collection_id}/`
- 名称映射：`data/name_mapping.json`

可在 `app.py` 中修改存储路径：

```python
kb_manager = KnowledgeBaseManager(persist_directory="./data")
```

### 知识库名称处理

- 支持中文和特殊字符的知识库名称
- 自动转换为 Chroma DB 兼容的格式（如：`kb_xxxxx`）
- 自动维护原始名称和实际名称的映射关系
- API 调用时支持使用原始名称或实际名称

## 🔧 开发说明

### 添加新的文件类型支持

1. 在 `knowledge_base/loader.py` 的 `DocumentLoader` 类中添加解析逻辑
2. 在 `SUPPORTED_EXTENSIONS` 中添加文件扩展名
3. 实现对应的 `_load_xxx` 方法

### 添加新的 Embedding 模型

1. 在 `knowledge_base/embedders/` 目录下创建新的实现类
2. 继承 `BaseEmbedder` 抽象类
3. 实现 `embed()` 和 `embed_query()` 方法
4. 在 `factory.py` 中注册新模型

### 本地开发

```bash
# 启用自动重载
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 指定日志级别
uvicorn app:app --log-level debug
```

### 生产部署

```bash
# 使用 Gunicorn（推荐）
pip install gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用 Docker（需要自行编写 Dockerfile）
```

## 🐛 常见问题

### Q: 上传文件时提示 "API Key 未配置"

**A**: 确保已设置 `DASHSCOPE_API_KEY` 环境变量，并且 API Key 有效。

### Q: API 请求返回 401 或 403 错误

**A**: 
- 401：请求头中缺少 `X-API-Key`
- 403：API 密钥无效，检查环境变量 `API_KEY` 是否配置正确

### Q: 上传的文件在文档列表中看不到

**A**: 
- 检查文件是否成功上传（查看日志）
- 检查 `limit` 参数是否足够大
- 尝试使用 `include_preview=false` 获取完整文件列表

### Q: 知识库名称被转换了，前端无法识别

**A**: 系统会自动处理名称映射，API 返回的 `name` 字段是显示名称（原始名称），`actual_name` 是实际存储名称。前端应使用 `name` 字段进行显示和后续调用。

### Q: 文档去重不工作

**A**: 文档 ID 基于内容、文件名、切分策略生成。如果使用相同的切分策略上传相同内容，会被自动去重。如需重新上传，可以：
1. 使用不同的切分策略
2. 先删除旧文档再上传

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

- GitHub: https://github.com/pgnzbl/RagBackend
- Issues: https://github.com/pgnzbl/RagBackend/issues

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [Chroma](https://www.trychroma.com/) - 开源向量数据库
- [通义千问](https://tongyi.aliyun.com/) - 阿里云大模型服务

---

⭐ 如果这个项目对你有帮助，请给个 Star！
