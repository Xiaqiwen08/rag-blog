import os
from dotenv import load_dotenv
load_dotenv()
import pymysql
import chromadb
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_chroma import Chroma
from langchain_core.documents import Document
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter

prompt = ChatPromptTemplate.from_template("""
    你是我的AI助手。请根据下面的【资料】回答用户的问题。
    如果资料里没有答案，就老实说"资料里没有提到"。

    【资料】
    {context}

    【问题】
    {question}
""")

embeddings = OllamaEmbeddings(model="nomic-embed-text")
llm = ChatOllama(model="deepseek-r1:8b")
vectorstore = None
try:
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings,
        collection_name="blog_posts"
    )
    print("✅ 已自动加载已有向量库")
except Exception:
    print("⚠️ 向量库为空，请先调用 /ai-init 初始化")

# ChromaDB 客户端
chroma_client = chromadb.PersistentClient(path="./chroma_db")
blog_collection = chroma_client.get_or_create_collection(name="blog_posts")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 连接数据库（cards.db 文件会自动创建）
def get_db():
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),   # 从.env读！读不到就是空
        database=os.getenv("DB_NAME", "wen_blog"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

# ========== 数据模型 ==========
class Card(BaseModel):
    title:str
    date: str = ""
    desc:str

class Question(BaseModel):
    question:str

# ========== GET ==========
@app.get("/")
def hello():
    return {"message": "Hello~"}

@app.get("/greet/{name}")
def greet(name: str):
    return {"greeting": f"Hello {name}!"}

@app.get("/ping")
def ping():
    return {"status":"ok"}

@app.get("/cards")
def get_cards():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    # 把 Row 对象转成 dict 列表
    cards = [dict(row) for row in rows]
    return {"cards":cards}

# ========== POST ==========
@app.post("/cards")             # POST 请求
def add_card(card:Card):        # card 自动从请求体 JSON 解析
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cards (title, date, `desc`) VALUES (%s, %s, %s)",
        (card.title,card.date,card.desc)
    )
    conn.commit()
    conn.close()
    return {"message":f"新增成功:{card.title}"}

# ========== DELETE ==========
@app.delete("/cards/{index}")                       # {index} 是路径参数
def delete_card(index:int):                 # Python 自动把字符串转成整数
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cards ORDER BY id")
    rows = cursor.fetchall()
    if index < 0 or index >=len(rows):
        conn.close()
        return {"error":""}
    card_id = rows[index]["id"]
    cursor.execute("DELETE FROM cards WHERE id = %s",(card_id,))
    conn.commit()
    conn.close()
    return{"message":"已删除"}

# ========== PUT ==========
@app.put("/cards/{index}")
def update_card(index: int,card :Card):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cards ORDER BY id")
    rows = cursor.fetchall()
    if index < 0 or index >= len(rows):
        conn.close()
        return {"error":"索引不存在"}
    card_id = rows[index]["id"]
    cursor.execute(
        "UPDATE cards SET title = %s, date = %s, `desc` = %s WHERE id = %s",
        (card.title, card.date, card.desc, card_id)
    )
    conn.commit()
    conn.close()
    return {"message":f"已更新：{card.title}"}

# ========== AI 搜索 ==========
@app.post("/ai-search")
def ai_search(q:Question):
    results = blog_collection.query(
        query_texts=[q.question],       # ④ 搜这个问题
        n_results=3                     # ⑤ 要前3条最匹配的
    )
    item = []
    for doc,dist in zip(results["documents"][0],results["distances"][0]):
        item.append({"content":doc,"distance":round(dist,4)})
    return{"results":item}

# ========== AI 初始化：批量向量化 ==========
@app.post("/ai-init")
def ai_init():
    # ① 先删掉旧的集合！（384维的旧货架）
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    try:
        chroma_client.delete_collection(name="blog_posts")
        print("已删除旧集合")
    except Exception:
        pass   # 没有旧集合也不报错

    conn = get_db();
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, `desc` FROM cards ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

     # ① 每条卡片 → 一个Document（昨天学的！）
    docs = []
    for row in rows:
        docs.append(Document(
            page_content=f"{row['title']}——{row['desc']}",
            metadata={"id": row["id"], "title": row["title"]}
        ))

    # ② 切分（你的文本短，chunk可以大点）
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    # ③ 入库（统一用langchain_chroma + nomic嵌入！）
    global vectorstore
    vectorstore = Chroma.from_documents(
        chunks, embeddings,
        persist_directory="./chroma_db",
        collection_name="blog_posts"
    )
    return {"message": f"已向量化 {len(rows)} 篇，切成 {len(chunks)} 块"}

# ========== RAG 问答 ==========
@app.post("/rag")
def rag(q:Question):
    if vectorstore is None:
        return {"answer": "向量库还没初始化，请先调用 /ai-init 哦~"}
    retriever = vectorstore.as_retriever(search_kwargs={"k":3})
    rag_chain = (
        {"context": retriever, "question":RunnablePassthrough()}
        | prompt
        | llm
    )
    answer = rag_chain.invoke(q.question)
    return {"answer":answer.content}