"""
improved_ai.py
====================
改进版坦克AI - 解决预测性和自适应问题
保持简洁，重点改进核心算法
"""

import random
import math

class ImprovedThreatField:
    """改进的威胁场算法 - 增加预测性"""
    
    def __init__(self, map_width, map_height):
        self.width = map_width
        self.height = map_height
        self.threat_map = [[0] * map_height for _ in range(map_width)]
        self.future_threat_map = [[0] * map_height for _ in range(map_width)]
    
    def calculate_threat_field(self, bullets, tanks, walls, my_name):
        """计算当前威胁场和未来威胁场"""
        # 重置威胁图
        self.threat_map = [[0] * self.height for _ in range(self.width)]
        self.future_threat_map = [[0] * self.height for _ in range(self.width)]
        
        # 当前威胁
        for bullet in bullets:
            if bullet['owner'] != my_name:
                self.propagate_bullet_threat(bullet, walls, current=True)
        
        for tank in tanks:
            if tank['alive'] and tank['name'] != my_name:
                self.propagate_tank_threat(tank, current=True)
        
        # 未来威胁预测（预测2步后）
        for bullet in bullets:
            if bullet['owner'] != my_name:
                self.propagate_bullet_threat(bullet, walls, current=False)
        
        for tank in tanks:
            if tank['alive'] and tank['name'] != my_name:
                self.propagate_tank_threat(tank, current=False)
        
        return self.threat_map, self.future_threat_map
    
    def propagate_bullet_threat(self, bullet, walls, current=True):
        """子弹威胁传播 - 区分当前和未来威胁"""
        x, y = bullet['x'], bullet['y']
        dx, dy = bullet['dx'], bullet['dy']
        
        # 当前威胁：预测3步
        # 未来威胁：预测5步（从2步后开始）
        start_step = 0 if current else 2
        end_step = 3 if current else 5
        
        target_map = self.threat_map if current else self.future_threat_map
        
        for step in range(start_step, end_step):
            next_x = x + dx * step * 2
            next_y = y + dy * step * 2
            
            if [next_x, next_y] in walls:
                break
            
            if not (0 <= next_x < self.width and 0 <= next_y < self.height):
                break
            
            # 威胁强度：未来威胁权重稍低
            base_threat = 15 if current else 10
            threat = base_threat / (step + 1)
            target_map[next_x][next_y] += threat
    
    def propagate_tank_threat(self, tank, current=True):
        """敌人威胁传播"""
        x, y = tank['x'], tank['y']
        target_map = self.threat_map if current else self.future_threat_map
        
        # 敌人周围威胁范围
        range_size = 3 if current else 4  # 未来威胁范围稍大
        
        for dx in range(-range_size, range_size + 1):
            for dy in range(-range_size, range_size + 1):
                new_x, new_y = x + dx, y + dy
                
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    distance = abs(dx) + abs(dy)
                    if distance <= range_size:
                        base_threat = 8 if current else 6
                        threat = base_threat / (distance + 1)
                        target_map[new_x][new_y] += threat

class AdaptiveStrategy:
    """自适应策略系统"""
    
    def __init__(self):
        self.performance_history = []  # 记录表现历史
        self.strategy_weights = {
            'survival': 0.7,    # 保命权重
            'attack': 0.3       # 攻击权重
        }
        self.threat_threshold = 15  # 威胁阈值
    
    def update_strategy(self, my_hp, enemy_count, threat_level):
        """根据情况自适应调整策略"""
        # 根据血量调整保命权重
        if my_hp == 1:
            self.strategy_weights['survival'] = 0.9
            self.strategy_weights['attack'] = 0.1
        elif my_hp == 2:
            self.strategy_weights['survival'] = 0.7
            self.strategy_weights['attack'] = 0.3
        else:
            self.strategy_weights['survival'] = 0.5
            self.strategy_weights['attack'] = 0.5
        
        # 根据敌人数量调整
        if enemy_count >= 3:
            self.strategy_weights['survival'] += 0.1
            self.strategy_weights['attack'] -= 0.1
        
        # 根据威胁等级调整
        if threat_level > 20:
            self.strategy_weights['survival'] += 0.1
            self.strategy_weights['attack'] -= 0.1
        
        # 确保权重在合理范围内
        self.strategy_weights['survival'] = max(0.3, min(0.9, self.strategy_weights['survival']))
        self.strategy_weights['attack'] = 1 - self.strategy_weights['survival']
    
    def get_decision_score(self, threat, attack_value, future_threat):
        """计算决策评分"""
        # 当前威胁
        current_risk = threat * self.strategy_weights['survival']
        
        # 未来威胁（预测性）
        future_risk = future_threat * 0.3  # 未来威胁权重30%
        
        # 攻击价值
        attack_benefit = attack_value * self.strategy_weights['attack']
        
        # 综合评分：攻击价值 - 当前威胁 - 未来威胁
        score = attack_benefit - current_risk - future_risk
        
        return score

class ImprovedTankAI:
    """改进版坦克AI - 预测性 + 自适应"""
    
    def __init__(self):
        self.threat_field = None
        self.strategy = AdaptiveStrategy()
        self.last_action = "UP"
        self.action_history = []  # 记录行动历史
    
    def get_action(self, state):
        """主决策函数"""
        my_info = state['self']
        my_hp = my_info['hp']
        
        # 计算威胁场（当前 + 未来）
        self.threat_field = ImprovedThreatField(state['map_width'], state['map_height'])
        current_threat, future_threat = self.threat_field.calculate_threat_field(
            state['bullets'], state['tanks'], state['walls'], my_info['name']
        )
        
        # 分析当前情况
        enemy_count = len([t for t in state['tanks'] if t['alive'] and t['name'] != my_info['name']])
        current_threat_level = self.get_current_threat_level(current_threat, my_info)
        
        # 自适应调整策略
        self.strategy.update_strategy(my_hp, enemy_count, current_threat_level)
        
        # 获取最佳移动方向
        best_direction = self.find_best_move(state, current_threat, future_threat, my_info)
        
        # 记录行动历史
        self.action_history.append({
            'action': best_direction,
            'hp': my_hp,
            'threat_level': current_threat_level,
            'enemy_count': enemy_count
        })
        
        # 保持历史记录在合理范围内
        if len(self.action_history) > 10:
            self.action_history.pop(0)
        
        return best_direction
    
    def get_current_threat_level(self, threat_map, my_info):
        """获取当前位置的威胁等级"""
        x, y = my_info['x'], my_info['y']
        return threat_map[x][y]
    
    def find_best_move(self, state, current_threat, future_threat, my_info):
        """找到最佳移动方向"""
        my_x, my_y = my_info['x'], my_info['y']
        
        best_direction = "UP"
        best_score = float('-inf')
        
        for direction, new_x, new_y in self.get_valid_moves(state, my_x, my_y):
            # 当前威胁
            threat = current_threat[new_x][new_y]
            
            # 未来威胁
            future_threat_level = future_threat[new_x][new_y]
            
            # 攻击价值
            attack_value = self.calculate_attack_value(state, new_x, new_y)
            
            # 计算综合评分
            score = self.strategy.get_decision_score(threat, attack_value, future_threat_level)
            
            # 额外考虑：避免重复行动
            if len(self.action_history) >= 2:
                last_action = self.action_history[-1]['action']
                if direction == last_action:
                    score *= 0.8  # 重复行动惩罚
            
            if score > best_score:
                best_score = score
                best_direction = direction
        
        return best_direction
    
    def get_valid_moves(self, state, x, y):
        """获取有效的移动方向"""
        moves = []
        directions = [
            ("UP", x, y - 1),
            ("DOWN", x, y + 1),
            ("LEFT", x - 1, y),
            ("RIGHT", x + 1, y)
        ]
        
        for direction, new_x, new_y in directions:
            if self.is_valid_position(state, new_x, new_y):
                moves.append((direction, new_x, new_y))
        
        return moves if moves else [("UP", x, y)]
    
    def is_valid_position(self, state, x, y):
        """检查位置是否有效"""
        if x < 0 or x >= state['map_width'] or y < 0 or y >= state['map_height']:
            return False
        
        if [x, y] in state['walls']:
            return False
        
        for tank in state['tanks']:
            if tank['alive'] and tank['x'] == x and tank['y'] == y:
                return False
        
        return True
    
    def calculate_attack_value(self, state, x, y):
        """计算攻击价值"""
        attack_value = 0
        
        for tank in state['tanks']:
            if tank['alive'] and tank['name'] != state['self']['name']:
                distance = abs(tank['x'] - x) + abs(tank['y'] - y)
                
                if distance <= 5:
                    # 基础攻击价值
                    base_value = 15 / (distance + 1)
                    
                    # 敌人血量奖励
                    if tank['hp'] <= 1:
                        base_value += 15  # 血量低时大幅提高攻击价值
                    elif tank['hp'] == 2:
                        base_value += 5   # 血量中等时适度提高
                    
                    attack_value += base_value
        
        return attack_value

if __name__ == "__main__":
    import sys, json
    if sys.version_info >= (3,7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ai = ImprovedTankAI()
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