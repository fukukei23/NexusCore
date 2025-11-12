from nexuscore.agents.tester_agent import TesterAgent

tester_agent = TesterAgent()

# コードに対するテストと証言を生成
code_to_test = """def add(a, b): return a + b"""
result = tester_agent.generate_tests_and_testimony(code_to_test)
print(result)

# 実装計画に基づくテストと証言を生成
plan = {"functions": [{"name": "add", "args": ["a", "b"], "return": "a + b"}]}
result = tester_agent.generate_tests_from_plan(plan, 'some_module')
print(result)
