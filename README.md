# 📚 轻量级知识库管理后端

基于 **FastAPI** + **Chroma DB** 的轻量级知识库管理系统，专为 Chrome 插件设计。

## ✨ 功能特性

- ✅ **创建知识库** - 支持多个独立的知识库（collection）
- ✅ **文件上传** - 支持 PDF、TXT、DOCX、MD 文件解析
- ✅ **自动向量化** - 使用通义千问 text-embedding-v4 模型生成向量
- ✅ **智能切分** - 自动将文档切分为适合检索的 chunks
- ✅ **向量检索** - 支持自然语言查询，返回 top-k 相关片段
- ✅ **持久化存储** - 使用 Chroma PersistentClient 持久化数据
- ✅ **文档管理** - 查看、删除知识库和文档
- ✅ **去重功能** - 自动检测并跳过重复文档

## 🛠️ 技术栈

- **FastAPI** - 现代 Python Web 框架
- **Chroma DB** - 向量数据库（PersistentClient）
- **通义千问** - Embedding 模型（text-embedding-v4，使用OpenAI兼容API）
- **pdfplumber** - PDF 解析
- **python-docx** - DOCX 解析

## 📦 安装

### 1. 克隆项目（或直接使用）

```bash
cd RAGBackend
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

设置通义千问API Key：

```bash
# Windows (CMD)
set DASHSCOPE_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:DASHSCOPE_API_KEY="your_api_key_here"

# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key_here
```

**获取API Key**: https://help.aliyun.com/zh/model-studio/get-api-key

**可选环境变量**：
- `TONGYI_API_BASE_URL`: API地址（默认：`https://dashscope.aliyuncs.com/compatible-mode/v1`）
- `TONGYI_EMBEDDING_MODEL`: 模型名称（默认：`text-embedding-v4`）

## 🚀 运行

```bash
uvicorn app:app --reload
```

服务将在 `http://localhost:8000` 启动。

访问 `http://localhost:8000/docs` 查看交互式 API 文档。

> **📘 前端对接文档**: 请查看 [API_对接文档.md](API_对接文档.md) 获取完整的 Chrome 插件对接指南。

## 📡 API 接口

### 1. 创建知识库

```bash
curl -X POST "http://localhost:8000/kb/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "my_kb"}'
```

**响应：**
```json
{
  "success": true,
  "message": "知识库创建成功: my_kb",
  "kb_name": "my_kb"
}
```

### 2. 上传文件

```bash
curl -X POST "http://localhost:8000/kb/my_kb/upload" \
  -F "file=@example.pdf"
```

**响应：**
```json
{
  "success": true,
  "message": "文件上传成功",
  "kb_name": "my_kb",
  "filename": "example.pdf",
  "chunks_count": 15,
  "file_metadata": {
    "filename": "example.pdf",
    "file_type": "pdf",
    "total_pages": 10
  }
}
```

### 3. 查询知识库

```bash
curl -X POST "http://localhost:8000/kb/my_kb/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是人工智能？",
    "top_k": 5
  }'
```

**响应：**
```json
{
  "success": true,
  "kb_name": "my_kb",
  "query": "什么是人工智能？",
  "results": [
    {
      "text": "人工智能是...",
      "score": 0.85,
      "distance": 0.15,
      "metadata": {
        "filename": "example.pdf",
        "chunk_index": 3,
        "file_type": "pdf"
      },
      "id": "abc123..."
    }
  ],
  "count": 5
}
```

### 4. 获取知识库列表

```bash
curl -X GET "http://localhost:8000/kb/list"
```

**响应：**
```json
{
  "success": true,
  "knowledge_bases": [
    {
      "name": "my_kb",
      "document_count": 150
    }
  ],
  "count": 1
}
```

### 5. 获取知识库文档

```bash
curl -X GET "http://localhost:8000/kb/my_kb/docs?limit=100"
```

### 6. 删除知识库

```bash
curl -X DELETE "http://localhost:8000/kb/my_kb"
```

### 7. 删除文档

```bash
curl -X DELETE "http://localhost:8000/kb/my_kb/docs" \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": ["id1", "id2"]}'
```

## 📁 项目结构

```
RAGBackend/
├── app.py                      # FastAPI 主应用
├── knowledge_base/
│   ├── __init__.py
│   ├── manager.py              # 知识库管理器
│   ├── loader.py               # 文档加载器
│   ├── splitter.py             # 文本切分器
│   ├── embedder.py             # Embedding 模型
│   └── vectorstore.py          # Chroma 向量存储
├── data/                       # 持久化向量库目录（自动创建）
├── requirements.txt            # 依赖列表
└── README.md                   # 项目文档
```

## ⚙️ 配置说明

### 文本切分参数

在 `knowledge_base/splitter.py` 中可调整：

- `chunk_size`: 每个 chunk 的字符数（默认 400）
- `chunk_overlap`: chunk 之间的重叠字符数（默认 50）

### Embedding 模型

固定使用**通义千问 text-embedding-v4**模型，通过OpenAI兼容API调用。

**配置方式（必须）：**
设置环境变量 `DASHSCOPE_API_KEY`，获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key

**默认配置：**
- 模型：`text-embedding-v4`（可通过 `TONGYI_EMBEDDING_MODEL` 环境变量修改）
- API地址（北京地域，默认）：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- API地址（新加坡地域）：`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`（通过 `TONGYI_API_BASE_URL` 设置）

**注意**：未设置 `DASHSCOPE_API_KEY` 时服务将无法启动。

### 持久化目录

向量库数据默认存储在 `./data` 目录，可在 `app.py` 中修改：

```python
kb_manager = KnowledgeBaseManager(persist_directory="./data")
```

## 🔧 开发说明

### 添加新的文件类型支持

1. 在 `knowledge_base/loader.py` 的 `SUPPORTED_EXTENSIONS` 中添加扩展名
2. 实现对应的 `_load_xxx` 方法

### Embedding 模型配置

系统固定使用通义千问模型，通过环境变量配置：

```bash
# 设置API Key（必需）
export DASHSCOPE_API_KEY=your_api_key

# 可选：自定义API地址（新加坡地域）
export TONGYI_API_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1

# 可选：自定义模型名称
export TONGYI_EMBEDDING_MODEL=text-embedding-v4
```

## 🐛 常见问题

### 1. API Key配置

首次使用需要配置通义千问API Key：

- 获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
- 通过 `POST /config/embedding` 接口配置
- 或设置环境变量 `DASHSCOPE_API_KEY`

### 2. 内存占用高

- 减少 `chunk_size`
- 使用更小的 embedding 模型
- 限制单次查询的 `top_k` 数量

### 3. PDF 解析失败

确保安装了 `pdfplumber` 及其依赖（可能需要系统级的 PDF 处理库）。

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Happy Coding! 🎉**

