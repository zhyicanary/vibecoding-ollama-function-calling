import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from sentence_transformers import CrossEncoder
import streamlit as st
from langchain_ollama import OllamaEmbeddings,ChatOllama
# ================= 配置区 =================
BASE_DIR = os.path.dirname(__file__)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
PDF_PATH = os.environ.get(
    "RAG_PDF_PATH",
    os.path.join(BASE_DIR, "软件与人工智能学院本科生学业预警实施办法.pdf")
)
EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "qwen3-embedding:4b")
RERANKER_MODEL = os.environ.get("RAG_RERANKER_MODEL", "BAAI/bge-reranker-base")
LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "qwen3:8b")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K_RETRIEVE = 10      # 混合检索召回数量
TOP_K_RERANK = 3         # 重排序后保留数量
ENSEMBLE_WEIGHTS = [0.6, 0.4]  # [向量检索权重, BM25权重]

# ================= 1. 文档加载与切分 =================
def load_and_split_documents(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", " "]
    )
    return text_splitter.split_documents(documents)

# ================= 2. 构建混合检索器 =================
def build_ensemble_retriever(splits):
    # 向量检索
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K_RETRIEVE})
    
    # BM25关键词检索
    bm25_retriever = BM25Retriever.from_documents(splits)
    bm25_retriever.k = TOP_K_RETRIEVE
    
    # 混合检索
    ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=ENSEMBLE_WEIGHTS
    )
    return ensemble_retriever

# ================= 3. Cross-Encoder 重排序 =================
class RerankRetriever:
    def __init__(self, base_retriever, reranker_model, top_k):
        self.base_retriever = base_retriever
        self.reranker = CrossEncoder(reranker_model)
        self.top_k = top_k

    def invoke(self, query):
        docs = self.base_retriever.invoke(query)
        if not docs:
            return []
        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)
        ranked_docs = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in ranked_docs[:self.top_k]]

# ================= 4. Prompt模板（严格约束） =================
PROMPT_TEMPLATE = """你是广州软件学院软件与人工智能学院的学业预警咨询助手。
请【仅】根据以下参考资料回答学生问题，禁止使用任何外部知识或编造内容。
如果参考资料中没有相关信息，必须明确回复：“根据《本科生学业预警实施办法》，未找到相关说明。”

【参考资料】：
{context}

【学生问题】：
{question}

【回答要求】：
1. 准确引用预警级别、学分阈值及处理流程；
2. 涉及数字条款时必须与原文一致；
3. 语言简洁、官方、严谨。
"""

# ================= 5. Streamlit Web UI =================
def main():
    st.set_page_config(page_title="学业预警智能问答系统", page_icon="🎓")
    st.title("软件与人工智能学院学业预警问答系统")
    st.caption("基于《本科生学业预警实施办法》| 混合检索 + Cross-Encoder重排序 | Qwen3生成")

    # 初始化RAG链（缓存避免重复加载）
    @st.cache_resource
    def init_rag_chain():
        splits = load_and_split_documents(PDF_PATH)
        ensemble_retriever = build_ensemble_retriever(splits)
        rerank_retriever = RerankRetriever(ensemble_retriever, RERANKER_MODEL, TOP_K_RERANK)
        
        llm = ChatOllama(model=LLM_MODEL, temperature=0, base_url=OLLAMA_HOST)
        prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)
        
        rag_chain = (
            {"context": lambda x: "\n\n".join(doc.page_content for doc in rerank_retriever.invoke(x)),
             "question": RunnablePassthrough()}
            | prompt
            | llm
        )
        return rag_chain

    rag_chain = init_rag_chain()

    # 对话交互
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if question := st.chat_input("请输入学业预警相关问题..."):
        st.session_state.messages.append({"role": "user", "content": question})
        st.chat_message("user").write(question)
        
        with st.spinner("正在检索并重排序相关知识..."):
            response_placeholder = st.empty()
            full_answer = ""
            for chunk in rag_chain.stream(question):
                if hasattr(chunk, 'content'):
                    full_answer += chunk.content
                    response_placeholder.markdown(full_answer + "▌")
            response_placeholder.markdown(full_answer) 
        
        st.session_state.messages.append({"role": "assistant", "content": full_answer})    

        
if __name__ == "__main__":
    main()