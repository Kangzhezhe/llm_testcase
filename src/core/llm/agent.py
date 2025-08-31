"""
智能代理模块 - 实现工具调用和自动重新生成机制
支持在工具调用后重新生成LLM输出，直到获得非工具调用的聊天结果
现在也支持MCP工具调用
"""
import json
from typing import List, Dict, Any, Optional, Callable, Union
from .llm import LLM
from .tool_call import LLMToolCaller
from .template_parser.template_parser import TemplateParser

# 尝试导入MCP相关模块
try:
    from .mcp_client import MCPServerConfig
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class Agent:
    """
    智能代理类，集成LLM和工具调用功能
    在工具调用后会自动重新生成LLM输出，直到获得最终的聊天结果
    """
    
    def __init__(self, model=None, temperature=0.3, history_len=5, logger=False, max_iterations=5, max_consecutive_tools=3, mcp_configs=None):
        """
        初始化智能代理
        
        Args:
            model: LLM模型名称
            temperature: 生成温度
            history_len: 历史记录长度
            logger: 是否启用日志
            max_iterations: 最大迭代次数，防止无限循环
            max_consecutive_tools: 最多连续工具调用次数
            mcp_configs: MCP服务器配置列表
        """
        self.llm = LLM(model=model, temperature=temperature, history_len=history_len, logger=logger, mcp_configs=mcp_configs)
        self.tools = {}
        self.tool_caller = None
        self.max_iterations = max_iterations
        self.max_consecutive_tools = max_consecutive_tools
        self.conversation_history = []
        self.mcp_configs = mcp_configs
        
    def register_tools(self, tools: List[Callable]):
        """
        注册工具函数
        
        Args:
            tools: 工具函数列表，每个函数需要有类型注解
        """
        for tool in tools:
            self.tools[tool.__name__] = tool
        self.tool_caller = LLMToolCaller(tools)
        
    def _add_to_history(self, role: str, content: str, tool_calls: List[Dict] = None, tool_results: List[Dict] = None):
        """添加对话历史"""
        entry = {
            "role": role,
            "content": content,
            "timestamp": None,  # 可以添加时间戳
        }
        if tool_calls:
            entry["tool_calls"] = tool_calls
        if tool_results:
            entry["tool_results"] = tool_results
        self.conversation_history.append(entry)
        
    def _build_enhanced_prompt(self, prompt: str, docs: Optional[List] = None) -> str:
        """
        构建增强的提示词，包含对话历史和工具调用上下文
        """
        # 构建对话历史
        history_text = ""
        if self.conversation_history:
            for entry in self.conversation_history[-self.llm.history_len:]:
                role = entry["role"]
                content = entry["content"]
                history_text += f"{role}: {content}\n"
                
                # 添加工具调用历史
                if "tool_calls" in entry:
                    for tool_call in entry["tool_calls"]:
                        history_text += f"[工具调用] {tool_call['name']}: {tool_call['args']}\n"
                if "tool_results" in entry:
                    for tool_result in entry["tool_results"]:
                        history_text += f"[工具结果] {tool_result['name']}: {tool_result['result']}\n"
        
        # 添加知识库内容
        if docs:
            context = "\n\n".join(
                doc["content"] if isinstance(doc, dict) and "content" in doc else doc for doc in docs
            )
            full_prompt = (
                history_text 
                + "\nuser: " 
                + f"你是知识库问答助手。请根据以下知识内容和对话历史回答用户问题。\n\n知识内容：\n{context}\n\n用户问题：{prompt}\n\n请简明回答："
            )
        else:
            full_prompt = history_text + "user: " + prompt
            
        return full_prompt
        
    def chat(self, prompt: str, docs: Optional[List] = None, parser: Optional[TemplateParser] = None, 
             use_tools: bool = True, use_mcp: bool = False, **kwargs) -> Dict[str, Any]:
        """
        智能对话接口，支持工具调用和自动重新生成
        
        Args:
            prompt: 用户输入
            docs: 可选的知识库文档
            parser: 可选的模板解析器
            use_tools: 是否启用传统工具调用
            use_mcp: 是否启用MCP工具调用
            **kwargs: 传递给LLM的其他参数
            
        Returns:
            包含最终结果和执行过程的字典
        """
        result = {
            "final_response": "",
            "tool_calls": [],
            "iterations": 0,
            "success": True,
            "error": None
        }
        
        try:
            # 添加用户输入到历史
            self._add_to_history("user", prompt)
            
            current_prompt = prompt
            iteration = 0
            consecutive_tool_calls = 0
            
            while iteration < self.max_iterations:
                iteration += 1
                result["iterations"] = iteration
                
                # 构建当前轮次的提示词
                if iteration == 1:
                    # 第一次调用，使用原始提示词
                    effective_prompt = current_prompt
                elif consecutive_tool_calls >= self.max_consecutive_tools:
                    # 连续工具调用过多，要求提供最终答案
                    tool_context = self._build_tool_context(result["tool_calls"])
                    effective_prompt = f"{current_prompt}\n\n{tool_context}\n\n你已经调用了多个工具，请基于以上所有工具调用结果，提供最终答案，不要再次调用工具。"
                else:
                    # 正常对话，可以继续调用工具
                    if result["tool_calls"]:
                        tool_context = self._build_tool_context(result["tool_calls"])
                        effective_prompt = f"{current_prompt}\n\n{tool_context}\n\n如果需要更多信息可以继续调用工具，或者基于现有结果给出最终答案。"
                    else:
                        effective_prompt = current_prompt
                
                # 决定本轮是否允许工具调用：
                # 如果当前是倒数第二次迭代（即 iteration == max_iterations - 1），
                # 则不允许再调用任何工具，让模型直接基于已有上下文给出最终答案。
                allow_tools_this_round = True
                if iteration >= self.max_iterations - 1:
                    # 到了最后一轮或倒数第二轮，不再允许工具调用
                    allow_tools_this_round = False

                # 调用LLM - 支持MCP和传统工具（根据 allow_tools_this_round 开关）
                if use_mcp and allow_tools_this_round:
                    # 优先使用MCP工具
                    llm_response = self.llm.call(
                        effective_prompt,
                        docs=docs,
                        parser=parser,
                        use_mcp=True,
                        **kwargs
                    )
                elif use_tools and self.tool_caller and allow_tools_this_round:
                    # 使用传统工具
                    llm_response = self.llm.call(
                        effective_prompt,
                        docs=docs,
                        parser=parser,
                        caller=self.tool_caller,
                        **kwargs
                    )
                else:
                    # 不使用工具（包括倒数第二轮/最后一轮的保护）
                    llm_response = self.llm.call(
                        effective_prompt,
                        docs=docs,
                        parser=parser,
                        **kwargs
                    )
                
                # 检查是否为工具调用
                if isinstance(llm_response, dict) and "tool_name" in llm_response:
                    # 记录工具调用
                    tool_call_info = {
                        "name": llm_response["tool_name"],
                        "args": self._extract_tool_args(llm_response["llm_output"]),
                        "result": llm_response["tool_result"],
                        "iteration": iteration,
                        "type": "mcp" if use_mcp else "traditional"
                    }
                    result["tool_calls"].append(tool_call_info)
                    
                    # 增加连续工具调用计数
                    consecutive_tool_calls += 1
                    
                    # 如果是最后一次迭代，直接返回工具结果
                    if iteration >= self.max_iterations:
                        result["final_response"] = f"工具调用结果: {llm_response['tool_result']}"
                        result["success"] = False
                        result["error"] = "达到最大迭代次数"
                        break
                    
                    # 继续下一轮
                    continue
                else:
                    # 获得了最终的聊天结果
                    result["final_response"] = llm_response
                    consecutive_tool_calls = 0  # 重置计数
                    break
            
            # 添加助手回复到历史
            self._add_to_history(
                "assistant", 
                result["final_response"],
                tool_calls=result["tool_calls"] if result["tool_calls"] else None
            )
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["final_response"] = f"处理过程中出现错误: {e}"
            
        return result
    
    def _extract_tool_args(self, llm_output: str) -> Dict:
        """从LLM输出中提取工具参数"""
        try:
            if self.tool_caller:
                parsed = self.tool_caller.parser.validate(llm_output)
                if parsed.get('success', False):
                    return parsed["data"].get("args", {})
        except Exception:
            pass
        return {}
    
    def _build_tool_context(self, tool_calls: List[Dict]) -> str:
        """构建工具调用上下文"""
        if not tool_calls:
            return ""
        
        context = "已执行的工具调用及结果:\n"
        for i, call in enumerate(tool_calls, 1):
            context += f"{i}. 调用工具 {call['name']}\n"
            context += f"   参数: {call['args']}\n"
            context += f"   结果: {call['result']}\n"
        
        return context
    
    def simple_chat(self, prompt: str, **kwargs) -> str:
        """
        简单聊天接口，直接返回最终回复字符串
        """
        result = self.chat(prompt, **kwargs)
        return result["final_response"]
    
    def chat_with_tools(self, prompt: str, tools: Optional[List[Callable]] = None, **kwargs) -> Dict[str, Any]:
        """
        带工具的聊天接口
        
        Args:
            prompt: 用户输入
            tools: 可选的工具列表，如果提供则临时注册这些工具
            **kwargs: 其他参数
        """
        # 临时注册工具
        original_tools = self.tools.copy()
        original_caller = self.tool_caller
        
        if tools:
            self.register_tools(tools)
        
        try:
            result = self.chat(prompt, use_tools=True, **kwargs)
        finally:
            # 恢复原始工具配置
            self.tools = original_tools
            self.tool_caller = original_caller
            
        return result
    
    def get_conversation_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.llm.history.clear()
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        tools = list(self.tools.keys())  # 传统工具
        
        # 添加MCP工具
        if hasattr(self.llm, 'get_available_tools'):
            mcp_tools = self.llm.get_available_tools("mcp")
            tools.extend(mcp_tools)
        
        return tools
    
    async def init_mcp(self):
        """初始化MCP连接"""
        if hasattr(self.llm, 'init_mcp'):
            await self.llm.init_mcp()
    
    async def cleanup_mcp(self):
        """清理MCP连接"""
        if hasattr(self.llm, 'cleanup_mcp'):
            await self.llm.cleanup_mcp()


# 便捷函数
def create_agent_with_tools(tools: List[Callable], **kwargs) -> Agent:
    """
    创建带工具的智能代理
    
    Args:
        tools: 工具函数列表
        **kwargs: 传递给Agent的参数，包括：
            - model: LLM模型名称
            - temperature: 生成温度
            - history_len: 历史记录长度
            - logger: 是否启用日志
            - max_iterations: 最大迭代次数
            - max_consecutive_tools: 最多连续工具调用次数
            - mcp_configs: MCP服务器配置列表
    """
    agent = Agent(**kwargs)
    agent.register_tools(tools)
    return agent


def create_agent_with_mcp(mcp_configs: List, **kwargs) -> Agent:
    """
    创建支持MCP的智能代理
    
    Args:
        mcp_configs: MCP服务器配置列表
        **kwargs: 传递给Agent的其他参数
    """
    if not MCP_AVAILABLE:
        raise ImportError("MCP功能不可用，请检查fastmcp库是否已安装")
    
    return Agent(mcp_configs=mcp_configs, **kwargs)


# 示例用法
if __name__ == "__main__":
    # 定义示例工具
    def calculate_add(a: float, b: float) -> float:
        """计算两个数的和"""
        return a + b
    
    def calculate_multiply(a: float, b: float) -> float:
        """计算两个数的乘积"""
        return a * b
    
    def get_weather(city: str) -> str:
        """获取城市天气信息"""
        return f"{city}今天天气晴朗，温度25°C"
    
    def search_web(query: str) -> str:
        """模拟网络搜索"""
        return f"搜索'{query}'的结果: 这是一个模拟的搜索结果"
    
    # 创建智能代理
    agent = create_agent_with_tools(
        tools=[calculate_add, calculate_multiply, get_weather, search_web],
        logger=True,
        max_iterations=5,
        max_consecutive_tools=4  # 允许最多连续4次工具调用
    )
    
    print("=== 智能代理示例 ===")
    print(f"可用工具: {agent.get_available_tools()}")
    
    # 测试用例1: 数学计算
    print("\n--- 测试1: 数学计算 ---")
    result1 = agent.chat("请帮我计算 3 + 5 的结果")
    print(f"最终回复: {result1['final_response']}")
    print(f"工具调用: {result1['tool_calls']}")
    print(f"迭代次数: {result1['iterations']}")
    
    # 测试用例2: 复合计算
    print("\n--- 测试2: 复合计算 ---")
    result2 = agent.chat("请计算 (3 + 5) × 2 的结果")
    print(f"最终回复: {result2['final_response']}")
    print(f"工具调用: {result2['tool_calls']}")
    print(f"迭代次数: {result2['iterations']}")
    
    # 测试用例3: 天气查询
    print("\n--- 测试3: 天气查询 ---")
    result3 = agent.chat("北京的天气怎么样？")
    print(f"最终回复: {result3['final_response']}")
    print(f"工具调用: {result3['tool_calls']}")
    print(f"迭代次数: {result3['iterations']}")
    
    # 测试用例4: 普通对话（不需要工具）
    print("\n--- 测试4: 普通对话 ---")
    result4 = agent.chat("你好，请介绍一下你自己")
    print(f"最终回复: {result4['final_response']}")
    print(f"工具调用: {result4['tool_calls']}")
    print(f"迭代次数: {result4['iterations']}")
    
    # 显示对话历史
    print("\n--- 对话历史 ---")
    for i, entry in enumerate(agent.get_conversation_history(), 1):
        print(f"{i}. {entry['role']}: {entry['content']}")
        if "tool_calls" in entry:
            print(f"   工具调用: {entry['tool_calls']}")
