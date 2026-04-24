"""
advanced_ai.py
====================
进阶坦克AI - 解决多子弹协同威胁问题
第一阶段：威胁场算法 + 基础战术分析
"""

import random
import math

class ThreatField:
    """威胁场算法 - 计算整个地图的威胁分布"""
    
    def __init__(self, map_width, map_height):
        self.width = map_width
        self.height = map_height
        self.threat_map = [[0] * map_height for _ in range(map_width)]
    
    def calculate_threat_field(self, bullets, tanks, walls, my_name):
        """计算威胁场"""
        # 重置威胁图
        self.threat_map = [[0] * self.height for _ in range(self.width)]
        
        # 1. 子弹威胁传播
        for bullet in bullets:
            if bullet['owner'] != my_name:  # 只考虑敌人的子弹
                self.propagate_bullet_threat(bullet, walls)
        
        # 2. 敌人威胁传播
        for tank in tanks:
            if tank['alive'] and tank['name'] != my_name:
                self.propagate_tank_threat(tank)
        
        return self.threat_map
    
    def propagate_bullet_threat(self, bullet, walls):
        """子弹威胁传播 - 预测子弹轨迹"""
        x, y = bullet['x'], bullet['y']
        dx, dy = bullet['dx'], bullet['dy']
        
        # 预测子弹未来5步的轨迹
        for step in range(5):
            next_x = x + dx * step * 2  # 子弹速度是坦克2倍
            next_y = y + dy * step * 2
            
            # 检查是否撞墙
            if [next_x, next_y] in walls:
                break
            
            # 检查地图边界
            if not (0 <= next_x < self.width and 0 <= next_y < self.height):
                break
            
            # 威胁强度：距离越近威胁越大，但考虑时间衰减
            threat = 15 / (step + 1)
            self.threat_map[next_x][next_y] += threat
    
    def propagate_tank_threat(self, tank):
        """敌人威胁传播 - 考虑敌人攻击范围"""
        x, y = tank['x'], tank['y']
        
        # 敌人周围3格范围内都有威胁
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                new_x, new_y = x + dx, y + dy
                
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    distance = abs(dx) + abs(dy)
                    if distance <= 3:
                        threat = 8 / (distance + 1)
                        self.threat_map[new_x][new_y] += threat

class TacticalAnalyzer:
    """战术分析器 - 分析敌人意图和协同攻击"""
    
    def analyze_coordinated_threats(self, bullets, tanks, my_name):
        """分析协同威胁"""
        threats = {
            'bullet_clusters': self.find_bullet_clusters(bullets, my_name),
            'enemy_positions': self.analyze_enemy_positions(tanks, my_name),
            'escape_routes': self.find_escape_routes(bullets, tanks, my_name)
        }
        return threats
    
    def find_bullet_clusters(self, bullets, my_name):
        """找到子弹群集"""
        enemy_bullets = [b for b in bullets if b['owner'] != my_name]
        clusters = []
        
        for bullet in enemy_bullets:
            # 找到距离小于2格的子弹群
            nearby_bullets = []
            for other_bullet in enemy_bullets:
                if bullet != other_bullet:
                    distance = abs(bullet['x'] - other_bullet['x']) + abs(bullet['y'] - other_bullet['y'])
                    if distance <= 2:
                        nearby_bullets.append(other_bullet)
            
            if len(nearby_bullets) >= 1:  # 至少2颗子弹形成群集
                cluster = [bullet] + nearby_bullets
                if cluster not in clusters:
                    clusters.append(cluster)
        
        return clusters
    
    def analyze_enemy_positions(self, tanks, my_name):
        """分析敌人位置分布"""
        enemies = [t for t in tanks if t['alive'] and t['name'] != my_name]
        
        if not enemies:
            return {'count': 0, 'positions': [], 'threat_level': 0}
        
        # 计算敌人包围程度
        my_tank = next(t for t in tanks if t['name'] == my_name)
        my_x, my_y = my_tank['x'], my_tank['y']
        
        surrounding_enemies = 0
        for enemy in enemies:
            distance = abs(enemy['x'] - my_x) + abs(enemy['y'] - my_y)
            if distance <= 4:  # 4格范围内算包围
                surrounding_enemies += 1
        
        threat_level = surrounding_enemies / len(enemies) if enemies else 0
        
        return {
            'count': len(enemies),
            'positions': [(e['x'], e['y']) for e in enemies],
            'threat_level': threat_level
        }
    
    def find_escape_routes(self, bullets, tanks, my_name):
        """寻找逃生路线"""
        my_tank = next(t for t in tanks if t['name'] == my_name)
        my_x, my_y = my_tank['x'], my_tank['y']
        
        # 检查四个方向的逃生可能性
        directions = [
            ("UP", my_x, my_y - 1),
            ("DOWN", my_x, my_y + 1),
            ("LEFT", my_x - 1, my_y),
            ("RIGHT", my_x + 1, my_y)
        ]
        
        escape_routes = []
        for direction, new_x, new_y in directions:
            if 0 <= new_x < 19 and 0 <= new_y < 13:  # 地图边界
                # 计算这个方向的威胁
                threat = self.calculate_direction_threat(new_x, new_y, bullets, tanks, my_name)
                escape_routes.append({
                    'direction': direction,
                    'threat': threat,
                    'safe': threat < 10  # 威胁小于10算安全
                })
        
        return escape_routes
    
    def calculate_direction_threat(self, x, y, bullets, tanks, my_name):
        """计算某个方向的威胁"""
        threat = 0
        
        # 子弹威胁
        for bullet in bullets:
            if bullet['owner'] != my_name:
                distance = abs(bullet['x'] - x) + abs(bullet['y'] - y)
                if distance <= 2:
                    threat += 15 / (distance + 1)
        
        # 敌人威胁
        for tank in tanks:
            if tank['alive'] and tank['name'] != my_name:
                distance = abs(tank['x'] - x) + abs(tank['y'] - y)
                if distance <= 2:
                    threat += 10 / (distance + 1)
        
        return threat

class AdvancedTankAI:
    """进阶坦克AI - 使用威胁场和战术分析"""
    
    def __init__(self):
        self.threat_field = None
        self.tactical_analyzer = TacticalAnalyzer()
        self.last_action = "UP"
        self.hp_thresholds = {
            'critical': 1,    # 血量1点：保命模式
            'low': 2,         # 血量2点：谨慎模式
            'normal': 3       # 血量3点：正常模式
        }
    
    def get_action(self, state):
        """主决策函数"""
        my_info = state['self']
        my_hp = my_info['hp']
        
        # 初始化威胁场
        self.threat_field = ThreatField(state['map_width'], state['map_height'])
        threat_map = self.threat_field.calculate_threat_field(
            state['bullets'], state['tanks'], state['walls'], my_info['name']
        )
        
        # 战术分析
        tactical_info = self.tactical_analyzer.analyze_coordinated_threats(
            state['bullets'], state['tanks'], my_info['name']
        )
        
        # 根据血量选择策略
        if my_hp <= self.hp_thresholds['critical']:
            return self.survival_mode(state, threat_map, tactical_info)
        elif my_hp <= self.hp_thresholds['low']:
            return self.cautious_mode(state, threat_map, tactical_info)
        else:
            return self.aggressive_mode(state, threat_map, tactical_info)
    
    def survival_mode(self, state, threat_map, tactical_info):
        """保命模式 - 血量极低时"""
        my_x, my_y = state['self']['x'], state['self']['y']
        
        # 寻找威胁最低的方向
        best_direction = "UP"
        min_threat = float('inf')
        
        for direction, new_x, new_y in self.get_valid_moves(state, my_x, my_y):
            threat = threat_map[new_x][new_y]
            
            # 额外考虑逃生路线
            for route in tactical_info['escape_routes']:
                if route['direction'] == direction and route['safe']:
                    threat *= 0.5  # 安全路线威胁减半
            
            if threat < min_threat:
                min_threat = threat
                best_direction = direction
        
        return best_direction
    
    def cautious_mode(self, state, threat_map, tactical_info):
        """谨慎模式 - 血量较低时"""
        my_x, my_y = state['self']['x'], state['self']['y']
        
        # 平衡威胁和攻击机会
        best_direction = "UP"
        best_score = float('-inf')
        
        for direction, new_x, new_y in self.get_valid_moves(state, my_x, my_y):
            threat = threat_map[new_x][new_y]
            attack_value = self.calculate_attack_value(state, new_x, new_y)
            
            # 谨慎模式：安全权重更高
            score = attack_value * 0.3 - threat * 0.7
            
            if score > best_score:
                best_score = score
                best_direction = direction
        
        return best_direction
    
    def aggressive_mode(self, state, threat_map, tactical_info):
        """攻击模式 - 血量充足时"""
        my_x, my_y = state['self']['x'], state['self']['y']
        
        # 优先攻击，但避免过高威胁
        best_direction = "UP"
        best_score = float('-inf')
        
        for direction, new_x, new_y in self.get_valid_moves(state, my_x, my_y):
            threat = threat_map[new_x][new_y]
            attack_value = self.calculate_attack_value(state, new_x, new_y)
            
            # 攻击模式：攻击权重更高，但威胁不能太高
            if threat < 20:  # 威胁不能超过阈值
                score = attack_value * 0.7 - threat * 0.3
                
                if score > best_score:
                    best_score = score
                    best_direction = direction
        
        # 如果没有安全的攻击路线，转为谨慎模式
        if best_score == float('-inf'):
            return self.cautious_mode(state, threat_map, tactical_info)
        
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
        # 地图边界
        if x < 0 or x >= state['map_width'] or y < 0 or y >= state['map_height']:
            return False
        
        # 墙壁
        if [x, y] in state['walls']:
            return False
        
        # 其他坦克
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
                
                if distance <= 5:  # 攻击范围内
                    attack_value += 15 / (distance + 1)
                    
                    # 敌人血量低时优先攻击
                    if tank['hp'] <= 1:
                        attack_value += 10
        
        return attack_value

if __name__ == "__main__":
    import sys, json
    if sys.version_info >= (3,7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ai = AdvancedTankAI()
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