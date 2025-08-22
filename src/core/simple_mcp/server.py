"""
简化版MCP服务器实现
基于现有LLM框架的Model Context Protocol服务
不依赖外部MCP库，使用JSON-RPC协议
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

from ..llm.llm import LLM
from ..llm.tool_call import LLMToolCaller, infer_param_model
from ..llm.template_parser.template_parser import TemplateParser
from ..llm.rag import search_knowledge_base, build_multi_file_knowledge_base

logger = logging.getLogger(__name__)

@dataclass
class Resource:
    """资源数据模型"""
    uri: str
    name: str
    description: str
    mimeType: str

@dataclass
class Tool:
    """工具数据模型"""
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class TextContent:
    """文本内容数据模型"""
    type: str = "text"
    text: str = ""

@dataclass
class MCPMessage:
    """MCP消息数据模型"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class SimpleMCPServer:
    """简化版MCP服务器"""
    
    def __init__(self, llm_instance: Optional[LLM] = None):
        self.llm = llm_instance or LLM()
        self.tools = {}
        self.resources = {}
        self.knowledge_bases = {}
        self.prompts = {}
        
        # 注册默认工具
        self._register_default_tools()
        self._register_default_prompts()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 基础计算工具
        def add(a: float, b: float) -> float:
            """加法运算"""
            return a + b
        
        def multiply(a: float, b: float) -> float:
            """乘法运算"""
            return a * b
        
        def echo(text: str) -> str:
            """回显文本"""
            return f"Echo: {text}"
        
        # 知识库搜索工具
        def search_knowledge(query: str, top_k: int = 5, collection_name: str = "rag_demo") -> List[Dict]:
            """搜索知识库"""
            try:
                return self.llm.search_knowledge(query, top_k=top_k, collection_name=collection_name)
            except Exception as e:
                logger.error(f"Knowledge search failed: {e}")
                return []
        
        # 注册工具
        self.tools.update({
            "add": {
                "func": add,
                "description": "执行两个数字的加法运算",
                "param_model": infer_param_model(add)
            },
            "multiply": {
                "func": multiply,
                "description": "执行两个数字的乘法运算",
                "param_model": infer_param_model(multiply)
            },
            "echo": {
                "func": echo,
                "description": "回显输入的文本",
                "param_model": infer_param_model(echo)
            },
            "search_knowledge": {
                "func": search_knowledge,
                "description": "在知识库中搜索相关内容",
                "param_model": infer_param_model(search_knowledge)
            }
        })
    
    def _register_default_prompts(self):
        """注册默认提示模板"""
        self.prompts = {
            "llm_chat": {
                "description": "General LLM chat with optional RAG",
                "arguments": [
                    {"name": "query", "description": "User query", "required": True},
                    {"name": "use_rag", "description": "Whether to use RAG", "required": False},
                    {"name": "knowledge_base", "description": "Knowledge base to search", "required": False}
                ]
            },
            "llm_chat_with_tools": {
                "description": "LLM chat with tool calling capability",
                "arguments": [
                    {"name": "query", "description": "User query", "required": True},
                    {"name": "allowed_tools", "description": "List of tools LLM can use", "required": True},
                    {"name": "use_rag", "description": "Whether to use RAG", "required": False},
                    {"name": "knowledge_base", "description": "Knowledge base to search", "required": False}
                ]
            },
            "structured_output": {
                "description": "LLM with structured output parsing",
                "arguments": [
                    {"name": "query", "description": "User query", "required": True},
                    {"name": "template", "description": "Output template", "required": True}
                ]
            }
        }
    
    def register_tool(self, name: str, func: callable, description: str = ""):
        """注册新工具"""
        self.tools[name] = {
            "func": func,
            "description": description or f"Tool: {name}",
            "param_model": infer_param_model(func)
        }
    
    def register_knowledge_base(self, name: str, file_list: List[Dict], **kwargs):
        """注册知识库"""
        try:
            # 如果有LLM，使用LLM构建知识库
            if self.llm:
                collection = self.llm.build_knowledge_base(file_list, collection_name=name, **kwargs)
                self.knowledge_bases[name] = {
                    "collection": collection,
                    "file_list": file_list
                }
            else:
                # 没有LLM时，只保存文件列表信息
                self.knowledge_bases[name] = {
                    "collection": None,
                    "file_list": file_list
                }
            
            # 将知识库作为资源注册
            self.resources[f"knowledge_base_{name}"] = Resource(
                uri=f"knowledge://{name}",
                name=f"Knowledge Base: {name}",
                description=f"Knowledge base containing {len(file_list)} files",
                mimeType="application/json"
            )
            logger.info(f"Knowledge base '{name}' registered successfully")
        except Exception as e:
            logger.error(f"Failed to register knowledge base '{name}': {e}")
    
    async def handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP请求"""
        try:
            method = message.get("method")
            params = message.get("params", {})
            msg_id = message.get("id")
            
            if method == "initialize":
                return self._create_response(msg_id, {
                    "serverName": "simple-llm-mcp-server",
                    "serverVersion": "1.0.0",
                    "capabilities": {
                        "resources": True,
                        "tools": True,
                        "prompts": True
                    }
                })
            
            elif method == "resources/list":
                resources = [asdict(resource) for resource in self.resources.values()]
                return self._create_response(msg_id, {"resources": resources})
            
            elif method == "resources/read":
                uri = params.get("uri")
                return self._create_response(msg_id, await self._read_resource(uri))
            
            elif method == "tools/list":
                tools_list = []
                for tool_name, tool_info in self.tools.items():
                    param_model = tool_info["param_model"]
                    schema = param_model.model_json_schema() if hasattr(param_model, 'model_json_schema') else {}
                    
                    tools_list.append({
                        "name": tool_name,
                        "description": tool_info["description"],
                        "inputSchema": schema
                    })
                
                return self._create_response(msg_id, {"tools": tools_list})
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self._call_tool(tool_name, arguments)
                return self._create_response(msg_id, {"content": [{"type": "text", "text": str(result)}]})
            
            elif method == "prompts/list":
                prompts_list = [
                    {
                        "name": name,
                        "description": info["description"],
                        "arguments": info["arguments"]
                    }
                    for name, info in self.prompts.items()
                ]
                return self._create_response(msg_id, {"prompts": prompts_list})
            
            elif method == "prompts/get":
                prompt_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self._get_prompt(prompt_name, arguments)
                return self._create_response(msg_id, {"messages": [{"content": {"type": "text", "text": result}}]})
            
            else:
                return self._create_error_response(msg_id, -32601, f"Method not found: {method}")
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._create_error_response(msg_id, -32603, f"Internal error: {str(e)}")
    
    def _create_response(self, msg_id: Any, result: Any) -> Dict[str, Any]:
        """创建响应消息"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }
    
    def _create_error_response(self, msg_id: Any, code: int, message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def _read_resource(self, uri: str) -> Dict[str, Any]:
        """读取资源内容"""
        if uri and uri.startswith("knowledge://"):
            kb_name = uri.replace("knowledge://", "")
            if kb_name in self.knowledge_bases:
                kb_info = self.knowledge_bases[kb_name]
                return {
                    "contents": [{
                        "type": "text",
                        "text": json.dumps({
                            "knowledge_base": kb_name,
                            "files": kb_info["file_list"],
                            "collection_info": "Vector database collection ready for search"
                        }, ensure_ascii=False, indent=2)
                    }]
                }
        
        raise ValueError(f"Unknown resource URI: {uri}")
    
    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        
        try:
            tool_info = self.tools[name]
            func = tool_info["func"]
            param_model = tool_info["param_model"]
            
            # 验证参数
            params = param_model(**arguments)
            
            # 调用工具函数
            result = func(**params.model_dump())
            
            return result
            
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            raise ValueError(f"Error executing tool {name}: {str(e)}")
    
    async def _get_prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """获取并执行提示"""
        if name == "llm_chat":
            query = arguments.get("query", "")
            use_rag = arguments.get("use_rag", False)
            knowledge_base = arguments.get("knowledge_base", "rag_demo")
            
            docs = None
            if use_rag:
                docs = self.llm.search_knowledge(query, collection_name=knowledge_base)
            
            result = self.llm.call(query, docs=docs)
            return str(result)
        
        elif name == "llm_chat_with_tools":
            query = arguments.get("query", "")
            allowed_tools = arguments.get("allowed_tools", [])
            use_rag = arguments.get("use_rag", False)
            knowledge_base = arguments.get("knowledge_base", "rag_demo")
            
            # 准备工具列表
            available_tools = []
            tool_functions = []
            for tool_name in allowed_tools:
                if tool_name in self.tools:
                    tool_info = self.tools[tool_name]
                    tool_functions.append(tool_info["func"])
                    available_tools.append({
                        "name": tool_name,
                        "description": tool_info["description"],
                        "func": tool_info["func"]
                    })
            
            # 准备文档（如果使用RAG）
            docs = None
            if use_rag:
                docs = self.llm.search_knowledge(query, collection_name=knowledge_base)
            
            # 使用工具调用能力
            try:
                if tool_functions:
                    # 创建工具调用器
                    from ..llm.tool_call import LLMToolCaller
                    caller = LLMToolCaller(tool_functions)
                    
                    # 构建包含工具描述的增强查询
                    tool_descriptions = []
                    for tool in available_tools:
                        tool_descriptions.append(f"- {tool['name']}: {tool['description']}")
                    
                    enhanced_query = f"""用户查询: {query}

可用工具:
{chr(10).join(tool_descriptions)}

请分析用户的查询，如果需要使用工具来回答问题，请使用相应的工具。如果不需要工具，直接回答即可。"""
                    
                    # 调用LLM，包含工具调用指令
                    llm_response = self.llm.call(enhanced_query, docs=docs, caller=caller)
                    
                    # 尝试解析工具调用
                    tool_name, tool_result = caller.call(str(llm_response))
                    
                    if tool_name and tool_result is not None:
                        # 成功执行了工具调用
                        # 构建包含工具结果的上下文，让LLM基于工具结果给出最终回答
                        tool_context = f"我刚才使用了{tool_name}工具，得到结果：{tool_result}"
                        follow_up_query = f"原始问题: {query}\n\n{tool_context}\n\n请基于工具执行的结果给出完整、自然的回答。"
                        
                        # 第二次调用LLM，基于工具结果生成最终答案
                        final_response = self.llm.call(follow_up_query, docs=docs)
                        return str(final_response)
                    else:
                        # 没有工具调用或工具调用失败，返回原始LLM响应
                        return str(llm_response)
                else:
                    # 没有可用工具，使用普通聊天
                    result = self.llm.call(query, docs=docs)
                    return str(result)
                    
            except Exception as e:
                logger.error(f"Tool calling failed: {e}")
                # 降级到普通聊天
                result = self.llm.call(query, docs=docs)
                return str(result)
        
        elif name == "structured_output":
            query = arguments.get("query", "")
            template = arguments.get("template", "")
            
            if template:
                parser = TemplateParser(template)
                result = self.llm.call(query, parser=parser)
            else:
                result = self.llm.call(query)
            
            return json.dumps(result, ensure_ascii=False, indent=2) if not isinstance(result, str) else result
        
        else:
            raise ValueError(f"Unknown prompt: {name}")

class SimpleMCPServerTransport:
    """简化版MCP服务器传输层"""
    
    def __init__(self, server: SimpleMCPServer):
        self.server = server
        self.running = False
    
    async def start_stdio(self):
        """启动标准输入输出传输"""
        self.running = True
        
        while self.running:
            try:
                # 读取输入
                line = await asyncio.get_event_loop().run_in_executor(None, input, "")
                if not line.strip():
                    continue
                
                # 解析JSON-RPC消息
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # 处理请求
                response = await self.server.handle_request(message)
                
                # 发送响应
                print(json.dumps(response, ensure_ascii=False))
                
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.error(f"Transport error: {e}")
        
        self.running = False
    
    def stop(self):
        """停止服务器"""
        self.running = False

async def run_simple_mcp_server(llm_instance: Optional[LLM] = None):
    """运行简化版MCP服务器"""
    server = SimpleMCPServer(llm_instance)
    
    # 检查并注册已存在的知识库
    try:
        import chromadb
        persist_dir = "rag_chroma_db"
        if Path(persist_dir).exists():
            chroma_client = chromadb.PersistentClient(path=persist_dir)
            collections = chroma_client.list_collections()
            
            for collection in collections:
                collection_name = collection.name
                count = collection.count()
                
                # 为每个知识库创建资源
                server.resources[f"knowledge_base_{collection_name}"] = Resource(
                    uri=f"knowledge://{collection_name}",
                    name=f"Knowledge Base: {collection_name}",
                    description=f"Knowledge base with {count} chunks",
                    mimeType="application/json"
                )
                
                # 记录知识库信息
                server.knowledge_bases[collection_name] = {
                    "collection": collection_name,
                    "file_list": [],
                    "chunk_count": count
                }
            
            print(f"注册了 {len(collections)} 个知识库资源")
        else:
            print("未找到知识库目录")
    except Exception as e:
        print(f"注册知识库资源失败: {e}")
    
    transport = SimpleMCPServerTransport(server)
    
    print("Simple MCP Server started. Ready for JSON-RPC communication.")
    
    try:
        await transport.start_stdio()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    finally:
        transport.stop()

if __name__ == "__main__":
    # 创建LLM实例
    llm = LLM()
    
    # 可选：构建知识库
    file_list = [
        {"file_path": "data/需求文件/需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx", "type": "需求文档"},
        {"file_path": "data/需求文件/湖北中烟工程中心数字管理应用用户操作手册v1.0.docx", "type": "用户手册"},
        {"file_path": "data/需求文件/数字信息化管理应用系统接口文档.docx", "type": "技术文档"}
    ]
    
    server = SimpleMCPServer(llm)
    
    try:
        server.register_knowledge_base("default_kb", file_list)
        print("知识库构建成功")
    except Exception as e:
        print(f"知识库构建失败: {e}")
    
    # 运行服务器
    asyncio.run(run_simple_mcp_server(llm))
