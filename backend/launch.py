"""
BMI 系统一键启动菜单
用户可以选择启动哪个组件
"""

import os
import sys
import platform
import subprocess
from typing import Optional


class BMILauncher:
    """BMI 系统启动器"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    def run_command(self, command: str, name: str):
        """运行命令"""
        print(f"\n启动 {name}...")
        print(f"命令: {command}")
        print("-" * 60)
        
        try:
            if self.os_type == "Windows":
                os.system(command)
            else:
                os.system(f"bash -c '{command}'")
        except Exception as e:
            print(f"错误: {e}")
    
    def start_mcp_server(self):
        """启动 MCP 服务器"""
        cmd = f"cd {self.backend_dir} && python bmi_mcp_server.py 8001"
        self.run_command(cmd, "MCP 服务器 (Port 8001)")
    
    def start_agent_sync(self):
        """启动同步 Agent"""
        cmd = f"cd {self.backend_dir} && python bmi_agent_sync.py"
        self.run_command(cmd, "同步 Agent")
    
    def start_agent_async(self):
        """启动异步 Agent"""
        cmd = f"cd {self.backend_dir} && python bmi_agent.py"
        self.run_command(cmd, "异步 Agent")
    
    def start_agent_api(self):
        """启动 Agent API"""
        cmd = f"cd {self.backend_dir} && python bmi_agent_api.py 8000"
        self.run_command(cmd, "Agent API (Port 8000)")
    
    def run_tests(self):
        """运行测试"""
        cmd = f"cd {self.backend_dir} && python test_bmi_system.py"
        self.run_command(cmd, "系统测试")
    
    def check_system(self):
        """检查系统"""
        cmd = f"cd {self.backend_dir} && python check_system.py"
        self.run_command(cmd, "系统检查")
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "="*60)
        print("BMI 系统启动菜单")
        print("="*60)
        print("\n请选择要启动的组件:\n")
        print("1. 检查系统环境")
        print("2. 启动 MCP 服务器 (必需)")
        print("3. 启动同步 Agent (简单)")
        print("4. 启动异步 Agent (高级)")
        print("5. 启动 Agent API (生产)")
        print("6. 运行系统测试")
        print("0. 退出")
        print("\n" + "-"*60)
    
    def run(self):
        """主循环"""
        while True:
            self.show_menu()
            choice = input("\n请输入选项 (0-6): ").strip()
            
            if choice == "0":
                print("\n再见！")
                break
            elif choice == "1":
                self.check_system()
            elif choice == "2":
                self.start_mcp_server()
            elif choice == "3":
                self.start_agent_sync()
            elif choice == "4":
                self.start_agent_async()
            elif choice == "5":
                self.start_agent_api()
            elif choice == "6":
                self.run_tests()
            else:
                print("❌ 无效选项，请重新选择")
    
    def print_startup_guide(self):
        """打印启动指南"""
        print("\n" + "="*60)
        print("BMI 系统启动指南")
        print("="*60 + "\n")
        
        print("推荐启动步骤:\n")
        print("第 1 步: 检查系统环境")
        print("  python check_system.py\n")
        
        print("第 2 步: 启动 MCP 服务器（新终端）")
        print("  python bmi_mcp_server.py 8001\n")
        
        print("第 3 步: 选择一个 Agent 模式运行\n")
        
        print("方案 A - 同步模式（推荐新手）")
        print("  python bmi_agent_sync.py\n")
        
        print("方案 B - 异步模式（推荐高并发）")
        print("  python bmi_agent.py\n")
        
        print("方案 C - API 模式（推荐生产）")
        print("  python bmi_agent_api.py 8000")
        print("  访问: http://localhost:8000/docs\n")
        
        print("第 4 步: 测试系统（新终端）")
        print("  python test_bmi_system.py\n")
        print("="*60 + "\n")


def main():
    """主函数"""
    launcher = BMILauncher()
    
    # 检查参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "help":
            launcher.print_startup_guide()
        elif command == "check":
            launcher.check_system()
        elif command == "mcp":
            launcher.start_mcp_server()
        elif command == "sync":
            launcher.start_agent_sync()
        elif command == "async":
            launcher.start_agent_async()
        elif command == "api":
            launcher.start_agent_api()
        elif command == "test":
            launcher.run_tests()
        else:
            print(f"未知命令: {command}")
            print("\n可用命令:")
            print("  python launch.py help    - 显示启动指南")
            print("  python launch.py check   - 检查系统")
            print("  python launch.py mcp     - 启动 MCP 服务器")
            print("  python launch.py sync    - 启动同步 Agent")
            print("  python launch.py async   - 启动异步 Agent")
            print("  python launch.py api     - 启动 API 服务器")
            print("  python launch.py test    - 运行测试")
    else:
        # 交互式菜单
        try:
            launcher.run()
        except KeyboardInterrupt:
            print("\n\n已中断")


if __name__ == "__main__":
    main()
