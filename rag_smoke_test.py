"""Offline smoke test for Taobao knowledge-base retrieval."""

from pathlib import Path

from rag.retriever import TfidfRetriever, load_chunks


chunks = load_chunks(Path(__file__).parent / "knowledge_base")
results = TfidfRetriever(chunks).search("淘宝退款多久到账", limit=1)
assert results, "检索结果为空"
assert "退款" in results[0].text or "退货" in results[0].text, results[0].text
print(f"RAG retrieval smoke test passed: {results[0].source}#{results[0].chunk_id}")
