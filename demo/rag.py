import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from read_file import read_file, smart_split
from ENV import deep_seek_url, deep_seek_api_key, deep_seek_default_model

# 1. 初始化 DashScope embedding 客户端
client = OpenAI(
    api_key=deep_seek_api_key,
    base_url=deep_seek_url
)

def get_embedding(text):
    resp = client.embeddings.create(
        model="text-embedding-v4",
        input=text,
        dimensions=1024,
        encoding_format="float"
    )
    return resp.data[0].embedding

# 2. 构建知识库（Chroma本地向量库）
def build_chroma_knowledge_base(file_path, persist_dir="rag_chroma_db"):
    content = read_file(file_path)
    pieces = smart_split(content, max_len=1000)
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    collection = chroma_client.get_or_create_collection("rag_demo")
    # 清空旧数据（兼容新版chroma）
    all_ids = collection.get()['ids']
    if all_ids:
        collection.delete(ids=all_ids)
    # 插入新数据
    for idx, piece in enumerate(pieces):
        emb = get_embedding(piece)
        collection.add(
            embeddings=[emb],
            documents=[piece],
            ids=[f"doc_{idx}"]
        )
        print(f"分块{idx+1} 已入库")
    print(f"共入库 {len(pieces)} 块")
    return collection

# 3. 检索相关内容
def search_knowledge_base(query, collection, top_k=5):
    query_emb = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )
    docs = results["documents"][0]
    return docs

# 4. LLM问答（以LangChain OpenAI兼容接口为例）
from langchain_openai import ChatOpenAI

def rag_qa(query, docs):
    llm = ChatOpenAI(
        base_url=deep_seek_url,
        api_key=deep_seek_api_key,
        model=deep_seek_default_model,
        temperature=0.2
    )
    context = "\n\n".join(docs)
    prompt = f"""你是知识库问答助手。请根据以下知识内容回答用户问题。\n\n知识内容：\n{context}\n\n用户问题：{query}\n\n请用中文简明回答："""
    return llm.invoke(prompt)

# 5. 主流程
def main():
    file_path = "D:\\testcase\\aitestcases\\data\\需求文件\\需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx"  # 替换为你的文档
    # 第一次运行需构建知识库
    collection = build_chroma_knowledge_base(file_path)
    while True:
        query = input("请输入你的问题（exit退出）：").strip()
        if query.lower() == "exit":
            break
        docs = search_knowledge_base(query, collection)
        print("\n【检索到的知识块】")
        for i, doc in enumerate(docs):
            print(f"Top{i+1}:\n{doc}\n------")
        answer = rag_qa(query, docs)
        print("\n【RAG答案】\n", answer)

if __name__ == "__main__":
    main()