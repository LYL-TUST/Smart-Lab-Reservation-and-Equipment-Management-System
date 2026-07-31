"""
MCP Client — 通过 MCP 协议发现并调用工具

将原本的 `import src.rules_engine` / `import src.diff_parser`
替换为通过 MCP 协议发现和调用工具。

设计原则:
- 每个 MCP Server 以子进程方式启动，通过 stdio 通信
- 工具在运行时发现（list_tools），而非编译时绑定
- 同时保留直接 import 模式，两种模式通过 `--mcp` 开关选择

使用方式:
    async with McpToolClient() as client:
        tools = await client.list_all_tools()
        result = await client.call("filter_code_review_issues", {...})
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional

logger = logging.getLogger(__name__)

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 可用的 MCP Server 定义
MCP_SERVERS = {
    "rules_engine": {
        "module": "mcp_servers.rules_engine_server",
        "description": "规则引擎 — 基于特征签名的 LLM 审查结果过滤",
    },
    "diff_parser": {
        "module": "mcp_servers.diff_parser_server",
        "description": "Diff 解析器 — Git diff → 结构化变更数据",
    },
    "ast_context": {
        "module": "mcp_servers.ast_context_server",
        "description": "AST 上下文压缩 — 只提取变更函数定义，Token 降 57-98%",
    },
    "feedback_loop": {
        "module": "mcp_servers.feedback_loop_server",
        "description": "反馈飞轮 — 记录 Accept/Dismiss，自动生长规则",
    },
}


class McpServerConnection:
    """
    与单个 MCP Server 的连接。

    MCP 2.0 中 stdio_client 是 async context manager，
    它内部管理子进程和 I/O task group。
    Session 必须在此 context 内使用。

    因此 McpServerConnection 本身也是一个 async context manager，
    确保 stdio_client context 在连接整个生命周期内保持活动。
    """

    def __init__(self, name: str, server_def: dict):
        self.name = name
        self.server_def = server_def
        self._stdio_ctx = None
        self._session = None
        self._tools: list[dict] = []

    async def __aenter__(self):
        """进入 context：连接 MCP Server 并初始化 session。"""
        server_module = self.server_def["module"]

        from mcp.client.stdio import stdio_client, StdioServerParameters

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", server_module],
            cwd=str(_PROJECT_ROOT),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        # 进入 stdio_client context（启动子进程和 I/O task group）
        self._stdio_ctx = stdio_client(server_params)
        read_stream, write_stream = await self._stdio_ctx.__aenter__()

        # 在 context 内建立 session
        from mcp.client.session import ClientSession
        self._session = ClientSession(read_stream, write_stream)
        await self._session.initialize()

        # 发现工具列表
        tools_result = await self._session.list_tools()
        self._tools = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in tools_result.tools
        ]

        logger.info(
            "MCP [%s] 已连接: 发现 %d 个工具 (%s)",
            self.name,
            len(self._tools),
            ", ".join(t["name"] for t in self._tools),
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出 context：关闭 session 和 stdio 通道。"""
        self._session = None
        self._tools = []
        if self._stdio_ctx:
            await self._stdio_ctx.__aexit__(exc_type, exc_val, exc_tb)
            self._stdio_ctx = None

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        调用 MCP Server 上的工具。

        必须在 async with 块内调用。
        """
        if not self._session:
            raise RuntimeError(f"MCP Server [{self.name}] 未连接")

        known_tools = [t["name"] for t in self._tools]
        if tool_name not in known_tools:
            raise ValueError(
                f"MCP Server [{self.name}] 没有工具 '{tool_name}'。"
                f"可用工具: {known_tools}"
            )

        logger.debug("MCP [%s] 调用 %s(%s)", self.name, tool_name, list(arguments.keys()))

        result = await self._session.call_tool(tool_name, arguments)

        if result.content:
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_output": text}

        return {}

    def list_tools(self) -> list[dict]:
        """返回已发现的工具列表。"""
        return self._tools


class McpToolClient:
    """
    MCP 多工具客户端 — 管理多个 MCP Server 的连接。

    使用 AsyncExitStack 确保所有 async context manager
    在同一个 task scope 内正确进入和退出。

    用法:
        async with McpToolClient(servers=["rules_engine", "diff_parser"]) as client:
            tools = client.list_all_tools()
            result = await client.call("filter_code_review_issues", {...})
    """

    def __init__(self, servers: Optional[list[str]] = None):
        self._server_names = servers or list(MCP_SERVERS.keys())
        self._connections: dict[str, McpServerConnection] = {}
        self._tool_index: dict[str, str] = {}
        self._stack: Optional[AsyncExitStack] = None

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        for name in self._server_names:
            if name not in MCP_SERVERS:
                logger.warning("未知 MCP Server: %s，已跳过", name)
                continue
            conn = McpServerConnection(name, MCP_SERVERS[name])
            entered_conn = await self._stack.enter_async_context(conn)
            self._connections[name] = entered_conn
            for tool in entered_conn.list_tools():
                self._tool_index[tool["name"]] = name
        logger.info(
            "MCP 客户端已就绪: %d 个 Server, %d 个工具",
            len(self._connections), len(self._tool_index),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._connections.clear()
        self._tool_index.clear()
        if self._stack:
            await self._stack.aclose()
            self._stack = None

    def list_all_tools(self) -> list[dict]:
        """返回所有已发现工具的扁平列表。"""
        tools = []
        for conn in self._connections.values():
            for t in conn.list_tools():
                tools.append({**t, "server": conn.name})
        return tools

    async def call(self, tool_name: str, arguments: dict) -> dict:
        """调用指定工具。自动路由到正确的 MCP Server。"""
        server_name = self._tool_index.get(tool_name)
        if not server_name:
            available = list(self._tool_index.keys())
            raise ValueError(
                f"未找到工具 '{tool_name}'。可用工具: {available}"
            )
        conn = self._connections[server_name]
        return await conn.call_tool(tool_name, arguments)


def print_tool_registry(tools: list[dict]):
    """打印工具注册表（用于调试和演示）。"""
    print("\n" + "=" * 60)
    print("  MCP 工具注册表 (运行时发现)")
    print("=" * 60)
    for t in tools:
        server = t.get("server", "?")
        name = t["name"]
        desc = t.get("description", "")
        print(f"  [{server}] {name}")
        print(f"          {desc[:80]}")
    print("=" * 60 + "\n")


# ── Local Registry Client ──
# 不通过子进程，直接从 MCP Server 模块的 tool registry 发现和调用工具。
# 走的是和 McpToolClient 完全相同的抽象：discover → route → call，
# 只是 transport 层用本地函数调用替代了 stdio JSON-RPC。


class LocalRegistryClient:
    """
    本地 MCP 工具注册表客户端。

    不启动子进程，直接从已导入的 MCPServer 实例的 list_tools() 
    发现工具，通过 call_tool() 路由调用。

    API 与 McpToolClient 完全一致——只是 transport 不同。
    证明了 MCP 的核心设计：工具绑定由 transport 层决定，上层无感。
    """

    def __init__(self, servers: Optional[list[str]] = None):
        self._server_names = servers or list(MCP_SERVERS.keys())
        self._tool_index: dict[str, str] = {}
        self._tool_functions: dict[str, callable] = {}
        self._all_tools: list[dict] = []

    def discover(self):
        """从 MCP Server 模块的 tool registry 发现所有可用工具。"""
        import importlib
        import asyncio

        for name in self._server_names:
            if name not in MCP_SERVERS:
                continue

            module_path = MCP_SERVERS[name]["module"]
            try:
                module = importlib.import_module(module_path)
                server = module.server

                # 调用 MCPServer.list_tools() 获取注册的工具
                async def _get():
                    return await server.list_tools()
                tools = asyncio.run(_get())

                for tool in tools:
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": getattr(tool, 'input_schema', None) or {},
                        "server": name,
                    }
                    self._all_tools.append(tool_info)
                    self._tool_index[tool.name] = name

                    # 找到对应的工具函数（从模块中）
                    fn = getattr(module, tool.name, None)
                    if fn:
                        self._tool_functions[tool.name] = fn

                logger.info("MCP [%s] 发现 %d 个工具", name, len(tools))

            except Exception as e:
                logger.warning("MCP [%s] 工具发现失败: %s", name, e)

        # 打印发现结果
        print_tool_registry(self._all_tools)

        print(f"  [MCP] 共发现 {len(self._all_tools)} 个工具，来自 {len(self._tool_index)} 个 Server")
        print(f"  [MCP] 工具在运行时发现，而非编译时 import 绑定\n")

    def list_all_tools(self) -> list[dict]:
        return self._all_tools

    def call(self, tool_name: str, arguments: dict) -> dict:
        """
        通过 MCP 路由调用工具。

        实际的工具发现→路由→调用链路：
        1. 从 tool_index 查找 tool 所属的 server
        2. 从 tool_functions 获取注册的函数
        3. 调用并返回结果
        """
        import json as json_mod

        server_name = self._tool_index.get(tool_name)
        if not server_name:
            raise ValueError(f"未找到工具 '{tool_name}'")

        fn = self._tool_functions.get(tool_name)
        if not fn:
            raise ValueError(f"工具 '{tool_name}' 已发现但未注册可调用函数")

        print(f"  [MCP] 路由: {tool_name} → [{server_name}]")

        # 调用 MCP tool 函数
        try:
            result = fn(**arguments)
            # 结果可能是 JSON 字符串（MCP tool 的标准返回格式）
            if isinstance(result, str):
                return json_mod.loads(result)
            return result
        except Exception as e:
            raise RuntimeError(f"MCP 调用 {tool_name} 失败: {e}")


def create_mcp_client(use_local: bool = True):
    """
    工厂函数：创建 MCP 客户端。

    Args:
        use_local: True=本地注册表模式, False=子进程模式（不稳定）

    Returns:
        LocalRegistryClient 或 McpToolClient 实例
    """
    if use_local:
        client = LocalRegistryClient()
        client.discover()
        return client
    else:
        # 子进程模式（需要 async）
        import asyncio

        async def _create():
            client = McpToolClient()
            await client.__aenter__()
            return client

        return asyncio.run(_create())


# ── 同步包装器（用于非 async 场景） ──

def call_mcp_sync(tool_name: str, arguments: dict) -> dict:
    """
    以同步方式调用 MCP 工具。

    用于在 review_pipeline 等同步函数中集成 MCP 调用。
    """
    async def _call():
        async with McpToolClient() as client:
            return await client.call(tool_name, arguments)

    return asyncio.run(_call())


# ── CLI 入口: 列出所有可用工具 ──

async def _cli_list_tools():
    """CLI 演示: 发现所有工具并打印注册表。"""
    print("正在启动 MCP Servers 并发现工具...\n")
    async with McpToolClient() as client:
        tools = client.list_all_tools()
        print_tool_registry(tools)

        # 演示调用
        if tools:
            print("运行演示: 调用规则引擎过滤测试数据...\n")
            test_issues = [
                {
                    "line": 10, "severity": "suggestion", "category": "style",
                    "title": "Consider renaming",
                    "description": "Consider renaming 'x' to something meaningful"
                },
                {
                    "line": 20, "severity": "critical", "category": "correctness",
                    "title": "Possible null pointer",
                    "description": "No null check before dereference"
                },
            ]
            result = await client.call("filter_code_review_issues", {
                "issues": test_issues,
                "file_path": "fastapi/app.py"
            })
            print(f"  过滤前: {len(test_issues)} 个问题")
            print(f"  过滤后: {len(result.get('passed', []))} 个通过")
            print(f"  被拦截: {result.get('filtered_count', 0)} 个")
            print(f"  触发规则: {result.get('applied_rules', [])}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(_cli_list_tools())
