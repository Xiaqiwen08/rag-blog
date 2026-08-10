import chromadb

# ① 创建客户端——数据存到本地 chroma_db 文件夹
client = chromadb.PersistentClient(path="./chroma_db")

# ② 创建/获取一个集合（类似 MySQL 里的一张表）
collection = client.get_or_create_collection(name="blog_posts")

# ③ 存入两条带向量的数据
collection.add(
    documents=[
        "Python FastAPI 是一个非常快、易于使用的后端框架",
        "数据结构中的链表是通过指针串联的内存块",
    ],
    ids=["post_1", "post_2"]
)

print("存入成功！共", collection.count(), "条")

# ④ 相似度搜索
results = collection.query(
    query_texts=["数据结构中的链表是通过指针串联的内存块"],
    n_results=2
)

print("\n搜索结果：")
for i,(doc,dist) in enumerate(zip(results["documents"][0],results["distances"][0])):
    print(f"{i+1}.{doc}  (距离: {dist:.4f})")