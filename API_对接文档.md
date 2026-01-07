# 📘 RAGBackend API 对接文档

> 本文档专为 Chrome 插件前端开发者设计，提供完整的 API 接口说明和示例代码。

## 📋 目录

1. [概述](#概述)
2. [基础配置](#基础配置)
3. [API端点](#api端点)
4. [数据模型](#数据模型)
5. [错误处理](#错误处理)
6. [JavaScript示例](#javascript示例)
7. [典型流程](#典型流程)

**注意**：Embedding配置在后端通过环境变量设置，前端无需配置相关API。

---

## 概述

RAGBackend 是一个基于 FastAPI 的知识库管理系统，提供知识库管理、文件上传、向量检索等功能。

**基础信息：**
- **基础URL**: `http://localhost:8000`（开发环境）
- **API版本**: v1.0.0
- **内容类型**: `application/json`（除文件上传外）
- **CORS**: 已配置允许跨域请求
- **Embedding模型**: 固定使用通义千问 text-embedding-v4（后端通过环境变量配置）

**API文档：**
- 交互式文档: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

**后端配置说明：**
- Embedding配置在后端通过环境变量 `DASHSCOPE_API_KEY` 设置
- 前端无需关心Embedding配置，直接使用API接口即可

---

## 基础配置

### Chrome插件中的API调用

```javascript
// 配置后端地址（建议存储在插件的storage中）
const API_BASE_URL = 'http://localhost:8000';

// 通用请求函数
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };
  
  try {
    const response = await fetch(url, config);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    
    return data;
  } catch (error) {
    console.error('API请求失败:', error);
    throw error;
  }
}
```

---

## API端点

### 1. 系统检查

#### 1.1 健康检查
```
GET /health
```

**响应示例：**
```json
{
  "status": "ok"
}
```

**JavaScript示例：**
```javascript
async function healthCheck() {
  return await apiRequest('/health');
}
```

---

### 2. 知识库管理

#### 2.1 创建知识库
```
POST /kb/create
```

**请求体：**
```json
{
  "name": "my_kb"
}
```

**注意**：
- 知识库名称必须符合Chroma DB规范：只能包含字母、数字、下划线和连字符(-)，3-63个字符
- 如果名称包含中文或特殊字符，系统会自动转换为符合规范的格式
- 请使用返回的 `kb_name` 作为后续操作的标识符

**响应示例（名称未转换）：**
```json
{
  "success": true,
  "message": "知识库创建成功: my_kb",
  "kb_name": "my_kb",
  "name_converted": false
}
```

**响应示例（名称已转换）：**
```json
{
  "success": true,
  "message": "知识库创建成功: APP_1000_abc12345（原名称：APP专项头部1000收录判断）",
  "kb_name": "APP_1000_abc12345",
  "original_name": "APP专项头部1000收录判断",
  "name_converted": true
}
```

**JavaScript示例：**
```javascript
async function createKnowledgeBase(name) {
  return await apiRequest('/kb/create', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}
```

---

#### 2.2 获取知识库列表
```
GET /kb/list
```

**响应示例：**
```json
{
  "success": true,
  "knowledge_bases": [
    {
      "name": "my_kb",
      "document_count": 150,
      "embedding_dimension": 1536
    }
  ],
  "count": 1
}
```

**JavaScript示例：**
```javascript
async function listKnowledgeBases() {
  return await apiRequest('/kb/list');
}
```

---

#### 2.3 获取知识库文档列表
```
GET /kb/{name}/docs?limit=100
```

**参数：**
- `name` (路径参数): 知识库名称
- `limit` (查询参数): 返回数量限制，默认100

**响应示例：**
```json
{
  "success": true,
  "kb_name": "my_kb",
  "total_documents": 150,
  "files": [
    {
      "filename": "example.pdf",
      "chunks": [
        {
          "id": "abc123...",
          "chunk_index": 0,
          "text_preview": "文档内容预览..."
        }
      ],
      "file_metadata": {
        "filename": "example.pdf",
        "file_type": "pdf",
        "total_pages": 10
      }
    }
  ]
}
```

**JavaScript示例：**
```javascript
async function getKnowledgeBaseDocs(kbName, limit = 100) {
  return await apiRequest(`/kb/${kbName}/docs?limit=${limit}`);
}
```

---

#### 2.4 删除知识库
```
DELETE /kb/{name}
```

**响应示例：**
```json
{
  "success": true,
  "message": "知识库删除成功: my_kb",
  "kb_name": "my_kb"
}
```

**JavaScript示例：**
```javascript
async function deleteKnowledgeBase(name) {
  return await apiRequest(`/kb/${name}`, {
    method: 'DELETE',
  });
}
```

---

### 3. 文件管理

#### 3.1 上传文件到知识库
```
POST /kb/{name}/upload?split_strategy=newline&chunk_size=500&chunk_overlap=50
Content-Type: multipart/form-data
```

**路径参数：**
- `name`: 知识库名称

**查询参数（可选）：**
- `split_strategy`: 切分策略，默认 `fixed`
  - `fixed`: 固定长度切分
  - `newline`: 按换行符切分
  - `paragraph`: 按段落切分（双换行）
  - `sentence`: 按句子切分
  - `smart`: 智能切分（优先段落，然后句子，最后固定长度）
- `chunk_size`: Chunk大小（字符数），默认 `400`
- `chunk_overlap`: Chunk重叠大小，默认 `50`

**表单数据：**
- `file` (FormData): 上传的文件

**支持的文件格式：**
- PDF (.pdf)
- 文本文件 (.txt)
- Word文档 (.docx)
- Markdown (.md)

**响应示例：**
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

**JavaScript示例：**
```javascript
async function uploadFile(kbName, file, splitStrategy = 'fixed', chunkSize = 400, chunkOverlap = 50) {
  const formData = new FormData();
  formData.append('file', file);
  
  // 构建查询参数
  const params = new URLSearchParams({
    split_strategy: splitStrategy,
    chunk_size: chunkSize.toString(),
    chunk_overlap: chunkOverlap.toString()
  });
  
  const response = await fetch(`${API_BASE_URL}/kb/${kbName}/upload?${params}`, {
    method: 'POST',
    body: formData,
    // 注意：不要设置Content-Type，浏览器会自动设置multipart/form-data
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return await response.json();
}

// 使用示例 - 默认策略
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];
await uploadFile('my_kb', file);

// 使用示例 - 按换行符切分
await uploadFile('my_kb', file, 'newline');

// 使用示例 - 自定义参数
await uploadFile('my_kb', file, 'paragraph', 500, 100);
```

**Chrome插件中使用FileReader：**
```javascript
// 从插件中读取文件
async function uploadFileFromChrome(kbName, fileEntry, splitStrategy = 'fixed', chunkSize = 400, chunkOverlap = 50) {
  return new Promise((resolve, reject) => {
    fileEntry.file((file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      // 构建查询参数
      const params = new URLSearchParams({
        split_strategy: splitStrategy,
        chunk_size: chunkSize.toString(),
        chunk_overlap: chunkOverlap.toString()
      });
      
      fetch(`${API_BASE_URL}/kb/${kbName}/upload?${params}`, {
        method: 'POST',
        body: formData,
      })
      .then(response => response.json())
      .then(resolve)
      .catch(reject);
    });
  });
}
```

---

#### 3.2 获取切分策略列表
```
GET /kb/split-strategies
```

**响应示例：**
```json
{
  "success": true,
  "strategies": {
    "fixed": "固定长度切分",
    "newline": "按换行符切分",
    "paragraph": "按段落切分（双换行）",
    "sentence": "按句子切分",
    "smart": "智能切分（优先段落，然后句子，最后固定长度）"
  }
}
```

**JavaScript示例：**
```javascript
async function getSplitStrategies() {
  return await apiRequest('/kb/split-strategies');
}

// 使用示例：动态填充策略选择下拉框
async function loadStrategiesToSelect(selectElement) {
  const result = await getSplitStrategies();
  if (result.success && result.strategies) {
    selectElement.innerHTML = '';
    for (const [key, description] of Object.entries(result.strategies)) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = `${key} - ${description}`;
      selectElement.appendChild(option);
    }
  }
}
```

---

#### 3.3 删除文档
```
DELETE /kb/{name}/docs
```

**请求体：**
```json
{
  "doc_ids": ["id1", "id2", "id3"]
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "成功删除 3 个文档",
  "kb_name": "my_kb",
  "deleted_count": 3
}
```

**JavaScript示例：**
```javascript
async function deleteDocuments(kbName, docIds) {
  return await apiRequest(`/kb/${kbName}/docs`, {
    method: 'DELETE',
    body: JSON.stringify({ doc_ids: docIds }),
  });
}
```

---

### 4. 查询功能

#### 4.1 查询知识库
```
POST /kb/{name}/query
```

**请求体：**
```json
{
  "query": "你的问题",
  "top_k": 5
}
```

**参数说明：**
- `query` (必需): 查询文本
- `top_k` (可选): 返回结果数量，默认5

**响应示例：**
```json
{
  "success": true,
  "kb_name": "my_kb",
  "query": "什么是人工智能？",
  "results": [
    {
      "text": "人工智能（AI）是...",
      "score": 0.85,
      "distance": 0.15,
      "metadata": {
        "filename": "example.pdf",
        "chunk_index": 3,
        "file_type": "pdf",
        "total_chunks": 15
      },
      "id": "abc123def456..."
    }
  ],
  "count": 5
}
```

**JavaScript示例：**
```javascript
async function queryKnowledgeBase(kbName, query, topK = 5) {
  return await apiRequest(`/kb/${kbName}/query`, {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  });
}
```

---

## 数据模型

### 知识库信息
```typescript
interface KnowledgeBase {
  name: string;
  document_count: number;
  embedding_dimension?: number;
}
```

### 查询结果
```typescript
interface QueryResult {
  text: string;
  score: number;        // 相似度分数 (0-1)
  distance: number;     // 向量距离
  metadata: {
    filename: string;
    chunk_index: number;
    total_chunks: number;
    file_type: string;
    [key: string]: any;
  };
  id: string;
}
```


---

## 错误处理

### HTTP状态码

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### JavaScript错误处理示例

```javascript
async function safeApiRequest(endpoint, options = {}) {
  try {
    const result = await apiRequest(endpoint, options);
    return { success: true, data: result };
  } catch (error) {
    console.error('API请求失败:', error);
    return {
      success: false,
      error: error.message || '未知错误',
    };
  }
}

// 使用示例
const result = await safeApiRequest('/kb/list');
if (result.success) {
  console.log('知识库列表:', result.data);
} else {
  alert(`错误: ${result.error}`);
}
```

---

## JavaScript示例

### 完整的API客户端类

```javascript
class RAGBackendClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
      config.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return data;
  }

  // 健康检查
  async healthCheck() {
    return await this.request('/health');
  }

  // 知识库管理
  async createKB(name) {
    return await this.request('/kb/create', {
      method: 'POST',
      body: { name },
    });
  }

  async listKBs() {
    return await this.request('/kb/list');
  }

  async getKBDocs(kbName, limit = 100) {
    return await this.request(`/kb/${kbName}/docs?limit=${limit}`);
  }

  async deleteKB(name) {
    return await this.request(`/kb/${name}`, { method: 'DELETE' });
  }

  // 文件管理
  async uploadFile(kbName, file) {
    const formData = new FormData();
    formData.append('file', file);

    return await this.request(`/kb/${kbName}/upload`, {
      method: 'POST',
      body: formData,
      headers: {}, // 让浏览器自动设置Content-Type
    });
  }

  async deleteDocuments(kbName, docIds) {
    return await this.request(`/kb/${kbName}/docs`, {
      method: 'DELETE',
      body: { doc_ids: docIds },
    });
  }

  // 查询
  async query(kbName, query, topK = 5) {
    return await this.request(`/kb/${kbName}/query`, {
      method: 'POST',
      body: { query, top_k: topK },
    });
  }

}

// 使用示例
const client = new RAGBackendClient('http://localhost:8000');

// 创建知识库
await client.createKB('my_kb');

// 上传文件
const file = document.getElementById('fileInput').files[0];
await client.uploadFile('my_kb', file);

// 查询
const results = await client.query('my_kb', '什么是人工智能？', 5);
console.log(results.results);
```

---

## 典型流程

### 流程1: 创建知识库并上传文件

```javascript
// 1. 创建知识库
await client.createKB('my_kb');

// 2. 上传文件
const file = /* 从文件选择器或拖拽获取 */;
const uploadResult = await client.uploadFile('my_kb', file);
console.log(`上传成功，切分为 ${uploadResult.chunks_count} 个chunks`);
```

### 流程2: 查询知识库

```javascript
// 1. 查询
const queryResult = await client.query('my_kb', '你的问题', 5);

// 2. 处理结果
queryResult.results.forEach((result, index) => {
  console.log(`结果 ${index + 1}:`);
  console.log(`  文本: ${result.text}`);
  console.log(`  相似度: ${result.score}`);
  console.log(`  来源: ${result.metadata.filename}`);
});
```

### 流程3: 管理知识库

```javascript
// 1. 获取所有知识库
const kbs = await client.listKBs();
console.log(`共有 ${kbs.count} 个知识库`);

// 2. 查看某个知识库的文档
const docs = await client.getKBDocs('my_kb');
console.log(`知识库包含 ${docs.files.length} 个文件`);

// 3. 删除文档
await client.deleteDocuments('my_kb', ['doc_id_1', 'doc_id_2']);

// 4. 删除知识库
await client.deleteKB('my_kb');
```

---

## 注意事项

1. **后端配置**: Embedding模型在后端通过环境变量配置，前端无需关心配置。
   - 后端需要设置 `DASHSCOPE_API_KEY` 环境变量
   - 获取API Key: https://help.aliyun.com/zh/model-studio/get-api-key
   - 可选环境变量: `TONGYI_API_BASE_URL`, `TONGYI_EMBEDDING_MODEL`
2. **固定使用通义千问模型**，系统默认使用 `text-embedding-v4` 模型。
3. **文件上传使用 `multipart/form-data`**，不要手动设置 `Content-Type`。
4. **向量维度不匹配时**，需要重新上传文档或创建新的知识库。

---

## 支持与反馈

如有问题或建议，请访问：
- **API文档**: `http://localhost:8000/docs`
- **OpenAPI规范**: `http://localhost:8000/openapi.json`

---

**最后更新**: 2024-01-01  
**API版本**: v1.0.0

