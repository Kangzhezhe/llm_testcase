# LLM与Agent的MCP集成

本项目现在支持Model Context Protocol (MCP)，允许通过标准化协议与外部工具和服务进行交互。

## 安装依赖

```bash
# 安装MCP支持
pip install fastmcp
```

## 基本使用

### 1. 传统工具调用（无变化）

```python
from src.core.llm.llm import LLM
from src.core.llm.tool_call import LLMToolCaller

def add(a: float, b: float) -> float:
    return a + b

caller = LLMToolCaller([add])
llm = LLM()
result = llm.call("请计算 3 + 5", caller=caller)
```

### 2. MCP工具调用（新功能）

```python
from src.core.llm.llm import LLM, create_llm_with_mcp
from src.core.llm.mcp_client import MCPServerConfig, MCPTransportType

# 创建MCP配置
mcp_configs = [
    MCPServerConfig(
        name="demo",
        command="python",
        args=["-m", "src.core.llm.demo_mcp_server"],
        transport=MCPTransportType.STDIO
    )
]

# 创建支持MCP的LLM
llm = create_llm_with_mcp(mcp_configs, logger=True)

# 异步使用
async def main():
    await llm.init_mcp()
    result = llm.call("请计算 10 × 2", use_mcp=True)
    await llm.cleanup_mcp()

import asyncio
asyncio.run(main())
```

### 3. Agent的MCP支持

```python
from src.core.llm.agent import Agent, create_agent_with_mcp
from src.core.llm.mcp_client import MCPServerConfig, MCPTransportType

# 创建MCP配置
mcp_configs = [MCPServerConfig(...)]

# 创建支持MCP的Agent
agent = create_agent_with_mcp(mcp_configs, logger=True)

async def main():
    await agent.init_mcp()
    
    # 使用MCP工具
    result = agent.chat("请获取当前时间", use_mcp=True)
    print(result['final_response'])
    
    await agent.cleanup_mcp()

asyncio.run(main())
```

### 4. 混合使用

```python
# 同时支持传统工具和MCP工具
def subtract(a: float, b: float) -> float:
    return a - b

agent = Agent(mcp_configs=mcp_configs, logger=True)
agent.register_tools([subtract])

async def main():
    await agent.init_mcp()
    
    # 使用传统工具
    result1 = agent.chat("请计算 10 - 3", use_tools=True)
    
    # 使用MCP工具
    result2 = agent.chat("请获取当前时间", use_mcp=True)
    
    await agent.cleanup_mcp()
```

## MCP服务器配置

### 支持的传输类型

- **STDIO**: 通过标准输入输出与子进程通信
- **SSE**: 通过Server-Sent Events与HTTP服务器通信
- **WebSocket**: 通过WebSocket与服务器通信

```python
# STDIO配置
MCPServerConfig(
    name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"],
    transport=MCPTransportType.STDIO
)

# SSE配置
MCPServerConfig(
    name="web_service",
    url="http://localhost:8000/mcp",
    transport=MCPTransportType.SSE
)

# WebSocket配置
MCPServerConfig(
    name="ws_service",
    url="ws://localhost:8000/mcp",
    transport=MCPTransportType.WEBSOCKET
)
```

## 演示MCP服务器

项目包含一个演示MCP服务器 (`demo_mcp_server.py`)，提供以下工具：

- `calculate`: 基本数学运算
- `get_current_time`: 获取当前时间
- `echo_message`: 回声消息
- `get_weather`: 获取天气信息（模拟）

运行演示服务器：
```bash
python -m src.core.llm.demo_mcp_server
```

## 测试

运行测试脚本验证功能：

```bash
# 测试LLM的MCP集成
python test_mcp_integration.py

# 测试Agent的MCP功能
python test_agent_mcp.py
```

## 注意事项

1. **异步支持**: MCP功能需要异步环境，请使用 `asyncio.run()` 或在异步函数中调用
2. **资源管理**: 记得在使用完毕后调用 `cleanup_mcp()` 清理连接
3. **错误处理**: MCP连接可能失败，代码会自动回退到传统工具
4. **依赖检查**: 代码会自动检测 `fastmcp` 库是否可用

## 兼容性

- 完全向后兼容现有的传统工具调用
- 可以同时使用传统工具和MCP工具
- 现有代码无需修改即可继续使用

## 扩展

您可以轻松集成其他MCP服务器：

- 文件系统操作
- 数据库查询
- API调用
- Git操作
- 网络搜索
- 等等...

只需配置相应的 `MCPServerConfig` 即可！
