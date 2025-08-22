"""
MCP命令行工具
提供启动服务器、运行客户端测试等功能
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path

def setup_server_command(subparsers):
    """设置服务器命令"""
    server_parser = subparsers.add_parser('server', help='启动MCP服务器')
    server_parser.add_argument('--config', '-c', default='configs/mcp_config.json', help='配置文件路径')
    server_parser.add_argument('--host', default='localhost', help='服务器主机')
    server_parser.add_argument('--port', type=int, default=8000, help='服务器端口')
    server_parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

def setup_client_command(subparsers):
    """设置客户端命令"""
    client_parser = subparsers.add_parser('client', help='运行MCP客户端测试')
    client_parser.add_argument('--server-cmd', nargs='+', help='服务器启动命令')
    client_parser.add_argument('--demo', action='store_true', help='运行演示')
    client_parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')

def setup_config_command(subparsers):
    """设置配置命令"""
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_subparsers = config_parser.add_subparsers(dest='config_action', help='配置操作')
    
    # 创建配置
    create_parser = config_subparsers.add_parser('create', help='创建配置文件')
    create_parser.add_argument('--file', '-f', default='configs/mcp_config.json', help='配置文件路径')
    create_parser.add_argument('--example', action='store_true', help='创建示例配置')
    
    # 查看配置
    show_parser = config_subparsers.add_parser('show', help='显示配置')
    show_parser.add_argument('--file', '-f', default='configs/mcp_config.json', help='配置文件路径')
    
    # 添加知识库
    kb_parser = config_subparsers.add_parser('add-kb', help='添加知识库')
    kb_parser.add_argument('name', help='知识库名称')
    kb_parser.add_argument('files', nargs='+', help='文件路径列表')
    kb_parser.add_argument('--type', default='document', help='文件类型')
    kb_parser.add_argument('--config', '-c', default='configs/mcp_config.json', help='配置文件路径')

async def run_server(args):
    """运行MCP服务器"""
    from .config import MCPConfig, MCPServerLauncher
    
    print(f"启动简化版MCP服务器...")
    print(f"配置文件: {args.config}")
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    try:
        # 加载配置
        config = MCPConfig(args.config)
        
        # 创建启动器
        launcher = MCPServerLauncher(config)
        launcher.register_custom_tools()
        
        # 创建服务器
        server = launcher.create_server()
        
        # 启动服务器
        from .server import run_simple_mcp_server
        await run_simple_mcp_server(server.llm)
        
    except Exception as e:
        print(f"服务器启动失败: {e}")
        return 1
    
    return 0

async def run_client_demo(args):
    """运行客户端演示"""
    from .client import demo_simple_mcp_client
    
    print("运行简化版MCP客户端演示...")
    
    try:
        await demo_simple_mcp_client()
    except Exception as e:
        print(f"客户端演示失败: {e}")
        return 1
    
    return 0

async def run_client_interactive(args):
    """运行交互式客户端"""
    from .client import SimpleMCPClientManager
    
    print("启动交互式简化版MCP客户端...")
    print("输入 'help' 查看帮助，输入 'quit' 退出")
    
    try:
        async with SimpleMCPClientManager() as client:
            while True:
                try:
                    user_input = input("\nMCP> ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    if user_input.lower() == 'help':
                        print("""
可用命令:
  help                    - 显示帮助
  list resources          - 列出资源
  list tools              - 列出工具
  list prompts            - 列出提示
  call <tool> <args>      - 调用工具 (args为JSON格式，如: {"a": 1, "b": 2})
  chat <message>          - 普通聊天
  chat-tools <tools> <message> - 聊天时允许LLM调用指定工具
  rag <message>           - RAG聊天
  struct <template> <msg> - 结构化输出
  quit/exit/q             - 退出

示例命令:
  call add {"a": 10, "b": 20}
  call echo {"text": "Hello World"}
  chat 你好，请介绍一下自己
  chat-tools add 请使用工具计算 10+5 
  rag 总结我的产品需求文档
  struct "姓名={name:str},年龄={age:int}" 请输出一个用户示例
                        """)
                        continue
                    
                    if user_input.lower() == 'list resources':
                        resources = await client.list_resources()
                        print("可用资源:")
                        for r in resources:
                            print(f"  {r['name']}: {r['uri']}")
                        continue
                    
                    if user_input.lower() == 'list tools':
                        tools = await client.list_tools()
                        print("可用工具:")
                        for t in tools:
                            print(f"  {t['name']}: {t['description']}")
                        continue
                    
                    if user_input.lower() == 'list prompts':
                        prompts = await client.list_prompts()
                        print("可用提示:")
                        for p in prompts:
                            print(f"  {p['name']}: {p['description']}")
                        continue
                    
                    if user_input.startswith('call '):
                        parts = user_input[5:].split(' ', 1)
                        if len(parts) < 2:
                            print("用法: call <tool_name> <json_args>")
                            print("示例: call add {\"a\": 10, \"b\": 20}")
                            continue
                        
                        tool_name = parts[0]
                        try:
                            args = json.loads(parts[1])
                            result = await client.call_tool(tool_name, args)
                            print(f"结果: {result}")
                        except json.JSONDecodeError as e:
                            print(f"JSON格式错误: {e}")
                            print("正确格式示例: {\"a\": 10, \"b\": 20}")
                            print("注意：属性名必须用双引号包围")
                        except Exception as e:
                            print(f"工具调用失败: {e}")
                        continue
                    
                    if user_input.startswith('chat '):
                        message = user_input[5:]
                        result = await client.chat(message)
                        print(f"回复: {result}")
                        continue
                    
                    if user_input.startswith('chat-tools '):
                        parts = user_input[11:].split(' ', 1)
                        if len(parts) < 2:
                            print("用法: chat-tools <tool1,tool2,...> <message>")
                            print("示例: chat-tools add 请使用工具计算 10+5 ")
                            continue
                        
                        tools_str = parts[0]
                        message = parts[1]
                        
                        # 解析工具列表
                        allowed_tools = [tool.strip() for tool in tools_str.split(',')]
                        
                        # 获取可用工具列表以验证
                        available_tools = await client.list_tools()
                        available_tool_names = [tool['name'] for tool in available_tools]
                        
                        # 验证工具是否存在
                        invalid_tools = [tool for tool in allowed_tools if tool not in available_tool_names]
                        if invalid_tools:
                            print(f"未找到工具: {', '.join(invalid_tools)}")
                            print(f"可用工具: {', '.join(available_tool_names)}")
                            continue
                        
                        print(f"正在处理聊天请求（允许工具: {', '.join(allowed_tools)}）...")
                        
                        # 调用带工具的聊天
                        try:
                            result = await client.chat_with_tools(message, allowed_tools)
                            print(f"回复: {result}")
                        except AttributeError:
                            # 如果客户端还没有chat_with_tools方法，使用普通聊天
                            print("注意：当前客户端版本不支持工具调用，使用普通聊天模式")
                            result = await client.chat(message)
                            print(f"回复: {result}")
                        except Exception as e:
                            print(f"带工具聊天失败: {e}")
                        continue
                    
                    if user_input.startswith('rag '):
                        message = user_input[4:]
                        result = await client.chat(message, use_rag=True)
                        print(f"RAG回复: {result}")
                        continue
                    
                    if user_input.startswith('struct '):
                        parts = user_input[7:].split(' ', 1)
                        if len(parts) < 2:
                            print("用法: struct <template> <message>")
                            print("示例: struct \"姓名={name:str},年龄={age:int}\" 请输出一个用户示例")
                            continue
                        
                        template = parts[0]
                        message = parts[1]
                        result = await client.structured_chat(message, template)
                        print(f"结构化回复: {result}")
                        continue
                    
                    print("未知命令，输入 'help' 查看帮助")
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"操作失败: {e}")
        
        print("\n再见!")
        
    except Exception as e:
        print(f"交互式客户端失败: {e}")
        return 1
    
    return 0

def handle_config_command(args):
    """处理配置命令"""
    if args.config_action == 'create':
        from .config import MCPConfig, create_example_config
        
        if args.example:
            config = create_example_config()
            print(f"示例配置已创建: {config.config_file}")
        else:
            config = MCPConfig(args.file)
            config.save_config()
            print(f"配置文件已创建: {args.file}")
    
    elif args.config_action == 'show':
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            print(json.dumps(config_data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    elif args.config_action == 'add-kb':
        from .config import MCPConfig
        
        config = MCPConfig(args.config)
        file_list = [{"file_path": fp, "type": args.type} for fp in args.files]
        config.add_knowledge_base(args.name, file_list)
        print(f"知识库 '{args.name}' 已添加到配置")
    
    else:
        print("请指定配置操作: create, show, add-kb")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MCP (Model Context Protocol) 工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 设置子命令
    setup_server_command(subparsers)
    setup_client_command(subparsers)
    setup_config_command(subparsers)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'server':
            return await run_server(args)
        
        elif args.command == 'client':
            if args.demo:
                return await run_client_demo(args)
            elif args.interactive:
                return await run_client_interactive(args)
            else:
                return await run_client_demo(args)  # 默认运行演示
        
        elif args.command == 'config':
            handle_config_command(args)
            return 0
        
    except KeyboardInterrupt:
        print("\n操作已取消")
        return 130
    except Exception as e:
        print(f"执行失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
