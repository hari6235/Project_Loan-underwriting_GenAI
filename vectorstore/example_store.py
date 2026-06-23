import os
import yaml

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# -------------------------
# LOAD EXAMPLES FROM few_shots.yaml
# -------------------------
_yaml_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "few_shots.yaml")

with open(_yaml_path, "r") as f:
    _data = yaml.safe_load(f)

examples = [
    {
        "question": ex["user"],
        "answer": str(ex["assistant"])
    }
    for ex in _data["examples"]
]

# -------------------------
# BUILD FAISS VECTORSTORE
# -------------------------
texts = [e["question"] for e in examples]
metadatas = [{"answer": e["answer"]} for e in examples]

vectorstore = FAISS.from_texts(
    texts=texts,
    embedding=OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY")
    ),
    metadatas=metadatas
)


def search_examples(query: str):
    docs = vectorstore.similarity_search(query, k=1)

    if docs:
        return docs[0].metadata["answer"]

    return None