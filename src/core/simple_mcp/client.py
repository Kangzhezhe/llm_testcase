"""
简化版MCP客户端实现
用于连接和调用简化版MCP服务器的功能
基于JSON-RPC协议
"""
import asyncio
import json
import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPRequest:
    """MCP请求数据模型"""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = ""
    params: Optional[Dict[str, Any]] = None

class SimpleMCPClient:
    """简化版MCP客户端，用于与简化版MCP服务器交互"""
    
    def __init__(self, server_command: Optional[List[str]] = None):
        self.server_command = server_command or ["python", "-m", "src.core.mcp.server"]
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._resources = []
        self._tools = []
        self._prompts = []
        self.initialized = False
    
    async def connect(self):
        """连接到MCP服务器"""
        try:
            # 启动服务器进程
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )
            
            # 等待一下让服务器启动，并读取初始化输出
            await asyncio.sleep(1.0)
            
            # 检查进程是否正常运行
            if self.process.poll() is not None:
                # 进程已经退出，读取错误信息
                stderr = self.process.stderr.read()
                raise RuntimeError(f"Server process exited with code {self.process.returncode}: {stderr}")
            
            # 初始化连接
            await self._initialize()
            
            # 获取服务器能力
            await self._refresh_capabilities()
            
            logger.info("Successfully connected to MCP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """断开与服务器的连接"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("Disconnected from MCP server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                try:
                    self.process.kill()
                except:
                    pass
            finally:
                self.process = None
        self.initialized = False
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """发送请求到服务器"""
        if not self.process:
            raise RuntimeError("Not connected to server")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            # 发送请求
            request_line = json.dumps(request, ensure_ascii=False) + "\n"
            logger.debug(f"Sending request: {request_line.strip()}")
            
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
            
            # 读取响应，跳过非JSON行
            max_attempts = 10
            for attempt in range(max_attempts):
                response_line = self.process.stdout.readline()
                logger.debug(f"Received line {attempt + 1}: {response_line.strip()}")
                
                if not response_line:
                    raise RuntimeError("Server closed connection")
                
                # 检查是否是有效的JSON
                response_line = response_line.strip()
                if not response_line:
                    continue  # 跳过空行
                
                # 尝试解析JSON
                try:
                    response = json.loads(response_line)
                    # 检查是否是对我们请求的响应
                    if isinstance(response, dict) and response.get("id") == self.request_id:
                        if "error" in response:
                            raise RuntimeError(f"Server error: {response['error']}")
                        return response.get("result")
                    elif isinstance(response, dict) and "jsonrpc" in response:
                        # 这是一个JSON-RPC响应，但可能是通知或其他消息
                        logger.debug(f"Received JSON-RPC message: {response}")
                        continue
                except json.JSONDecodeError:
                    # 不是JSON，可能是服务器的状态信息，跳过
                    logger.debug(f"Skipping non-JSON line: {response_line}")
                    continue
            
            # 如果所有尝试都失败了
            raise RuntimeError(f"Failed to get valid JSON response after {max_attempts} attempts")
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def _initialize(self):
        """初始化连接"""
        try:
            result = await self._send_request("initialize", {
                "clientName": "simple-mcp-client",
                "clientVersion": "1.0.0"
            })
            self.initialized = True
            logger.info(f"Initialized with server: {result}")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    async def _refresh_capabilities(self):
        """刷新服务器能力信息"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
        
        try:
            # 获取资源列表
            resources_result = await self._send_request("resources/list")
            self._resources = resources_result.get("resources", [])
            
            # 获取工具列表
            tools_result = await self._send_request("tools/list")
            self._tools = tools_result.get("tools", [])
            
            # 获取提示列表
            try:
                prompts_result = await self._send_request("prompts/list")
                self._prompts = prompts_result.get("prompts", [])
            except Exception:
                self._prompts = []  # 某些服务器可能不支持prompts
                
        except Exception as e:
            logger.error(f"Failed to refresh capabilities: {e}")
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """列出可用资源"""
        await self._refresh_capabilities()
        return self._resources
    
    async def read_resource(self, uri: str) -> str:
        """读取资源内容"""
        try:
            result = await self._send_request("resources/read", {"uri": uri})
            contents = result.get("contents", [])
            return contents[0].get("text", "") if contents else ""
        except Exception as e:
            logger.error(f"Failed to read resource {uri}: {e}")
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具"""
        await self._refresh_capabilities()
        return self._tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        try:
            result = await self._send_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
            content = result.get("content", [])
            return content[0].get("text", "") if content else None
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}")
            raise
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """列出可用提示"""
        await self._refresh_capabilities()
        return self._prompts
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """获取并执行提示"""
        try:
            result = await self._send_request("prompts/get", {
                "name": name,
                "arguments": arguments
            })
            messages = result.get("messages", [])
            return messages[0].get("content", {}).get("text", "") if messages else ""
        except Exception as e:
            logger.error(f"Failed to get prompt {name}: {e}")
            raise
    
    # 便捷方法
    async def chat(self, query: str, use_rag: bool = False, knowledge_base: str = "rag_demo") -> str:
        """简单聊天接口"""
        return await self.get_prompt("llm_chat", {
            "query": query,
            "use_rag": use_rag,
            "knowledge_base": knowledge_base
        })
    
    async def chat_with_tools(self, query: str, allowed_tools: List[str], use_rag: bool = False, knowledge_base: str = "rag_demo") -> str:
        """带工具调用的聊天接口"""
        return await self.get_prompt("llm_chat_with_tools", {
            "query": query,
            "allowed_tools": allowed_tools,
            "use_rag": use_rag,
            "knowledge_base": knowledge_base
        })
    
    async def structured_chat(self, query: str, template: str) -> str:
        """结构化输出聊天接口"""
        return await self.get_prompt("structured_output", {
            "query": query,
            "template": template
        })
    
    async def search_knowledge(self, query: str, top_k: int = 5, collection_name: str = "rag_demo") -> List[Dict]:
        """搜索知识库"""
        result = await self.call_tool("search_knowledge", {
            "query": query,
            "top_k": top_k,
            "collection_name": collection_name
        })
        try:
            return json.loads(result) if isinstance(result, str) else result
        except:
            return []
    
    async def add_numbers(self, a: float, b: float) -> float:
        """计算两个数字的和"""
        result = await self.call_tool("add", {"a": a, "b": b})
        try:
            return float(result) if isinstance(result, str) else result
        except:
            return 0.0
    
    async def multiply_numbers(self, a: float, b: float) -> float:
        """计算两个数字的积"""
        result = await self.call_tool("multiply", {"a": a, "b": b})
        try:
            return float(result) if isinstance(result, str) else result
        except:
            return 0.0

class SimpleMCPClientManager:
    """简化版MCP客户端管理器，提供更高级的接口"""
    
    def __init__(self, server_command: Optional[List[str]] = None):
        self.client = SimpleMCPClient(server_command)
        self.connected = False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.connected = await self.client.connect()
        if not self.connected:
            raise RuntimeError("Failed to connect to MCP server")
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.client.disconnect()
        self.connected = False

# 使用示例和测试函数
async def demo_simple_mcp_client():
    """简化版MCP客户端演示"""
    async with SimpleMCPClientManager() as client:
        print("=== 简化版MCP客户端演示 ===\n")
        
        # 1. 列出可用资源
        print("1. 可用资源:")
        try:
            resources = await client.list_resources()
            for resource in resources:
                print(f"  - {resource.get('name', 'Unknown')}: {resource.get('uri', 'N/A')}")
        except Exception as e:
            print(f"  资源列表获取失败: {e}")
        print()
        
        # 2. 列出可用工具
        print("2. 可用工具:")
        try:
            tools = await client.list_tools()
            for tool in tools:
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'N/A')}")
        except Exception as e:
            print(f"  工具列表获取失败: {e}")
        print()
        
        # 3. 测试工具调用
        print("3. 工具调用测试:")
        try:
            # 测试加法
            result = await client.add_numbers(3.5, 2.5)
            print(f"  加法 3.5 + 2.5 = {result}")
            
            # 测试乘法
            result = await client.multiply_numbers(4, 6)
            print(f"  乘法 4 × 6 = {result}")
            
            # 测试回声
            result = await client.call_tool("echo", {"text": "Hello Simple MCP!"})
            print(f"  回声: {result}")
            
        except Exception as e:
            print(f"  工具调用错误: {e}")
        print()
        
        # 4. 测试聊天
        print("4. 聊天测试:")
        try:
            response = await client.chat("你好，请简单介绍一下你自己")
            print(f"  普通聊天: {response}")
            
            # 测试知识库搜索（如果有的话）
            try:
                kb_result = await client.search_knowledge("用户手册", top_k=3)
                print(f"  知识库搜索结果: {len(kb_result) if kb_result else 0} 条")
            except Exception:
                print("  知识库搜索不可用")
                
        except Exception as e:
            print(f"  聊天错误: {e}")
        print()
        
        # 5. 测试结构化输出
        print("5. 结构化输出测试:")
        try:
            template = "姓名={name:str}，年龄={age:int}，职业={job:str}"
            response = await client.structured_chat("请输出一个示例用户信息", template)
            print(f"  结构化输出: {response}")
        except Exception as e:
            print(f"  结构化输出错误: {e}")

# 兼容性别名
MCPLLMClient = SimpleMCPClient
MCPClientManager = SimpleMCPClientManager
demo_mcp_client = demo_simple_mcp_client

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_simple_mcp_client())
