"""FastAPI RAG service with an OpenAI-compatible chat endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rag.retriever import TfidfRetriever, load_chunks


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = Path(os.getenv("RAG_KNOWLEDGE_DIR", ROOT / "knowledge_base"))
PORT = int(os.getenv("RAG_PORT", "8000"))
TOP_K = int(os.getenv("RAG_TOP_K", "4"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("RAG_ALLOWED_ORIGINS", "http://localhost:8080").split(",")
    if origin.strip()
]


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[Message]
    stream: Optional[bool] = False


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    choices: list[ChatCompletionResponseChoice]


retriever: TfidfRetriever | None = None
model: ChatOpenAI | None = None
chain = None


def build_context(results) -> str:
    if not results:
        return "未检索到相关资料。"
    return "\n\n".join(
        f"[来源: {Path(item.source).name}#{item.chunk_id}]\n{item.text}" for item in results
    )


def format_sources(results) -> str:
    if not results:
        return "\n\n参考来源：未检索到相关资料。"
    sources = ", ".join(f"{Path(item.source).name}#{item.chunk_id}" for item in results)
    return f"\n\n参考来源：{sources}"


def build_fallback_answer(query: str, results) -> str:
    if not results:
        return "根据当前淘宝知识库，暂时没有找到和该问题直接相关的信息。请尝试更具体地描述订单、退款、物流或售后问题。"
    top = results[0]
    answer = (
        "根据淘宝知识库中的相关内容：\n\n"
        f"{top.text}\n\n"
        "如果你需要进一步确认具体订单情况，建议提供订单号、商品信息或问题场景。"
    )
    return answer


@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever, model, chain
    chunks = load_chunks(KNOWLEDGE_DIR)
    retriever = TfidfRetriever(chunks)
    logger.info("已加载 %d 个知识库分片", len(chunks))
    model = ChatOpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:3000/v1"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_CHAT_MODEL", "qwen-turbo"),
        temperature=0.2,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个严谨的知识库问答助手。只能依据给定的参考资料回答；资料不足时明确说明，不要编造。回答使用中文。"),
        ("human", "参考资料：\n{context}\n\n用户问题：\n{query}"),
    ])
    chain = prompt | model
    yield


app = FastAPI(title="RAG Knowledge Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "knowledge_base": str(KNOWLEDGE_DIR), "chunks": len(retriever.chunks) if retriever else 0}


@app.post("/v1/knowledge/reload")
def reload_knowledge():
    global retriever
    retriever = TfidfRetriever(load_chunks(KNOWLEDGE_DIR))
    return {"status": "ok", "chunks": len(retriever.chunks)}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if retriever is None or chain is None:
        raise HTTPException(status_code=503, detail="RAG 服务尚未初始化")
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    query = request.messages[-1].content
    results = retriever.search(query, TOP_K)
    try:
        result = chain.invoke({"query": query, "context": build_context(results)})
        content = f"{result.content}{format_sources(results)}"
    except Exception as exc:
        logger.warning("LLM invocation failed, using FAQ fallback answer: %s", exc)
        content = f"{build_fallback_answer(query, results)}{format_sources(results)}"
    if not request.stream:
        response = ChatCompletionResponse(choices=[ChatCompletionResponseChoice(
            index=0, message=Message(role="assistant", content=content), finish_reason="stop"
        )])
        return JSONResponse(content=response.model_dump())

    async def generate_stream():
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
        yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
