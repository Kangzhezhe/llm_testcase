#!/usr/bin/env python
"""
MCP服务器启动脚本
简化的启动方式
"""
import asyncio
import sys
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.simple_mcp import MCPServerLauncher, MCPConfig, run_mcp_server
from src.core.llm.llm import LLM

def create_default_config():
    """创建默认配置"""
    # 使用configs目录
    config = MCPConfig("mcp_server_config.json")  # 这会自动放在configs/目录下
    
    # 添加示例知识库（如果文件存在）
    potential_files = [
        {"file_path": "data/网易云音乐PRD.md", "type": "产品文档"},
        {"file_path": "data/testcase.md", "type": "测试用例"},
        {"file_path": "data/final_requirements.md", "type": "需求文档"}
    ]
    
    existing_files = []
    for file_info in potential_files:
        file_path = project_root / file_info["file_path"]
        if file_path.exists():
            existing_files.append(file_info)
    
    if existing_files:
        config.add_knowledge_base("default_kb", existing_files)
        print(f"已添加 {len(existing_files)} 个文件到默认知识库")
    
    return config

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动MCP服务器")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--port", "-p", type=int, default=8000, help="服务器端口")
    parser.add_argument("--host", default="localhost", help="服务器主机")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    parser.add_argument("--create-config", action="store_true", help="创建默认配置文件")
    
    args = parser.parse_args()
    
    if args.create_config:
        config = create_default_config()
        print(f"配置文件已创建: {config.config_file}")
        return
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # 加载配置
    config_file = args.config or str(project_root/'configs' / "mcp_server_config.json")
    if not Path(config_file).exists():
        print(f"配置文件不存在: {config_file}")
        print("使用 --create-config 创建默认配置")
        return
    
    config = MCPConfig(config_file)
    
    # 创建启动器
    launcher = MCPServerLauncher(config)
    
    # 创建LLM实例
    print("初始化LLM...")
    llm = LLM()
    
    # 构建知识库
    knowledge_bases = config.get_knowledge_bases()
    for kb_name, kb_config in knowledge_bases.items():
        try:
            print(f"构建知识库: {kb_name}")
            llm.build_knowledge_base(
                kb_config["file_list"], 
                collection_name=kb_name,
                **kb_config.get("config", {})
            )
            print(f"  ✓ 知识库 {kb_name} 构建成功")
        except Exception as e:
            print(f"  ✗ 知识库 {kb_name} 构建失败: {e}")
    
    # 启动服务器
    print(f"启动简化版MCP服务器...")
    print(f"配置: {config_file}")
    print("按 Ctrl+C 停止服务器")
    print("注意：这是简化版MCP实现，使用JSON-RPC over stdio协议")
    
    try:
        from src.core.simple_mcp.server import run_simple_mcp_server
        await run_simple_mcp_server(llm)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
