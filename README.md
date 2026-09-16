# RAG Knowledge Assistant

这是一个以 RAG（Retrieval-Augmented Generation，检索增强生成）为主线的 LangChain + FastAPI 淘宝知识库问答项目。系统会先检索订单、退款、物流、售后等资料，再把检索结果交给兼容 OpenAI API 的大模型生成回答。

## RAG 流程

```text
用户问题 -> 文档切块 -> TF-IDF 检索 -> 拼接参考资料 -> LLM 生成 -> 返回来源
```

核心实现位于 `rag/`，资料位于 `knowledge_base/`。检索器只使用 Python 标准库，因此不需要单独部署向量数据库；后续可以在同一接口替换为 Chroma、FAISS 或远程向量服务。

## 项目结构

```text
rag/
|- main.py                 # 共享 FastAPI RAG 服务
|- retriever.py            # 文档切块与 TF-IDF 检索
knowledge_base/             # 可直接编辑的 .md/.txt 知识库
rag_smoke_test.py           # 不依赖 LLM 的检索测试
basic/ ... withMemoryTest/  # 兼容入口，统一转发到共享 RAG 服务
```

## 安装与配置

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_BASE_URL=http://localhost:3000/v1
export OPENAI_API_KEY=your-key
export OPENAI_CHAT_MODEL=qwen-turbo
```

`OPENAI_BASE_URL` 可以指向 OneAPI 或其他 OpenAI-compatible 服务。不要把真实 API Key 写入代码或提交到仓库。

## 运行

先验证本地检索，不需要启动模型服务：

```bash
python rag_smoke_test.py
```

启动后端：

```bash
python -m rag.main
```

服务地址为 `http://localhost:8000`，接口文档为 `http://localhost:8000/docs`。历史目录仍可直接运行，例如 `python basic/main.py`，它们只是共享 RAG 服务的兼容入口，并分别保留原来的端口号。

### 本地网页

另开一个终端运行：

```bash
python -m http.server 8080 --directory basicWebUI
```

然后打开 `http://localhost:8080`。网页默认请求 `http://localhost:8000`。

### 放到个人主页展示

个人主页和 RAG 后端需要分别部署：

1. 将 `basicWebUI/index.html` 部署到 GitHub Pages、Vercel 或 Netlify。
2. 将 Python 后端部署到 Render、Railway、阿里云或自己的服务器，并获得 HTTPS 地址，例如 `https://your-rag-api.example.com`。
3. 在网页部署前，在 `index.html` 的脚本中加入：

```html
<script>
  window.RAG_API_URL = "https://your-rag-api.example.com";
</script>
```

   这段配置要放在原有问答脚本之前。
4. 后端启动时把主页域名加入允许跨域来源：

```bash
export RAG_ALLOWED_ORIGINS=https://your-homepage.example.com
python -m rag.main
```

不要把 `OPENAI_API_KEY` 放进网页代码。它只能配置在后端服务器环境变量中。

### 使用 Docker 部署

项目提供了 `Dockerfile`、`basicWebUI/Dockerfile` 和 `docker-compose.yml`。Docker Compose 会启动后端和 Nginx 网页，访客只需要访问同一个地址。

先在项目根目录创建 `.env`：

```dotenv
OPENAI_BASE_URL=https://你的云端模型地址/v1
OPENAI_API_KEY=你的真实密钥
OPENAI_CHAT_MODEL=qwen-turbo
RAG_ALLOWED_ORIGINS=http://localhost:8080
```

启动：

```bash
docker compose up -d --build
```

本地访问：`http://localhost:8080`。停止服务：

```bash
docker compose down
```

部署到公网服务器时，将 `8080:80` 改成 `80:80` 或由 HTTPS 反向代理转发到 8080，然后把 `OPENAI_BASE_URL` 配成云端可访问的模型服务地址。不要把 `.env` 提交到 Git，也不要把 API Key 写入前端页面。

## API

请求 `POST /v1/chat/completions`：

```json
{
  "messages": [{"role": "user", "content": "流量最多的套餐是什么？"}],
  "stream": false
}
```

回答会在末尾附上检索来源，例如 `telecom_plans.md#0`。健康检查使用 `GET /health`，编辑知识库后可调用 `POST /v1/knowledge/reload` 重新加载。

## 扩展知识库

将 `.md` 或 `.txt` 文件放入 `knowledge_base/`，然后调用 reload 接口。也可以通过 `RAG_KNOWLEDGE_DIR` 指定其他目录，通过 `RAG_TOP_K` 调整返回的文档数量。
