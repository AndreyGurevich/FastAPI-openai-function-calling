import asyncio
import json

from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import RunStep, RunStepDelta
from typing_extensions import override

from utils.config import DONE_MESSAGE, OPENAI_API_KEY
from utils.custom_logger import logger


# Define a function to get the response stream from the OpenAI API
async def get_openai_response_stream(thread_id: str, loop):
    event_handler = CustomEventHandler(loop)
    logger.info(f'We are in get_openai_response_stream with thread_id: {thread_id}')

    def run_stream():
        with openai_client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=dummy_assistant.id,
                # instructions="DO NOT USE IT, it overrides settings of assistant, specified in gpt_helper.py",
                event_handler=event_handler,
        ) as stream:
            stream.until_done()

    loop.run_in_executor(None, run_stream)

    while True:
        chunk = await event_handler.queue.get()
        if chunk is None:
            yield DONE_MESSAGE
            break
        logger.debug(f'next chunk in get_openai_response_stream: {chunk}')
        yield chunk


class CustomEventHandler(AssistantEventHandler):
    def __init__(self, loop):
        super().__init__()
        self.queue = asyncio.Queue()
        self.loop = loop
        # self.current_run = None

    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == 'thread.run.requires_action':
            # run_id = event.data.id
            self.handle_requires_action(event.data)

    @override
    def on_text_created(self, text) -> None:
        asyncio.run_coroutine_threadsafe(self.queue.put("\nassistant > "), self.loop)

    @override
    def on_text_delta(self, delta, snapshot):
        asyncio.run_coroutine_threadsafe(self.queue.put(delta.value), self.loop)

    @override
    def on_end(self):
        print(f'--- the end --- {self.current_run.required_action}')
        if self.current_run.required_action is None:
            asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)

    @override
    def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        print('on_run_step_delta')
        print(delta)

    @override
    def on_run_step_done(self, run_step: RunStep) -> None:
        print('on_run_step_done')
        print(run_step)

    @override
    def on_message_created(self, message: Message) -> None:
        """Callback that is fired when a message is created"""
        print('on_message_created')
        print(message)

    @override
    def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        # Callback that is fired whenever a message delta is returned from the API
        asyncio.run_coroutine_threadsafe(self.queue.put(delta.content[0].text.value), self.loop)
        print('on_message_delta')
        print(delta)
        # print(snapshot)

    @override
    def on_tool_call_created(self, tool_call):
        function_name = tool_call.function.name
        arguments_str = tool_call.function.arguments

        # Parse arguments if they are in JSON format
        try:
            arguments = json.loads(arguments_str) if arguments_str else {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse arguments: {e}")
            arguments = {}

        # Log function name and arguments
        logger.info(f'on_tool_call_created {function_name} with arguments:')
        for arg_name, arg_value in arguments.items():
            logger.info(f'  {arg_name}: {arg_value}')

        asyncio.run_coroutine_threadsafe(self.queue.put(f"\nI guess it's a tool call > {tool_call.function.name}\n"),
                                         self.loop)

    def on_tool_call_delta(self, delta, snapshot):
        # logger.info(f'on_tool_call_delta {delta.function.name}')
        # Inadequate number of calls happens here
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                asyncio.run_coroutine_threadsafe(self.queue.put(delta.code_interpreter.input), self.loop)
            if delta.code_interpreter.outputs:
                asyncio.run_coroutine_threadsafe(self.queue.put("\noutput >"), self.loop)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        asyncio.run_coroutine_threadsafe(self.queue.put(f"{output.logs}"), self.loop)
        if delta.type == 'text':
            if delta.code_interpreter.input:
                asyncio.run_coroutine_threadsafe(self.queue.put(delta.code_interpreter.input), self.loop)
            if delta.code_interpreter.outputs:
                asyncio.run_coroutine_threadsafe(self.queue.put("\non_tool_call_delta output >"), self.loop)
                # for output in delta.code_interpreter.outputs:
                #     if output.type == "logs":
                #         asyncio.run_coroutine_threadsafe(self.queue.put(f"{output.logs}"), self.loop)
        pass

    def handle_requires_action(self, data):
        logger.info(f'handle_requires_action, data.run_id is {data.id}')
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            logger.info(f'for-loop {tool.function.name} with arguments {tool.function.arguments}')
            # tool_outputs.append({"tool_call_id": tool.id, "output": "Some default for testing purpose"})
            if tool.function.name == "get_current_temperature":
                tool_outputs.append({"tool_call_id": tool.id, "output": "57"})
            elif tool.function.name == "get_rain_probability":
                tool_outputs.append({"tool_call_id": tool.id, "output": "0.06"})
            elif tool.function.name == "create_item":
                tool_outputs.append({"tool_call_id": tool.id, "output": "Something happened"})
        logger.info(f'Tool_outputs are {tool_outputs}')
        # Submit all tool_outputs at the same time
        asyncio.run_coroutine_threadsafe(self.submit_tool_outputs(tool_outputs, data), self.loop)

        logger.info('Just a log after submit_tool_outputs call')

    async def submit_tool_outputs(self, tool_outputs, data):
        logger.info(f'submit_tool_outputs {tool_outputs}, thread_id {data.thread_id}, run_id {data.id}')
        with openai_client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=data.thread_id,
                run_id=data.id,
                tool_outputs=tool_outputs,
                event_handler=CustomEventHandler(self.loop),
        ) as stream:
            for text in stream.text_deltas:
                logger.info(f"Stream text delta: {text}")
                asyncio.run_coroutine_threadsafe(self.queue.put(f"{text}"), self.loop)
                print(text, end="", flush=True)
            print()
        logger.info("submit_tool_outputs_stream call passed")
        await self.queue.put("Some strange output")
        async for chunk in get_openai_response_stream(data.thread_id, self.loop):
            logger.info(f"async chunk: {chunk}")
            # await self.queue.put(chunk)
            asyncio.run_coroutine_threadsafe(self.queue.put(f"{chunk}"), self.loop)


openai_client = OpenAI()
openai_client.api_key = OPENAI_API_KEY

# tools from https://platform.openai.com/docs/assistants/tools/function-calling/quickstart
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_temperature",
            "description": "Get the current temperature for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["Celsius", "Fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the user's location."
                    }
                },
                "required": ["location", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rain_probability",
            "description": "Get the probability of rain for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

dummy_assistant = openai_client.beta.assistants.create(
    name="Weather forecast assistant",
    instructions="You are a weather bot. Use the provided functions to answer questions.",
    tools=tools,
    model="gpt-4o",
)
