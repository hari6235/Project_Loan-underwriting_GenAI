import os
from numpy import rint
import yaml

from dotenv import load_dotenv
from openai import OpenAI

import json

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def load_prompts():

    with open(
        "prompts/system_prompt.yaml",
        "r"
    ) as file:

        system_prompt = yaml.safe_load(file)

    with open(
        "prompts/few_shots.yaml",
        "r"
    ) as file:

        few_shots = yaml.safe_load(file)

    return system_prompt, few_shots


def ask_llm(query: str):

    system_prompt, few_shots = load_prompts()

    messages = []

    messages.append(
        {
            "role": "system",
            "content":
                system_prompt["role"]
                + "\n"
                + system_prompt["instructions"]
        }
    )

    for example in few_shots["examples"]:

        messages.append(
            {
                "role": "user",
                "content": example["user"]
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(example["assistant"])
            }
        )

    messages.append(
        {
            "role": "user",
            "content": query
        }
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2
    )

    content = response.choices[0].message.content
    print("\nLLM RESPONSE:")
    print(content)
    print("\n")
    return content
