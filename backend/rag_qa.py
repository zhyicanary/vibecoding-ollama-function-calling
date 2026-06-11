from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import CrossEncoder

try:
    from langchain.retrievers import EnsembleRetriever
except ImportError:  # pragma: no cover - fallback for older versions
    # Lightweight fallback to avoid hard dependency on EnsembleRetriever.
    class EnsembleRetriever:
        def __init__(self, retrievers, weights=None):
            if not retrievers:
                raise ValueError("retrievers 不能为空")
            self.retrievers = retrievers
            if weights is None:
                weights = [1.0 / len(retrievers)] * len(retrievers)
            if len(weights) != len(retrievers):
                raise ValueError("weights 数量必须与 retrievers 一致")
            self.weights = weights

        def _get_docs(self, retriever, question):
            if hasattr(retriever, "invoke"):
                return retriever.invoke(question)
            return retriever.get_relevant_documents(question)

        def get_relevant_documents(self, question):
            scored = {}
            doc_lookup = {}
            for weight, retriever in zip(self.weights, self.retrievers):
                docs = self._get_docs(retriever, question)
                for rank, doc in enumerate(docs):
                    key = (doc.page_content, tuple(sorted(doc.metadata.items())))
                    score = weight / (rank + 1)
                    scored[key] = scored.get(key, 0.0) + score
                    doc_lookup[key] = doc
            ranked = sorted(scored.items(), key=lambda item: item[1], reverse=True)
            return [doc_lookup[key] for key, _ in ranked]

        def invoke(self, question):
            return self.get_relevant_documents(question)

PDF_PATH = "\u8f6f\u4ef6\u4e0e\u4eba\u5de5\u667a\u80fd\u5b66\u9662\u672c\u79d1\u751f\u5b66\u4e1a\u9884\u8b66\u5b9e\u65bd\u529e\u6cd5.pdf"
PERSIST_DIR = "./chroma_academic_warning"

EMBED_MODEL = "qwen3-embedding:4b"
CHAT_MODEL = "qwen3:8b"
RERANK_MODEL = "BAAI/bge-reranker-base"
OLLAMA_URL = "http://localhost:11434"

VECTOR_K = 6
BM25_K = 6
RERANK_TOP_K = 4


def load_documents(pdf_path: str):
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"未找到 PDF 文件: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    return loader.load()


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", "\u3002", "\uff0c", " ", ""],
    )
    return splitter.split_documents(documents)


def build_vector_retriever(documents):
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )
    return vectorstore.as_retriever(search_kwargs={"k": VECTOR_K})


def build_bm25_retriever(documents):
    retriever = BM25Retriever.from_documents(documents)
    retriever.k = BM25_K
    return retriever


def rerank(question: str, docs, top_k: int, reranker: CrossEncoder):
    # Cross-Encoder 评分用于更精确的重排序。
    pairs = [[question, doc.page_content] for doc in docs]
    scores = reranker.predict(pairs)
    scored = sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)
    return [doc for doc, _ in scored[:top_k]]


def build_rag_chain(ensemble_retriever, reranker: CrossEncoder):
    prompt = ChatPromptTemplate.from_template(
        """
你是学业预警制度助手。请严格根据【参考资料】作答。

规则：
- 只能使用【参考资料】中明确出现的信息。
- 若资料中没有答案，请回复：“根据已有资料无法确认”。
- 不要编造或推测任何名称、数字或流程。

【参考资料】
{context}

【用户问题】
{question}

【回答】
"""
    )

    llm = ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_URL, temperature=0)

    def build_context(question: str):
        try:
            docs = ensemble_retriever.invoke(question)
        except AttributeError:
            docs = ensemble_retriever.get_relevant_documents(question)
        docs = rerank(question, docs, top_k=RERANK_TOP_K, reranker=reranker)
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    return (
        {"context": RunnableLambda(build_context), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def main():
    documents = load_documents(PDF_PATH)
    chunks = split_documents(documents)

    vector_retriever = build_vector_retriever(chunks)
    bm25_retriever = build_bm25_retriever(chunks)

    ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )

    reranker = CrossEncoder(RERANK_MODEL)
    rag_chain = build_rag_chain(ensemble_retriever, reranker)

    print("学业预警问答系统已就绪，输入 exit 或 退出 结束。")
    while True:
        question = input("你的问题：").strip()
        if not question:
            continue
        if question.lower() == "exit" or question == "退出":
            print("已退出，再见！")
            break
        answer = rag_chain.invoke(question)
        print(f"\n回答：{answer}\n")
        print("-" * 40)


if __name__ == "__main__":
    main()
