# 淘宝知识库问答助手

<p align="center">
  <img src="https://raw.githubusercontent.com/CLX-great/RAG-taobao-knowledge-base-qa/main/docs/cover-banner.svg" alt="淘宝知识库问答助手封面" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/RAG-Knowledge%20QA-FF7A59?style=for-the-badge" alt="RAG" />
</p>

一个基于 RAG（Retrieval-Augmented Generation，检索增强生成）思路实现的淘宝知识库问答系统。它会先从知识库中检索与用户问题最相关的文档，再把检索结果和问题一起发送给大模型生成回答，并在最终输出中附带参考来源。

该项目适用于电商场景中的客服、售后、订单与退换货等知识问答场景，能够帮助用户快速定位答案、降低人工客服压力。

## 项目效果

- 支持订单相关咨询
- 支持退换货、物流和售后问题
- 支持优惠券和活动规则查询
- 每次回答都附带参考来源，易于核验
- 支持直接扩展知识库内容

## Demo 预览

<p align="center">
  <img src="https://raw.githubusercontent.com/CLX-great/RAG-taobao-knowledge-base-qa/main/docs/demo-preview.svg" alt="Demo 预览" width="100%" />
</p>

## 技术栈

- Python
- FastAPI
- TF-IDF 检索
- OpenAI 兼容接口
- 阿里云 DashScope（可替换为其他兼容模型服务）

## 系统流程

```text
用户提问
   ↓
读取知识库
   ↓
文档分块与检索
   ↓
召回相关资料
   ↓
拼接上下文
   ↓
大模型生成答案
   ↓
返回回答 + 参考来源
```

## 项目结构

```text
.
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements-server.txt
├── rag_smoke_test.py
├── rag/
│   ├── __init__.py
│   ├── main.py
│   └── retriever.py
├── knowledge_base/
│   └── telecom_plans.md
├── basic/
│   ├── main.py
│   ├── apiTest.py
│   ├── prompt_template_system.txt
│   └── prompt_template_user.txt
├── basicWebUI/
│   ├── index.html
│   ├── main.py
│   ├── apiWebUI.py
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── prompt_template_system.txt
│   └── prompt_template_user.txt
├── cot/
├── selfConsistency/
├── sportservice/
├── withMemoryTest/
└── ...
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置模型环境变量

当前示例使用阿里云 DashScope 的 OpenAI 兼容接口：

```bash
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export OPENAI_API_KEY=你的真实API_Key
export OPENAI_CHAT_MODEL=qwen-plus
```

说明：

- `OPENAI_BASE_URL` 是 DashScope 的兼容模式地址
- `OPENAI_API_KEY` 仅应保存在后端环境变量中
- `OPENAI_CHAT_MODEL` 使用 `qwen-plus`
- 不要把真实密钥写进前端页面，也不要提交到 Git 仓库

### 3. 先验证本地检索

```bash
python rag_smoke_test.py
```

该步骤不依赖真实模型，可先确认知识库和文本检索工作正常。

### 4. 启动后端服务

```bash
python -m rag.main
```

访问地址：

- http://localhost:8000
- http://localhost:8000/docs

### 5. 启动前端页面

另开一个终端：

```bash
python -m http.server 8080 --directory basicWebUI
```

然后打开：

```text
http://localhost:8080
```

前端默认请求后端地址：`http://localhost:8000`。

## 一键演示

如果你只是想本地快速体验，直接执行：

```bash
python rag_smoke_test.py
python -m rag.main
```

然后打开浏览器访问：

```text
http://localhost:8080
```

即可看到和截图相似的淘宝知识库问答助手交互效果。

## Docker 部署

项目自带 `Dockerfile` 和 `docker-compose.yml`，可以直接启动：

### 1. 配置 `.env`

```dotenv
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=你的真实API_Key
OPENAI_CHAT_MODEL=qwen-plus
RAG_ALLOWED_ORIGINS=http://localhost:8080
```

### 2. 启动服务

```bash
docker compose up -d --build
```

### 3. 访问

```text
http://localhost:8080
```

### 4. 停止

```bash
docker compose down
```

## API 文档

后端兼容 OpenAI 接口，核心地址：

```http
POST /v1/chat/completions
```

示例请求：

```json
{
  "messages": [
    {"role": "user", "content": "流量最多的套餐是什么？"}
  ],
  "stream": false
}
```

返回结果中会附带参考来源，例如：

```text
telecom_plans.md#0
```

其他接口：

- `GET /health`：健康检查
- `POST /v1/knowledge/reload`：重新加载知识库

## Knowledge Base 扩展

将 `.md` 或 `.txt` 文件放到 `knowledge_base/` 目录下，再调用 reload 接口即可更新问答知识库。

如果需要调整召回数量，可设置：

```bash
export RAG_TOP_K=5
```

或者通过 `RAG_KNOWLEDGE_DIR` 指定自定义知识库目录。

## 适用场景

- 电商客服问答助手
- 售后与退款知识库查询
- 订单问题智能解答
- 运营规则检索工具
- 面向 Demo 的轻量 RAG 应用

## 备注

- 目前知识库内容位于 `knowledge_base/`
- 当前实现不依赖向量数据库，适合小型知识库快速落地
- 后续可以替换为 Chroma、FAISS 或其他更强的向量检索方案

## License

本项目已附带 MIT License，适合开源展示和二次开发。详见 [LICENSE](LICENSE)。

## Git Ignore

该仓库已补充 `.gitignore`，已覆盖 Python 虚拟环境、缓存目录、IDE 配置和敏感环境变量文件，避免把 `.venv`、`.env`、缓存文件等不必要内容上传到 Git。

如果你将该项目用于展示、汇报或上线部署，建议优先准备真实业务知识库，再绑定稳定的 DashScope 模型参数即可。
