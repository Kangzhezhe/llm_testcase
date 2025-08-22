# MCP (Model Context Protocol) 集成

本项目已集成了完整的MCP (Model Context Protocol) 服务器和客户端实现，基于现有的LLM框架提供强大的模型上下文协议支持。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动MCP服务器

```bash
# 创建默认配置
python scripts/start_mcp_server.py --create-config

# 启动服务器
python scripts/start_mcp_server.py
```

### 3. 测试客户端

```bash
# 基础测试
python scripts/test_mcp_client.py --basic

# 完整演示
python scripts/test_mcp_client.py --demo

# 交互模式
python scripts/test_mcp_client.py --interactive
```

## 📋 功能特性

### 🔧 工具系统
- **数学运算**: 加法、减法、乘法、除法、幂运算
- **文本处理**: 回显、大小写转换、文本反转、单词统计
- **实用工具**: 当前时间、UUID生成、JSON格式化
- **知识库搜索**: 向量搜索和语义检索
- **自定义工具**: 支持动态注册自定义工具

### 🧠 LLM集成
- **普通对话**: 基于OpenAI API的对话功能
- **RAG问答**: 结合知识库的增强问答
- **结构化输出**: 基于模板的结构化解析
- **工具调用**: 自动工具调用和参数推断

### 📚 知识库管理
- **多文件支持**: Word、PDF、Markdown等多种格式
- **向量存储**: 基于ChromaDB的向量数据库
- **元数据过滤**: 支持正则表达式的元数据筛选
- **动态配置**: 运行时动态添加知识库

### ⚙️ 配置管理
- **JSON配置**: 简单易用的JSON配置文件
- **工具配置**: 灵活的工具启用/禁用配置
- **知识库配置**: 支持多知识库配置
- **自定义扩展**: 支持自定义工具和提示模板

## 🗂️ 项目结构

```
src/core/mcp/
├── __init__.py          # MCP模块入口
├── server.py            # MCP服务器实现
├── client.py            # MCP客户端实现
├── config.py            # 配置管理
├── cli.py               # 命令行工具
├── demo.py              # 完整演示
└── tests/
    └── test_mcp.py      # 单元测试

scripts/
├── start_mcp_server.py  # 服务器启动脚本
└── test_mcp_client.py   # 客户端测试脚本
```

## 🛠️ 使用指南

### 服务器配置

创建 `mcp_config.json` 配置文件：

```json
{
  "server": {
    "name": "llm-mcp-server",
    "version": "1.0.0",
    "host": "localhost",
    "port": 8000
  },
  "tools": {
    "enabled": ["add", "multiply", "echo", "search_knowledge"],
    "custom": {}
  },
  "knowledge_bases": {
    "demo_kb": {
      "file_list": [
        {"file_path": "data/example.txt", "type": "document"}
      ],
      "config": {
        "max_len": 1000,
        "overlap": 100
      }
    }
  }
}
```

### 启动服务器

```bash
# 使用默认配置
python scripts/start_mcp_server.py

# 使用自定义配置
python scripts/start_mcp_server.py --config my_config.json

# 指定端口和主机
python scripts/start_mcp_server.py --host 0.0.0.0 --port 9000

# 启用详细日志
python scripts/start_mcp_server.py --verbose
```

### 客户端使用

#### 编程方式

```python
from src.core.mcp import MCPClientManager

async def main():
    async with MCPClientManager() as client:
        # 普通聊天
        response = await client.chat("你好，MCP!")
        print(response)
        
        # 工具调用
        result = await client.add_numbers(10, 20)
        print(f"10 + 20 = {result}")
        
        # RAG问答
        response = await client.chat("什么是产品需求？", use_rag=True)
        print(response)
        
        # 结构化输出
        template = "姓名={name:str}，年龄={age:int}"
        response = await client.structured_chat("请输出用户信息", template)
        print(response)

import asyncio
asyncio.run(main())
```

#### 命令行方式

```bash
# 使用CLI工具
python -m src.core.mcp.cli client --interactive

# 或者使用测试脚本
python scripts/test_mcp_client.py --interactive
```

### 自定义工具

```python
from src.core.mcp import MCPConfig

# 1. 定义工具函数
def my_custom_tool(text: str, count: int = 1) -> str:
    """自定义工具示例"""
    return text * count

# 2. 注册到服务器
from src.core.mcp import MCPLLMServer
server = MCPLLMServer()
server.register_tool("repeat_text", my_custom_tool, "重复文本工具")

# 3. 或者通过配置文件注册
config = MCPConfig()
config.add_custom_tool(
    "repeat_text",
    "重复文本工具", 
    "my_module.tools",
    "my_custom_tool"
)
```

### 知识库管理

```python
from src.core.mcp import MCPConfig

config = MCPConfig()

# 添加知识库
file_list = [
    {"file_path": "data/manual.pdf", "type": "手册"},
    {"file_path": "data/faq.txt", "type": "FAQ"}
]

config.add_knowledge_base("support_kb", file_list, max_len=1500, overlap=150)
```

## 🎯 使用场景

### 1. 智能客服系统
```python
# RAG增强的客服机器人
async def customer_service_bot(question: str):
    async with MCPClientManager() as client:
        # 搜索相关文档
        docs = await client.search_knowledge(question, collection_name="support_kb")
        
        # RAG问答
        response = await client.chat(f"客户问题：{question}", use_rag=True)
        return response
```

### 2. 代码生成助手
```python
# 结构化代码生成
async def code_generator(requirement: str):
    template = "语言={language:str}，代码={code:str}，说明={description:str}"
    
    async with MCPClientManager() as client:
        result = await client.structured_chat(
            f"请为以下需求生成代码：{requirement}",
            template
        )
        return result
```

### 3. 数据分析工具
```python
# 自定义分析工具
def analyze_data(data: list, method: str = "mean") -> float:
    """数据分析工具"""
    if method == "mean":
        return sum(data) / len(data)
    elif method == "max":
        return max(data)
    elif method == "min":
        return min(data)
    return 0

# 注册并使用
server.register_tool("analyze", analyze_data, "数据分析工具")
```

## 🔍 故障排除

### 常见问题

1. **服务器启动失败**
   - 检查端口是否被占用
   - 确认LLM API配置正确
   - 查看详细日志：`--verbose`

2. **客户端连接失败**
   - 确认服务器正在运行
   - 检查主机和端口配置
   - 查看防火墙设置

3. **知识库构建失败**
   - 检查文件路径是否正确
   - 确认ChromaDB依赖已安装
   - 查看文件格式是否支持

4. **工具调用失败**
   - 检查工具参数类型
   - 确认工具已正确注册
   - 查看函数签名是否正确

### 调试方法

```bash
# 启用详细日志
python scripts/start_mcp_server.py --verbose

# 查看配置
python -m src.core.mcp.cli config show

# 运行测试
python -m pytest src/core/mcp/tests/test_mcp.py -v
```

## 📈 性能优化

### 服务器优化
- 使用连接池管理数据库连接
- 启用向量索引加速搜索
- 配置合适的块大小和重叠

### 客户端优化
- 复用连接减少开销
- 批量调用减少网络请求
- 使用异步操作提高并发

## 🔄 更新日志

### v1.0.0
- ✅ 完整的MCP协议实现
- ✅ 服务器和客户端支持
- ✅ 工具系统和知识库集成
- ✅ 配置管理和CLI工具
- ✅ 完整的测试套件

## 📄 许可证

本项目遵循原项目许可证。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进MCP功能！

---

**MCP集成让您的LLM应用更加强大和灵活！** 🎉
