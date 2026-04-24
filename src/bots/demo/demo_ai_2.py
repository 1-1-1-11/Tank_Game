"""
demo_ai_2.py
====================
Y. L. Tank Game 最简AI演示脚本。
- 演示如何实现 TankAI 类和 get_action(self, state) 接口。
- 代码示例：每回合朝最近的敌人靠拢。
- 适合选手参考 state 参数结构和基本用法。
"""

import random

class TankAI:
    def get_action(self, state):
        """
        示例：每回合朝最近的敌人靠拢。
        """
        self_info = state['self']
        my_x, my_y = self_info['x'], self_info['y']
        # 只考虑存活的其他坦克
        enemies = [t for t in state['tanks'] if t['alive'] and t['name'] != self_info['name']]
        if not enemies:
            return "UP"  # 没有敌人，随便走
        # 找到最近的敌人
        nearest = min(enemies, key=lambda t: abs(t['x']-my_x)+abs(t['y']-my_y))
        dx = nearest['x'] - my_x
        dy = nearest['y'] - my_y
        # 优先横向靠近，再纵向
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > 0 else "LEFT"
        elif dy != 0:
            return "DOWN" if dy > 0 else "UP"
        else:
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
