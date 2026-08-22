import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = Path(__file__).resolve().parent / "mcp_server.py"


class ToolboxUnavailable(RuntimeError):
    pass


class Toolbox:
    def __init__(self, command=None, args=None):
        self._command = command or sys.executable
        self._args = args or [str(SERVER_SCRIPT)]
        self._stack = None
        self._session = None

    @property
    def connected(self):
        return self._session is not None

    async def start(self):
        if self.connected:
            return

        parameters = StdioServerParameters(
            command=self._command,
            args=self._args,
            cwd=str(SERVER_SCRIPT.parent),
            env=dict(os.environ),
        )

        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(stdio_client(parameters))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception:
            await stack.aclose()
            raise

        self._stack = stack
        self._session = session

    async def stop(self):
        if self._stack is None:
            return

        stack, self._stack, self._session = self._stack, None, None
        await stack.aclose()

    def _require_session(self):
        if self._session is None:
            raise ToolboxUnavailable("The appointment tool server is not running.")
        return self._session

    async def tool_specs(self):
        session = self._require_session()
        listed = await session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in listed.tools
        ]

    async def call(self, name, arguments):
        session = self._require_session()
        result = await session.call_tool(name, arguments)
        text = "".join(getattr(block, "text", "") for block in result.content)

        if result.isError:
            return f"The {name} tool failed: {text}"

        return text or "The tool returned no output."


toolbox = Toolbox()
