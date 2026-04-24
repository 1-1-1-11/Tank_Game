"""
demo_ai_1.py
====================
Y. L. Tank Game 最简AI演示脚本。
- 演示如何实现 TankAI 类和 get_action(self, state) 接口。
- 代码示例：每回合随机选择一个方向移动。
- 适合选手参考 state 参数结构和基本用法。
"""

import random

class TankAI:
    def get_action(self, state):
        """
        AI主逻辑，每回合被自动调用。
        参数:
            state (dict): 当前回合的游戏状态，结构见README。
        返回:
            str: "UP"、"DOWN"、"LEFT"、"RIGHT" 之一，表示本回合移动方向。
        示例：随机选择一个方向。
        """
        # 仅做演示：随机选择一个方向
        return random.choice(["UP", "DOWN", "LEFT", "RIGHT"])

if __name__ == "__main__":
    import sys, json
    if sys.version_info >= (3,7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ai = TankAI()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            state = json.loads(line)
            action = ai.get_action(state)
            print(action)
            sys.stdout.flush()
        except Exception:
            print("UP")
            sys.stdout.flush()
