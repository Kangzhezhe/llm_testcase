"""
Agent模块的测试用例
"""
import sys
import os

from ..template_parser.template_parser import TemplateParser
from ..agent import Agent, create_agent_with_tools


def tool_calculate_add(a: float, b: float) -> float:
    """加法工具函数"""
    return a + b


def tool_calculate_multiply(a: float, b: float) -> float:
    """乘法工具函数"""
    return a * b


def tool_echo(text: str) -> str:
    """回声工具函数"""
    return f"回声: {text}"


def tool_get_info(name: str) -> str:
    """信息获取工具函数"""
    return f"获取到{name}的信息: 这是一个测试用户"


def test_agent_basic():
    """测试基本功能"""
    print("=== 测试Agent基本功能 ===")
    
    # 创建agent
    agent = Agent(logger=False, max_iterations=3)
    
    # 注册工具
    tools = [tool_calculate_add, tool_calculate_multiply, tool_echo, tool_get_info]
    agent.register_tools(tools)
    
    print(f"可用工具: {agent.get_available_tools()}")
    
    # 测试1: 简单计算
    print("\n--- 测试1: 简单计算 ---")
    result = agent.chat("请使用工具计算 3 + 5")
    print(f"结果: {result}")
    
    # 测试2: 不需要工具的对话
    print("\n--- 测试2: 普通对话 ---")
    result = agent.chat("你好，今天天气不错")
    print(f"结果: {result}")
    
    # 测试3: 回声测试
    print("\n--- 测试3: 回声测试 ---")
    result = agent.chat("请使用工具重复说'Hello World'")
    print(f"结果: {result}")
    
    # 添加断言来验证结果
    assert result["success"] == True
    assert "tool_calls" in result


def test_agent_with_create_function():
    """测试使用便捷创建函数"""
    print("\n\n=== 测试便捷创建函数 ===")
    parser = TemplateParser("最后结果是:{result:int}")
    
    tools = [tool_calculate_add, tool_calculate_multiply]
    agent = create_agent_with_tools(tools, logger=False, max_iterations=8)
    
    # 测试复合计算1: 简单的两步运算
    print("\n--- 测试复合计算1: (4 + 6) × 3 ---")
    result1 = agent.chat("请使用工具计算 (4 + 6) × 3 的结果，每一步需要数学计算的都调用工具计算", parser=parser)
    print(f"结果1: {result1}")
    print(f"工具调用次数: {len(result1['tool_calls'])}")
    print(f"迭代次数: {result1['iterations']}")
    
    # 清空历史，开始新的测试
    agent.clear_history()
    
    # 测试复合计算2: 三步运算
    print("\n--- 测试复合计算2: (2 + 3) × (4 + 5) ---")
    result2 = agent.chat("请使用工具计算 (2 + 3) × (4 + 5) 的结果，每一步数学运算都要调用相应的工具",parser=parser)
    print(f"结果2: {result2}")
    print(f"工具调用次数: {len(result2['tool_calls'])}")
    print(f"迭代次数: {result2['iterations']}")
    
    # 清空历史，开始新的测试
    agent.clear_history()
    
    # 测试复合计算3: 更复杂的多步运算
    print("\n--- 测试复合计算3: ((1 + 2) × 3) + (4 × 5) ---")
    result3 = agent.chat("请使用工具计算 ((1 + 2) × 3) + (4 × 5) 的结果，每个加法和乘法运算都必须调用对应的工具",parser=parser)
    print(f"结果3: {result3}")
    print(f"工具调用次数: {len(result3['tool_calls'])}")
    print(f"迭代次数: {result3['iterations']}")
    
    # 清空历史，开始新的测试
    agent.clear_history()
    
    # 测试复合计算4: 连续多次相同运算
    print("\n--- 测试复合计算4: 1 + 2 + 3 + 4 + 5 ---")
    result4 = agent.chat("请使用加法工具计算 1 + 2 + 3 + 4 + 5 的结果，每次加法都要调用工具",parser=parser)
    print(f"结果4: {result4}")
    print(f"工具调用次数: {len(result4['tool_calls'])}")
    print(f"迭代次数: {result4['iterations']}")
    
    # 清空历史，开始新的测试
    agent.clear_history()
    
    # 测试复合计算5: 嵌套运算
    print("\n--- 测试复合计算5: 2 × (3 + (4 × 5)) ---")
    result5 = agent.chat("请使用工具计算 2 × (3 + (4 × 5)) 的结果，按运算优先级每步都调用相应工具",parser=parser)
    print(f"结果5: {result5}")
    print(f"工具调用次数: {len(result5['tool_calls'])}")
    print(f"迭代次数: {result5['iterations']}")
    
    # 清空历史，开始新的测试
    agent.clear_history()
    
    # 测试复合计算6: 大数运算
    print("\n--- 测试复合计算6: (100 + 200) × (300 + 400) ---")
    result6 = agent.chat("请使用工具计算 (100 + 200) × (300 + 400) 的结果，每个括号内的加法和最后的乘法都要调用工具",parser=parser)
    print(f"结果6: {result6}")
    print(f"工具调用次数: {len(result6['tool_calls'])}")
    print(f"迭代次数: {result6['iterations']}")
    
    # 统计所有测试结果
    all_results = [result1, result2, result3, result4, result5, result6]
    total_tool_calls = sum(len(r['tool_calls']) for r in all_results)
    total_iterations = sum(r['iterations'] for r in all_results)
    success_count = sum(1 for r in all_results if r['success'])
    
    print(f"\n=== 复合运算测试总结 ===")
    print(f"测试用例数: {len(all_results)}")
    print(f"成功用例数: {success_count}")
    print(f"总工具调用次数: {total_tool_calls}")
    print(f"总迭代次数: {total_iterations}")
    print(f"平均每个用例工具调用次数: {total_tool_calls/len(all_results):.1f}")
    print(f"平均每个用例迭代次数: {total_iterations/len(all_results):.1f}")
    
    # 添加断言来验证测试结果
    assert success_count == len(all_results), f"期望所有测试成功，但只有{success_count}/{len(all_results)}成功"
    assert total_tool_calls > 0, "应该有工具调用"
    assert total_iterations > 0, "应该有迭代"


def test_conversation_history():
    """测试对话历史功能"""
    print("\n\n=== 测试对话历史 ===")
    
    agent = create_agent_with_tools([tool_calculate_add], logger=False)
    
    # 进行几轮对话
    agent.chat("使用工具计算 1 + 1")
    agent.chat("使用工具计算 2 + 3")
    agent.chat("你好")
    
    # 查看历史
    history = agent.get_conversation_history()
    print(f"对话历史条数: {len(history)}")
    for i, entry in enumerate(history, 1):
        print(f"{i}. {entry['role']}: {entry['content'][:50]}...")
        if "tool_calls" in entry:
            print(f"   工具调用: {len(entry['tool_calls'])}次")


def test_simple_chat():
    """测试简单聊天接口"""
    print("\n\n=== 测试简单聊天接口 ===")
    
    agent = create_agent_with_tools([tool_calculate_add], logger=False)
    
    # 使用简单接口
    response = agent.simple_chat("计算 5 + 7")
    print(f"简单聊天结果: {response}")


def test_chat_with_tools():
    """测试临时工具功能"""
    print("\n\n=== 测试临时工具功能 ===")
    
    agent = Agent(logger=False)
    
    # 定义临时工具
    def temp_tool(x: int) -> str:
        return f"临时工具处理了: {x}"
    
    # 使用临时工具
    result = agent.chat_with_tools("请使用临时工具处理数字 42", tools=[temp_tool])
    print(f"临时工具结果: {result}")
    
    # 检查工具是否被清理
    print(f"agent可用工具: {agent.get_available_tools()}")


if __name__ == "__main__":
    try:
        # 运行所有测试
        test_agent_basic()
        test_agent_with_create_function()
        test_conversation_history()
        test_simple_chat()
        test_chat_with_tools()
        
        print("\n\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
