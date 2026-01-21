import argparse
import asyncio
import sys
import gradio as gr

from openai import AsyncOpenAI
from pathlib import Path
from pydantic import BaseModel

from usage import print_usage, format_usage_markdown

class Achievement(BaseModel):
    achievement_title: str
    achievement_message: str
    reward_tier: str


class ChatAgent:
    def __init__(self, model: str, prompt: str):
        self._ai = AsyncOpenAI()
        self.usage = []
        self.model = model
        self.reasoning = {'effort': 'low'}
        self._prompt = prompt
        self._history = []
        if prompt:
            self._history.append({'role': 'system', 'content': prompt})

    async def get_response(self, user_message: str):
        self._history.append({'role': 'user', 'content': user_message})

        response = await self._ai.responses.create(
            input=self._history,
            model=self.model,
            reasoning=self.reasoning
        )
        self.usage.append(response.usage)
        self._history.extend(
            response.output
        )
        return response.output_text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print_usage(self.model, self.usage)


async def _terminal_loop(agent: ChatAgent):
    while True:
        message = input("User: ")
        if not message:
            break
        response = await agent.get_response(message, None)
        print('Agent:', response)


def main(model: str):
    with open("sys_prompt.md", "r") as f:
        prompt = f.read()

    with ChatAgent(model, prompt) as agent:
        asyncio.run(_terminal_loop(agent))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument('character_file', type=str)
    parser.add_argument('--model', default='gpt-5-nano')
