"""
BMI 系统测试脚本
用于验证 MCP 服务器和 LangGraph 助手是否正常工作
"""

import asyncio
import httpx
import json
from typing import Optional


class BMISystemTester:
    """BMI 系统测试工具"""
    
    def __init__(self, mcp_url: str = "http://localhost:8001"):
        self.mcp_url = mcp_url
    
    async def test_server_health(self) -> bool:
        """测试 MCP 服务器是否在线"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.mcp_url}/health")
                result = response.json()
                print(f"✓ 服务器健康检查: {result['status']}")
                return True
        except Exception as e:
            print(f"✗ 服务器离线: {e}")
            return False
    
    async def test_list_tools(self) -> bool:
        """测试获取工具列表"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.mcp_url}/tools")
                tools = response.json()
                print(f"✓ 获取工具列表: {len(tools['tools'])} 个工具")
                for tool in tools['tools']:
                    print(f"  - {tool['name']}: {tool['description']}")
                return True
        except Exception as e:
            print(f"✗ 获取工具列表失败: {e}")
            return False
    
    async def test_calculate_bmi(self, weight: float, height: float) -> bool:
        """测试 BMI 计算工具"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"{self.mcp_url}/invoke_tool",
                    params={"tool_name": "calculate_bmi"},
                    json={"weight": weight, "height": height}
                )
                result = response.json()
                if result.get("success"):
                    data = result["result"]
                    print(f"✓ BMI 计算成功:")
                    print(f"  体重: {data['weight']} kg")
                    print(f"  身高: {data['height']} m")
                    print(f"  BMI: {data['bmi']}")
                    print(f"  分类: {data['category']}")
                    return True
                else:
                    print(f"✗ BMI 计算失败: {result.get('error')}")
                    return False
        except Exception as e:
            print(f"✗ BMI 计算异常: {e}")
            return False
    
    async def test_stream_invoke(self, weight: float, height: float) -> bool:
        """测试流式调用"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                async with client.stream(
                    "GET",
                    f"{self.mcp_url}/stream_invoke_tool",
                    params={
                        "tool_name": "calculate_bmi",
                        "weight": weight,
                        "height": height
                    }
                ) as response:
                    print(f"✓ 流式调用测试:")
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[6:])
                            print(f"  {data['status']}: {data}")
                    return True
        except Exception as e:
            print(f"✗ 流式调用失败: {e}")
            return False
    
    async def test_invalid_input(self) -> bool:
        """测试无效输入处理"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"{self.mcp_url}/invoke_tool",
                    params={"tool_name": "calculate_bmi"},
                    json={"weight": -60, "height": 1.70}
                )
                if response.status_code == 400:
                    print(f"✓ 无效输入处理: 正确拒绝了负体重")
                    return True
                else:
                    print(f"✗ 无效输入处理: 未能拒绝")
                    return False
        except Exception as e:
            print(f"✗ 无效输入测试异常: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("BMI 系统测试")
        print("="*60 + "\n")
        
        tests = [
            ("服务器健康检查", self.test_server_health()),
            ("获取工具列表", self.test_list_tools()),
            ("BMI 计算 (60kg, 1.70m)", self.test_calculate_bmi(60, 1.70)),
            ("BMI 计算 (85kg, 1.75m)", self.test_calculate_bmi(85, 1.75)),
            ("流式调用测试", self.test_stream_invoke(70, 1.80)),
            ("无效输入处理", self.test_invalid_input()),
        ]
        
        results = []
        for name, test in tests:
            print(f"\n测试: {name}")
            print("-" * 60)
            try:
                result = await test
                results.append((name, result))
            except Exception as e:
                print(f"✗ 测试异常: {e}")
                results.append((name, False))
        
        # 打印总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        passed = sum(1 for _, r in results if r)
        total = len(results)
        print(f"通过: {passed}/{total}")
        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")
        print("="*60 + "\n")
        
        return passed == total


async def test_agent_integration():
    """测试 LangGraph Agent 集成（需要 Ollama 运行）"""
    print("\n" + "="*60)
    print("LangGraph Agent 集成测试")
    print("="*60 + "\n")
    
    try:
        from bmi_agent import run_bmi_agent
        
        test_queries = [
            "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。",
            "我的身高是 1.80 m，体重 85 kg，请计算 BMI",
        ]
        
        for query in test_queries:
            print(f"\n用户: {query}")
            print("-" * 60)
            response = await run_bmi_agent(query)
            print(f"助手: {response}")
            print("="*60)
    
    except ImportError as e:
        print(f"✗ 无法导入 bmi_agent: {e}")
        print("  请确保已安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"✗ Agent 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    # 第一步：测试 MCP 服务器
    tester = BMISystemTester()
    all_passed = await tester.run_all_tests()
    
    if all_passed:
        print("\n✓ MCP 服务器测试全部通过！\n")
        
        # 第二步：测试 Agent 集成（可选）
        try:
            await test_agent_integration()
        except KeyboardInterrupt:
            print("\n✓ 测试中断")
    else:
        print("\n✗ 部分测试失败，请检查 MCP 服务器是否正常运行")
        print("  运行命令: python bmi_mcp_server.py 8001")


if __name__ == "__main__":
    import sys
    
    # 允许自定义 MCP 服务器 URL
    mcp_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    
    print(f"使用 MCP 服务器: {mcp_url}\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
