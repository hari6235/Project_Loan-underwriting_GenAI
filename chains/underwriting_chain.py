import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from vectorstore.example_store import search_examples

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)


def underwriting_chain(user_input: str):

    example = search_examples(user_input)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a Senior Loan Underwriting Assistant. Return structured JSON only."),
        ("user",
         f"Example reference: {example}"),
        ("user",
         "{input}")
    ])

    chain = prompt | llm

    response = chain.invoke({"input": user_input})

    return response.content