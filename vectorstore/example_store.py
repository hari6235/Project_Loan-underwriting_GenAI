import os
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

examples = [
    {"question": "What is EMI?", "answer": "EMI is monthly installment of loan repayment."},
    {"question": "What is credit score?", "answer": "Credit score reflects creditworthiness."},
    {"question": "What documents are required for loan?", "answer": "PAN, Aadhaar, income proof are required."}
]

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