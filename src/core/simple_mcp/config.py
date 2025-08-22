"""
MCP配置和工具注册辅助模块
"""
import json
import os
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

class MCPConfig:
    """MCP配置管理"""
    
    def __init__(self, config_file: Optional[str] = None):
        # 默认使用configs子目录
        if not os.path.exists("configs"):
            os.makedirs("configs")
        if config_file is None:
            config_file = "configs/mcp_config.json"
        elif not str(config_file).startswith(('configs/', 'configs\\')) and '/' not in str(config_file) and '\\' not in str(config_file):
            # 如果只是文件名，放到configs目录下
            config_file = f"configs/{config_file}"
        
        self.config_file = config_file
        
        # 确保configs目录存在
        config_dir = Path(self.config_file).parent
        config_dir.mkdir(exist_ok=True)
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
        
        # 默认配置
        return {
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
            "knowledge_bases": {},
            "prompts": {
                "enabled": ["llm_chat", "structured_output"],
                "custom": {}
            }
        }
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.config.get("server", {})
    
    def get_enabled_tools(self) -> List[str]:
        """获取启用的工具列表"""
        return self.config.get("tools", {}).get("enabled", [])
    
    def get_custom_tools(self) -> Dict[str, Any]:
        """获取自定义工具配置"""
        return self.config.get("tools", {}).get("custom", {})
    
    def get_knowledge_bases(self) -> Dict[str, Any]:
        """获取知识库配置"""
        return self.config.get("knowledge_bases", {})
    
    def add_knowledge_base(self, name: str, file_list: List[Dict], **kwargs):
        """添加知识库配置"""
        if "knowledge_bases" not in self.config:
            self.config["knowledge_bases"] = {}
        
        self.config["knowledge_bases"][name] = {
            "file_list": file_list,
            "config": kwargs
        }
        self.save_config()
    
    def add_custom_tool(self, name: str, description: str, module_path: str, function_name: str):
        """添加自定义工具配置"""
        if "tools" not in self.config:
            self.config["tools"] = {"enabled": [], "custom": {}}
        
        self.config["tools"]["custom"][name] = {
            "description": description,
            "module_path": module_path,
            "function_name": function_name
        }
        
        if name not in self.config["tools"]["enabled"]:
            self.config["tools"]["enabled"].append(name)
        
        self.save_config()

class MCPToolRegistry:
    """MCP工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.categories: Dict[str, List[str]] = {
            "math": [],
            "text": [],
            "knowledge": [],
            "utility": [],
            "custom": []
        }
    
    def register(self, name: str, func: Callable, description: str = "", category: str = "custom"):
        """注册工具"""
        from ..llm.tool_call import infer_param_model
        
        self.tools[name] = {
            "func": func,
            "description": description or f"Tool: {name}",
            "param_model": infer_param_model(func),
            "category": category
        }
        
        if category in self.categories:
            self.categories[category].append(name)
        else:
            self.categories["custom"].append(name)
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """列出工具"""
        if category:
            return self.categories.get(category, [])
        return list(self.tools.keys())
    
    def get_tools_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """按类别获取工具"""
        tool_names = self.categories.get(category, [])
        return {name: self.tools[name] for name in tool_names if name in self.tools}
    
    def export_config(self) -> Dict[str, Any]:
        """导出工具配置"""
        return {
            "tools": {
                name: {
                    "description": info["description"],
                    "category": info["category"]
                }
                for name, info in self.tools.items()
            },
            "categories": self.categories
        }

# 预定义的工具函数
def create_default_tools():
    """创建默认工具集合"""
    registry = MCPToolRegistry()
    
    # 数学工具
    def add(a: float, b: float) -> float:
        """加法运算"""
        return a + b
    
    def subtract(a: float, b: float) -> float:
        """减法运算"""
        return a - b
    
    def multiply(a: float, b: float) -> float:
        """乘法运算"""
        return a * b
    
    def divide(a: float, b: float) -> float:
        """除法运算"""
        if b == 0:
            raise ValueError("Division by zero")
        return a / b
    
    def power(base: float, exponent: float) -> float:
        """幂运算"""
        return base ** exponent
    
    # 文本工具
    def echo(text: str) -> str:
        """回显文本"""
        return f"Echo: {text}"
    
    def uppercase(text: str) -> str:
        """转换为大写"""
        return text.upper()
    
    def lowercase(text: str) -> str:
        """转换为小写"""
        return text.lower()
    
    def reverse_text(text: str) -> str:
        """反转文本"""
        return text[::-1]
    
    def count_words(text: str) -> int:
        """统计单词数"""
        return len(text.split())
    
    # 实用工具
    def current_time() -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_uuid() -> str:
        """生成UUID"""
        import uuid
        return str(uuid.uuid4())
    
    def format_json(data: str) -> str:
        """格式化JSON"""
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            return f"JSON parsing error: {e}"
    
    # 注册工具
    registry.register("add", add, "执行两个数字的加法运算", "math")
    registry.register("subtract", subtract, "执行两个数字的减法运算", "math")
    registry.register("multiply", multiply, "执行两个数字的乘法运算", "math")
    registry.register("divide", divide, "执行两个数字的除法运算", "math")
    registry.register("power", power, "执行幂运算", "math")
    
    registry.register("echo", echo, "回显输入的文本", "text")
    registry.register("uppercase", uppercase, "将文本转换为大写", "text")
    registry.register("lowercase", lowercase, "将文本转换为小写", "text")
    registry.register("reverse_text", reverse_text, "反转文本", "text")
    registry.register("count_words", count_words, "统计文本中的单词数", "text")
    
    registry.register("current_time", current_time, "获取当前时间", "utility")
    registry.register("generate_uuid", generate_uuid, "生成唯一标识符", "utility")
    registry.register("format_json", format_json, "格式化JSON字符串", "utility")
    
    return registry

# MCP服务器启动器
class MCPServerLauncher:
    """MCP服务器启动器"""
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self.tool_registry = create_default_tools()
    
    def register_custom_tools(self):
        """注册自定义工具"""
        custom_tools = self.config.get_custom_tools()
        
        for tool_name, tool_config in custom_tools.items():
            try:
                # 动态导入工具函数
                import importlib
                module_path = tool_config["module_path"]
                function_name = tool_config["function_name"]
                
                module = importlib.import_module(module_path)
                func = getattr(module, function_name)
                
                self.tool_registry.register(
                    tool_name,
                    func,
                    tool_config["description"],
                    "custom"
                )
                
            except Exception as e:
                print(f"Failed to register custom tool {tool_name}: {e}")
    
    def create_server(self):
        """创建MCP服务器实例"""
        from .server import SimpleMCPServer
        from ..llm.llm import LLM
        
        # 创建LLM实例
        llm = LLM()
        
        # 创建服务器
        server = SimpleMCPServer(llm)
        
        # 注册工具
        enabled_tools = self.config.get_enabled_tools()
        for tool_name in enabled_tools:
            tool_info = self.tool_registry.get_tool(tool_name)
            if tool_info:
                server.register_tool(
                    tool_name,
                    tool_info["func"],
                    tool_info["description"]
                )
        
        # 注册知识库
        knowledge_bases = self.config.get_knowledge_bases()
        for kb_name, kb_config in knowledge_bases.items():
            try:
                server.register_knowledge_base(
                    kb_name,
                    kb_config["file_list"],
                    **kb_config.get("config", {})
                )
            except Exception as e:
                print(f"Failed to register knowledge base {kb_name}: {e}")
        
        return server

# 示例配置生成
def create_example_config():
    """创建示例配置文件"""
    config = MCPConfig("mcp_config_example.json")  # 这会自动放在configs/目录下
    
    # 添加知识库
    file_list = [
        {"file_path": "data/example.txt", "type": "document"},
        {"file_path": "data/manual.pdf", "type": "manual"}
    ]
    config.add_knowledge_base("example_kb", file_list, max_len=1000, overlap=100)
    
    # 添加自定义工具
    config.add_custom_tool(
        "custom_calculator",
        "自定义计算器",
        "src.core.custom_tools",
        "advanced_calculate"
    )
    
    print(f"Example config created: {config.config_file}")
    return config

if __name__ == "__main__":
    # 创建示例配置
    create_example_config()
