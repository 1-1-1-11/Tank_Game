# xjy_upgraded.py
import sys, json, heapq
from collections import deque, defaultdict
import math

# ----------------- 可调参数 (战术决策模型) -----------------
# --- 核心权重 (W_ = Weight) ---
W_SURVIVAL = 100.0  # 生存分权重 (压倒性)
W_ANTI_TRAP = 15.0  # 反陷阱权重 (避免被逼入死角)
W_POSITION = 5.0  # 战略位置权重 (走廊/机动性/贴墙)
W_ATTACK = 1.0  # 攻击权重 (只有在安全时才考虑)

# --- 启发式参数 ---
ANTI_TRAP_BONUS = 5.0  # 每多一个未来选项的奖励
ENEMY_PROXIMITY_PENALTY = 25.0  # 对紧邻敌人的惩罚 (防止撞车)
GOAL_DANGER_K = 2.5

# --- 地图结构感知参数 (强化) ---
MIN_CORRIDOR_LENGTH = 3
CORRIDOR_DANGER_PENALTY = 5.0

# --- A* 和地图评估优化参数 (强化) ---
WALL_PROXIMITY_PENALTY = 3.5
MOBILITY_BRANCH_FACTOR = 1.5

# --- 威胁评估参数 (强化) ---
BULLET_PATH_THREAT = 150.0
FUTURE_WEIGHT = 0.6
DANGER_K = 2.0

# --- 混战/Vulture 模式参数 ---
VULTURING_HP = 1

# --- 不再使用的旧参数 (A*相关) ---
# ASTAR_GOAL_RADIUS = 7
# MOBILITY_GOAL_FACTOR = 0.8

# ----------------- 基本常量 -----------------
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}


# ----------------- 工具函数 -----------------
def manhattan(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])


def dir_from(a, b):
    if not a or not b: return None
    dx, dy = b[0] - a[0], b[1] - a[1]
    return next((k for k, v in DIRS.items() if v == (dx, dy)), None)


def is_valid(pos, w, h, walls, tanks_pos_set):
    x, y = pos
    return 0 <= x < w and 0 <= y < h and pos not in walls and pos not in tanks_pos_set


# ----------------- 辅助类 (威胁场, 策略, 评估器) -----------------
class ThreatField:  # (无重大修改)
    def __init__(self, w, h, walls):
        self.w, self.h, self.walls = w, h, walls;
        self.cur = [[0.0] * h for _ in range(w)];
        self.fut = [[0.0] * h for _ in range(w)]

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def calculate(self, bullets, tanks, my_name, strategy):
        for x in range(self.w):
            for y in range(self.h): self.cur[x][y] = 0.0; self.fut[x][y] = 0.0
        enemy_dirs = {t['name']: strategy.enemy_dir(t['name'], (t['x'], t['y'])) for t in tanks if
                      t.get('alive') and t.get('name') != my_name}
        for b in bullets:
            if b.get('owner') != my_name: self._propagate_bullet(b, self.cur, range(1, 3)); self._propagate_bullet(b,
                                                                                                                   self.fut,
                                                                                                                   range(
                                                                                                                       3,
                                                                                                                       5))
        for t in tanks:
            if t.get('alive') and t.get('name') != my_name:
                self._propagate_enemy_body(t, self.cur, 3, 12.0);
                self._propagate_enemy_body(t, self.fut, 4, 6.0)
                self._propagate_potential_fire_lines(t, enemy_dirs.get(t['name']))
        return self.cur, self.fut

    def _propagate_bullet(self, b, target, steps):
        x, y, dx, dy = b['x'], b['y'], b['dx'], b['dy']
        for s in steps:
            nx, ny = x + dx * s, y + dy * s
            if not self.in_bounds(nx, ny) or (nx, ny) in self.walls: break
            target[nx][ny] += BULLET_PATH_THREAT / (s + 0.5)

    def _propagate_enemy_body(self, t, target, rng, base):
        tx, ty = t['x'], t['y']
        for dx in range(-rng, rng + 1):
            for dy in range(-rng, rng + 1):
                nx, ny = tx + dx, ty + dy
                if self.in_bounds(nx, ny) and abs(dx) + abs(dy) <= rng: target[nx][ny] += base / (abs(dx) + abs(dy) + 1)

    def _propagate_potential_fire_lines(self, enemy, enemy_dir):
        ex, ey = enemy['x'], enemy['y']
        for d_name, (dx, dy) in DIRS.items():
            base = 8.0
            if enemy_dir:
                if d_name == enemy_dir:
                    base = 18.0
                elif d_name == OPPOSITE.get(enemy_dir):
                    base = 1.0
                else:
                    base = 6.0
            cx, cy, dist = ex, ey, 0
            while True:
                cx += dx;
                cy += dy;
                dist += 1
                if (cx, cy) in self.walls or not self.in_bounds(cx, cy): break
                self.fut[cx][cy] += base / (dist + 0.5)


class Strategy:  # (简化, 只用于调整攻击性)
    def __init__(self):
        self.mode = "balanced";
        self.last_pos = defaultdict(lambda: None)

    def update(self, hp, enemy_count, high_threat, enemies, best_target):
        if best_target and best_target['hp'] <= VULTURING_HP and hp > 1:
            self.mode = 'vulture'
        elif hp <= 1 or high_threat or enemy_count >= 2:
            self.mode = 'evasion'
        elif enemy_count == 1 and hp >= 2:
            self.mode = 'aggressive'
        else:
            self.mode = 'balanced'
        for t in enemies: self.last_pos[t['name']] = (t['x'], t['y'])

    def get_attack_factor(self):
        if self.mode == 'vulture': return 1.5
        if self.mode == 'evasion': return 0.1
        if self.mode == 'aggressive': return 1.0
        if self.mode == 'balanced': return 0.5
        return 0.2

    def enemy_dir(self, name, pos):
        last = self.last_pos.get(name)
        if last and last != pos: return dir_from(last, pos)
        return None


# ----------------- AI 主体 (全新架构) -----------------
class TankAI:
    def __init__(self):
        self.strategy = Strategy();
        self.last_action = None;
        self.last_hp = None
        self.mobility_map = None;
        self.static_walls = None;
        self.protection_timer = 0
        self.corridor_danger_map = None

    def _compute_mobility_map(self, w, h, walls):
        if self.static_walls == walls and self.mobility_map is not None: return
        self.static_walls = set(walls)
        self.mobility_map = [[0.0] * h for _ in range(w)]
        valid_neighbors = {}
        for x in range(w):
            for y in range(h):
                if (x, y) not in walls: valid_neighbors[(x, y)] = sum(1 for dx, dy in DIRS.values() if
                                                                      0 <= x + dx < w and 0 <= y + dy < h and (x + dx,
                                                                                                               y + dy) not in walls)
        for x in range(w):
            for y in range(h):
                if (x, y) in walls: continue
                q, visited, mobility_score = deque([((x, y), 0)]), {(x, y)}, 0.0
                while q:
                    (cur_x, cur_y), depth = q.popleft()
                    if depth >= MOBILITY_BFS_DEPTH: continue
                    neighbor_count = valid_neighbors.get((cur_x, cur_y), 0)
                    if neighbor_count > 2:
                        mobility_score += (neighbor_count - 2) * MOBILITY_BRANCH_FACTOR
                    else:
                        mobility_score += 0.1
                    for dx, dy in DIRS.values():
                        nx, ny = cur_x + dx, cur_y + dy
                        if (nx, ny) not in visited and (nx, ny) in valid_neighbors: visited.add((nx, ny)); q.append(
                            ((nx, ny), depth + 1))
                self.mobility_map[x][y] = mobility_score

    def _compute_corridor_danger_map(self, w, h, walls):
        if self.static_walls == walls and self.corridor_danger_map is not None: return
        self.static_walls = set(walls)
        self.corridor_danger_map = [[0.0] * h for _ in range(w)]
        for y in range(h):
            current_corridor = []
            for x in range(w):
                if (x, y) not in self.static_walls:
                    current_corridor.append((x, y))
                else:
                    if len(current_corridor) >= MIN_CORRIDOR_LENGTH:
                        for pos in current_corridor: self.corridor_danger_map[pos[0]][pos[1]] += CORRIDOR_DANGER_PENALTY
                    current_corridor = []
            if len(current_corridor) >= MIN_CORRIDOR_LENGTH:
                for pos in current_corridor: self.corridor_danger_map[pos[0]][pos[1]] += CORRIDOR_DANGER_PENALTY
        for x in range(w):
            current_corridor = []
            for y in range(h):
                if (x, y) not in self.static_walls:
                    current_corridor.append((x, y))
                else:
                    if len(current_corridor) >= MIN_CORRIDOR_LENGTH:
                        for pos in current_corridor: self.corridor_danger_map[pos[0]][pos[1]] += CORRIDOR_DANGER_PENALTY
                    current_corridor = []
            if len(current_corridor) >= MIN_CORRIDOR_LENGTH:
                for pos in current_corridor: self.corridor_danger_map[pos[0]][pos[1]] += CORRIDOR_DANGER_PENALTY

    def get_action(self, state):
        me = state['self'];
        w, h = state['map_width'], state['map_height']
        my_pos = (me['x'], me['y']);
        hp = me['hp']
        walls = set(tuple(wloc) for wloc in state.get('walls', []))
        tanks_all = state.get('tanks', [])
        enemies = [t for t in tanks_all if t['name'] != me['name'] and t.get('alive')]

        if self.last_hp is not None and hp < self.last_hp: self.protection_timer = 10  # 保护时间缩短, 更快反应
        is_protected = self.protection_timer > 0
        if self.protection_timer > 0: self.protection_timer -= 1

        if self.mobility_map is None: self._compute_mobility_map(w, h, walls)
        if self.corridor_danger_map is None: self._compute_corridor_danger_map(w, h, walls)

        tf = ThreatField(w, h, walls);
        cur, fut = tf.calculate(state.get('bullets', []), tanks_all, me['name'], self.strategy)
        danger = [[cur[x][y] + FUTURE_WEIGHT * fut[x][y] for y in range(h)] for x in range(w)]
        if is_protected: danger = [[d * 0.1 for d in row] for row in danger]

        best_target, _ = self._evaluate_targets(enemies, my_pos)
        high_threat = danger[my_pos[0]][my_pos[1]] > 18.0
        self.strategy.update(hp, len(enemies), high_threat, enemies, best_target)

        chosen_action = self._get_best_move_by_score(state, danger, best_target)

        return self._validate_and_get_final_action(chosen_action, state)

    def _get_best_move_by_score(self, state, danger, best_target):
        my_pos = (state['self']['x'], state['self']['y'])
        w, h = state['map_width'], state['map_height']
        tanks_pos_set = {(t['x'], t['y']) for t in state.get('tanks', []) if t.get('alive')}

        move_scores = {}

        for move in DIR_LIST:
            # 1. 规则检查 (硬约束)
            if self.last_action and move == OPPOSITE.get(self.last_action):
                move_scores[move] = -float('inf')
                continue

            dx, dy = DIRS[move]
            next_pos = (my_pos[0] + dx, my_pos[1] + dy)

            if not is_valid(next_pos, w, h, self.static_walls, tanks_pos_set):
                move_scores[move] = -float('inf')
                continue

            # 2. 综合评分 (软约束)
            nx, ny = next_pos

            # 生存分 (核心)
            survival_score = -danger[nx][ny]

            # 反陷阱分
            future_options = sum(1 for d in DIR_LIST if
                                 is_valid((nx + DIRS[d][0], ny + DIRS[d][1]), w, h, self.static_walls,
                                          tanks_pos_set - {my_pos}))
            anti_trap_score = future_options * ANTI_TRAP_BONUS

            # 位置分
            position_score = self.mobility_map[nx][ny] \
                             - self.corridor_danger_map[nx][ny] \
                             - (sum(
                1 for ndx, ndy in DIRS.values() if (nx + ndx, ny + ndy) in self.static_walls) * WALL_PROXIMITY_PENALTY) \
                             - (ENEMY_PROXIMITY_PENALTY if any(
                manhattan(next_pos, (e['x'], e['y'])) <= 1 for e in state.get('tanks', []) if
                e.get('alive') and e['name'] != state['self']['name']) else 0)

            # 攻击分
            attack_score = 0
            if best_target:
                dist_to_target = manhattan(next_pos, (best_target['x'], best_target['y']))
                attack_score = 50.0 / (dist_to_target + 1)

            # 总分
            total_score = (survival_score * W_SURVIVAL) + \
                          (anti_trap_score * W_ANTI_TRAP) + \
                          (position_score * W_POSITION) + \
                          (attack_score * W_ATTACK * self.strategy.get_attack_factor())

            move_scores[move] = total_score

        if not move_scores or all(s == -float('inf') for s in move_scores.values()):
            return None  # 没有找到任何合规的移动

        return max(move_scores, key=move_scores.get)

    def _evaluate_targets(self, enemies, my_pos):
        if not enemies: return None, None
        scored_enemies = [{'data': e, 'score': ((3 - e['hp']) * 20 / (manhattan(my_pos, (e['x'], e['y'])) + 1)) * (
            5 if e['hp'] <= VULTURING_HP else 1)} for e in enemies]
        best_target = max(scored_enemies, key=lambda x: x['score'])['data']
        return best_target, None

    def _validate_and_get_final_action(self, chosen_action, state):
        my_pos = (state['self']['x'], state['self']['y'])
        w, h = state['map_width'], state['map_height']
        tanks_pos_set = {(t['x'], t['y']) for t in state.get('tanks', []) if t.get('alive')}

        # 如果主逻辑给出了一个有效的、非反向的动作, 直接采纳
        if chosen_action:
            dx, dy = DIRS[chosen_action]
            next_pos = (my_pos[0] + dx, my_pos[1] + dy)
            is_reverse = self.last_action and chosen_action == OPPOSITE.get(self.last_action)
            if is_valid(next_pos, w, h, self.static_walls, tanks_pos_set) and not is_reverse:
                return chosen_action

        # 如果主逻辑卡住或给出了非法动作, 启动安全的回退逻辑
        # 1. 优先尝试重复上一步 (如果安全)
        if self.last_action:
            dx, dy = DIRS[self.last_action]
            next_pos = (my_pos[0] + dx, my_pos[1] + dy)
            if is_valid(next_pos, w, h, self.static_walls, tanks_pos_set):
                return self.last_action

        # 2. 寻找任何一个安全的、非反向的移动
        valid_moves = [d for d in DIR_LIST if
                       (not self.last_action or d != OPPOSITE.get(self.last_action)) and is_valid(
                           (my_pos[0] + DIRS[d][0], my_pos[1] + DIRS[d][1]), w, h, self.static_walls, tanks_pos_set)]
        if valid_moves:
            # 简单地选择一个, 例如 UP > LEFT > RIGHT > DOWN
            for pref in ["UP", "LEFT", "RIGHT", "DOWN"]:
                if pref in valid_moves:
                    return pref

        # 3. 终极兜底: 如果连非反向都不行 (被完全堵死), 只能选择一个不会撞墙的动作, 哪怕是反向
        any_valid_move = [d for d in DIR_LIST if
                          is_valid((my_pos[0] + DIRS[d][0], my_pos[1] + DIRS[d][1]), w, h, self.static_walls,
                                   tanks_pos_set)]
        if any_valid_move:
            return any_valid_move[0]

        # 4. 如果被完全封死, 没有任何有效移动, 只能选择原地不动 (重复上一步, 哪怕会撞墙, Pro规则会处理)
        return self.last_action if self.last_action else "UP"


# ----------------- 管道模式主循环 -----------------
if __name__ == "__main__":
    ai = TankAI()
    if sys.version_info >= (3, 7):
        try:
            sys.stdin.reconfigure(encoding='utf-8'); sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    while True:
        line = sys.stdin.readline()
        if not line: break
        state, action = None, None
        try:
            state = json.loads(line)
            action = ai.get_action(state)
        except Exception:
            try:
                if state is None: state = json.loads(line)
                action = ai._validate_and_get_final_action(None, state)  # 即使主逻辑崩溃, 也要走安全校验
            except Exception:
                action = "UP"  # 终极异常

        print(action)
        sys.stdout.flush()
        if state:
            ai.last_action = action
            ai.last_hp = state['self'].get('hp')


