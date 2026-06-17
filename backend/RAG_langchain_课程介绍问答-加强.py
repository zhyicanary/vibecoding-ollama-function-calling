# 1. 导入依赖库
# 包括：
# Markdown切分、向量检索、BM25检索、
# 混合检索、Cross-Encoder重排序、LLM
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from sentence_transformers import CrossEncoder


# 2. 读取 Markdown 文件，并按标题切分
# 按 # ## ### 切分章节，保留文档结构
with open(r"《智能应用系统设计》课程介绍.md", encoding="utf-8") as f:
    md_text = f.read()

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ],
    strip_headers=False
)

header_splits = header_splitter.split_text(md_text)
print(f"[调试] 按标题切分为 {len(header_splits)} 块")


# 3. 二次切分处理过长章节
# 控制 chunk 大小，方便检索
char_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "，", " ", ""]
)

splits = char_splitter.split_documents(header_splits)
print(f"[调试] 二次切分后共 {len(splits)} 个块")


# 4. 构建向量检索器（Vector Search）
# Question → Embedding → Chroma 向量检索
embeddings = OllamaEmbeddings(
    model="qwen3-embedding:4b",
    base_url="http://localhost:11434"
)

vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

vector_retriever = vectorstore.as_retriever(
    search_kwargs={"k": 6}
)


# 5. 构建 BM25 检索器
# Question → 关键词匹配 → BM25
bm25_retriever = BM25Retriever.from_documents(splits)
bm25_retriever.k = 6


# 6. 构建混合检索器（Hybrid Retrieval）
# Question → Vector Search + BM25 → EnsembleRetriever
ensemble_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.5, 0.5]
)


# 7. 加载 Cross-Encoder 重排序模型
# 用于对召回结果进行精排
reranker = CrossEncoder(
    "BAAI/bge-reranker-base"
)


# 8. 定义重排序函数
# Question → Candidate Docs → Rerank → Top4
def rerank_docs(question, docs, top_n=4):
    pairs = [
        [question, doc.page_content]
        for doc in docs
    ]

    scores = reranker.predict(pairs)

    scored_docs = list(zip(docs, scores))
    scored_docs.sort(
        key=lambda x: x[1],
        reverse=True
    )

    reranked_docs = [
        doc for doc, score in scored_docs[:top_n]
    ]

    print(f"\n[调试] 重排序后 Top {top_n}：")
    for i, (doc, score) in enumerate(scored_docs[:top_n]):
        print(
            f"  [{i+1}] "
            f"score={score:.4f} | "
            f"{doc.page_content[:80]}..."
        )

    return reranked_docs


# 9. 检索 + 重排序 + 格式化
# 完整流程：
# Question
# → Vector Search
# → BM25
# → EnsembleRetriever
# → CrossEncoder Rerank
# → Top4
def format_docs_with_debug(question):
    docs = ensemble_retriever.invoke(question)

    print(f"\n[调试] 初始召回 {len(docs)} 个文档：")
    for i, doc in enumerate(docs):
        print(
            f"  [{i+1}] "
            f"{doc.page_content[:80]}..."
        )

    docs = rerank_docs(
        question,
        docs,
        top_n=4
    )

    return "\n\n---\n\n".join(
        f"[来源：{doc.metadata}]\n{doc.page_content}"
        for doc in docs
    )


# 10. 构建 Prompt 模板
# 要求模型严格根据知识库回答
prompt = ChatPromptTemplate.from_template("""
你是一个课程信息助手。请严格根据下方【参考资料】回答用户问题。

规则：
- 只能使用【参考资料】中出现的信息
- 如果资料中没有明确答案，请回答"根据已有资料无法确认"
- 不要编造或推测任何数字、名称

【参考资料】
{context}

【用户问题】
{question}

【回答】
""")


# 11. 加载本地大模型（LLM）
# Top4 Context + Question → Answer
llm = ChatOllama(
    model="qwen3:8b",
    base_url="http://localhost:11434",
    temperature=0
)


# 12. 构建完整 RAG Chain
# 最终流程：
# Question
# → Vector Search
# → BM25
# → EnsembleRetriever
# → CrossEncoder Rerank
# → Top4
# → LLM
rag_chain = (
    {
        "context": RunnableLambda(format_docs_with_debug),
        "question": RunnablePassthrough()
    }
    | prompt
    | llm
    | StrOutputParser()
)


# 13. 启动交互式问答系统
print("\n========================================")
print("  课程知识库问答系统已就绪，输入 exit 退出")
print("========================================\n")

while True:
    question = input("你的问题：").strip()

    if not question:
        continue

    if question.lower() == "exit":
        print("已退出，再见！")
        break

    answer = rag_chain.invoke(question)

    print(f"\n回答：{answer}\n")
    print("-" * 40)