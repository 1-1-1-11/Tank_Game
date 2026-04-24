# fixed_test.py  （请将其保存覆盖原 test.py）
import sys, json, heapq
from collections import deque, defaultdict

# ----------------- 可调参数 -----------------
DEFAULT_MODE = "balanced"
REVERSE_FORBID = True
HAZARD_MEMORY_DECAY = 6
DEBUG = False

# 宏观视角与战略参数
MOBILITY_BFS_DEPTH = 8
REVERSE_PENALTY_SCORE = 10000

# --- 陷阱惩罚常量 (保留) ---
TRAP_PENALTY_DEADEND = 1000.0  # 绝对死胡同 (1个出口)
TRAP_PENALTY_CORRIDOR = 500.0  # 一格宽走廊 (2个相反出口)
TRAP_PENALTY_CORNER = 50.0  # 角落 (2个相邻出口)

# --- 绝对危险图常量 (保留) ---
DANGER_BULLET_PATH = 1000.0  # 绝对必杀格
DANGER_FIRE_LINE = 50.0  # 敌人潜在火力线
DANGER_ENEMY_BODY = 20.0  # 敌人身体碰撞区
BULLET_MAX_STEPS = 15  # 子弹射线计算的最大步数

# --- [新增] 攻击奖励常量 ---
ATTACK_BONUS_LOS = 200.0  # 成功命中火力线 (Line of Sight) 的奖励

# ----------------- 基本常量 -----------------
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}


# ----------------- 工具函数 -----------------
def manhattan(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])


def dir_from(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return next((k for k, v in DIRS.items() if v == (dx, dy)), None)


def is_valid(pos, w, h, walls, tanks_pos_set):
    x, y = pos
    return 0 <= x < w and 0 <= y < h and pos not in walls and pos not in tanks_pos_set


# ----------------- [已废弃] 辅助类 (ThreatField & Evaluator) -----------------
# (此类已按要求移除)

class Strategy:
    def __init__(self):
        self.mode = "balanced";
        self.last_pos = defaultdict(lambda: None)

    def update(self, hp, enemy_count, high_threat, is_stuck, enemies):
        """
        (保留)
        high_threat: bool, 是否站在高危格上 (如火力线或子弹路径)
        is_stuck: bool, 是否处于静态陷阱中 (走廊或死胡同)
        """
        self.mode = 'evasion' if hp <= 1 or high_threat or (enemy_count >= 3 and is_stuck) else \
            'aggressive' if enemy_count == 1 and hp >= 3 else 'balanced'
        for t in enemies: self.last_pos[t['name']] = (t['x'], t['y'])

    # --- [已废弃] weights (逻辑已移至 score_move) ---
    # def weights(self): ...

    def enemy_dir(self, name, pos):
        last = self.last_pos.get(name)
        if last and last != pos: return dir_from(last, pos)
        return None


# ----------------- AI 主体 -----------------
class TankAI:
    def __init__(self):
        self.strategy = Strategy()
        self.last_action = None
        self.last_pos = None
        self.last_hp = None
        self.history = deque(maxlen=8)
        self.hazard = defaultdict(int)
        self.mobility_map = None
        self.trap_map = None
        self.static_walls = None

    def _compute_mobility_map(self, w, h, walls):
        # (此函数保留不变)
        if self.static_walls == walls and self.mobility_map is not None: return
        self.static_walls = set(walls)
        self.mobility_map = [[0] * h for _ in range(w)]
        for x in range(w):
            for y in range(h):
                if (x, y) in walls: continue
                q, visited, count = deque([((x, y), 0)]), {(x, y)}, 0
                while q:
                    (cur_x, cur_y), depth = q.popleft()
                    if depth >= MOBILITY_BFS_DEPTH: continue
                    count += 1
                    for dx, dy in DIRS.values():
                        nx, ny = cur_x + dx, cur_y + dy
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls and (nx, ny) not in visited:
                            visited.add((nx, ny));
                            q.append(((nx, ny), depth + 1))
                self.mobility_map[x][y] = count

    def _compute_trap_map(self, w, h, walls_set):
        # (此函数保留不变)
        if self.static_walls == walls_set and self.trap_map is not None:
            return
        self.trap_map = [[0.0] * h for _ in range(w)]
        for x in range(w):
            for y in range(h):
                if (x, y) in walls_set:
                    continue
                valid_neighbors_dirs = []
                for d, (dx, dy) in DIRS.items():
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    if (nx, ny) in walls_set:
                        continue
                    valid_neighbors_dirs.append(d)
                num_neighbors = len(valid_neighbors_dirs)
                if num_neighbors == 1:
                    self.trap_map[x][y] = TRAP_PENALTY_DEADEND
                elif num_neighbors == 2:
                    d1, d2 = valid_neighbors_dirs
                    if d2 == OPPOSITE.get(d1):
                        self.trap_map[x][y] = TRAP_PENALTY_CORRIDOR
                    else:
                        self.trap_map[x][y] = TRAP_PENALTY_CORNER

    def calculate_absolute_danger_map(self, state, w, h, walls_set, my_name):
        # (此函数保留不变)
        danger_map = [[0.0] * h for _ in range(w)]
        bullets = state.get('bullets', [])
        tanks = state.get('tanks', [])
        enemies = [t for t in tanks if t['name'] != my_name and t['alive']]
        for b in bullets:
            if b.get('owner') == my_name:
                continue
            bx, by = b['x'], b['y']
            bdx, bdy = b['dx'], b['dy']
            for s in range(1, BULLET_MAX_STEPS + 1):
                nx, ny = bx + bdx * s * 2, by + bdy * s * 2
                if not (0 <= nx < w and 0 <= ny < h):
                    break
                if (nx, ny) in walls_set:
                    break
                danger_map[nx][ny] += DANGER_BULLET_PATH
        for t in enemies:
            tx, ty = t['x'], t['y']
            for (dx, dy) in DIRS.values():
                cx, cy = tx, ty
                while True:
                    cx += dx
                    cy += dy
                    if not (0 <= cx < w and 0 <= cy < h) or (cx, cy) in walls_set:
                        break
                    danger_map[cx][cy] += DANGER_FIRE_LINE
            danger_map[tx][ty] += DANGER_ENEMY_BODY
            for (dx, dy) in DIRS.values():
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls_set:
                    danger_map[nx][ny] += DANGER_ENEMY_BODY * 0.5
        return danger_map

    def get_action(self, state):
        # (此函数保留不变)
        me = state['self']
        w, h = state['map_width'], state['map_height']
        my_pos = (me['x'], me['y'])
        hp = me['hp']
        my_name = me['name']
        walls = set(tuple(wloc) for wloc in state.get('walls', []))
        tanks_all = state.get('tanks', [])
        tanks_alive = [t for t in tanks_all if t['alive']]
        tanks_pos_set = {(t['x'], t['y']) for t in tanks_alive}
        enemies = [t for t in tanks_all if t['name'] != my_name and t['alive']]

        if self.mobility_map is None:
            self._compute_mobility_map(w, h, walls)
        if self.trap_map is None:
            self._compute_trap_map(w, h, walls)

        danger_map = self.calculate_absolute_danger_map(state, w, h, walls, my_name)

        my_danger_level = danger_map[my_pos[0]][my_pos[1]]
        high_threat = my_danger_level >= DANGER_FIRE_LINE
        my_trap_level = self.trap_map[my_pos[0]][my_pos[1]]
        is_stuck = my_trap_level >= TRAP_PENALTY_CORRIDOR
        self.strategy.update(hp, len(enemies), high_threat, is_stuck, enemies)

        danger = danger_map

        chosen = self.get_next_best_move(state, danger, enemies, tanks_pos_set)

        final_pos_is_valid = False
        if chosen is not None:
            final_dx, final_dy = DIRS[chosen]
            final_pos = (my_pos[0] + final_dx, my_pos[1] + final_dy)
            final_pos_is_valid = is_valid(final_pos, w, h, walls, tanks_pos_set)

        if not final_pos_is_valid:
            fb = self._find_smart_fallback_move(my_pos, w, h, walls, tanks_pos_set, danger)
            chosen = fb

        return chosen

    def _find_smart_fallback_move(self, my_pos, w, h, walls, tanks_pos_set, danger):
        # (此函数保留不变)
        candidates = []
        for d in DIR_LIST:
            dx, dy = DIRS[d]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if is_valid((nx, ny), w, h, walls, tanks_pos_set):
                candidates.append(d)
        if not candidates:
            return None
        best_move = ""
        best_score = -float('inf')
        for move in candidates:
            dx, dy = DIRS[move]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            reverse_penalty = 0
            if REVERSE_FORBID and self.last_action and move == OPPOSITE.get(self.last_action):
                reverse_penalty = REVERSE_PENALTY_SCORE
            score = -danger[nx][ny] - reverse_penalty
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    # --- [已废弃] _calculate_attack_bonus (逻辑已移至 score_move) ---
    # def _calculate_attack_bonus(self, pos, enemies_list): ...

    # --- [重构] 统一的走位评分函数 ---
    def score_move(self, move, pos, enemies_list, danger_map, w, h, walls_set):
        """
        (核心请求)
        评估一个 "候选" 移动 (move) 及其目标位置 (pos) 的最终得分。
        此函数现在包含新的 LOS 攻击奖励 和 动态策略权重。
        """
        nx, ny = pos

        # --- 1. 定义进攻/机动性奖励 ---

        # 1a. 机动性奖励 (Mobility Bonus)
        # (来自 "提示词 3")：这个值越高，代表此处的“退路”越多。
        mobility_bonus = self.mobility_map[nx][ny]

        # 1b. 攻击奖励 (Attack Bonus)
        # (来自 "提示词 3")：检查这个 move 方向是否是开火方向，并能命中敌人。
        attack_bonus = 0.0
        if enemies_list:  # 仅在有敌人时才计算
            enemy_pos_set = {(t['x'], t['y']) for t in enemies_list}
            move_dir = move
            dx, dy = DIRS[move_dir]

            # 从新位置 (nx, ny) 沿着移动方向 (move_dir) 发射射线
            cx, cy = nx, ny
            while True:
                cx += dx
                cy += dy

                # 检查越界
                if not (0 <= cx < w and 0 <= cy < h):
                    break
                # 检查撞墙
                if (cx, cy) in walls_set:
                    break
                # 检查命中敌人
                if (cx, cy) in enemy_pos_set:
                    attack_bonus = ATTACK_BONUS_LOS  # 命中！
                    break

        # --- 2. 获取惩罚项 ---

        # 2a. 陷阱惩罚 (来自 "提示词 1")
        trap_penalty = self.trap_map[nx][ny]

        # 2b. 危险惩罚 (来自 "提示词 2")
        danger_penalty = danger_map[nx][ny]

        # --- 3. 根据策略模式应用权重 (核心请求) ---
        mode = self.strategy.mode
        final_score = 0.0

        if mode == 'evasion':
            # 纯粹保命：高机动性，极度规避危险，无视攻击
            final_score = (1.5 * mobility_bonus) - \
                          (10.0 * danger_penalty) - \
                          (5.0 * trap_penalty)

        elif mode == 'aggressive':
            # 激进：高攻击，轻微规避危险 (愿意换血)
            final_score = (0.5 * mobility_bonus) + \
                          (2.0 * attack_bonus) - \
                          (1.0 * danger_penalty) - \
                          (2.0 * trap_penalty)

        else:  # 'balanced' (默认)
            # 平衡：兼顾机动、攻击、安全
            final_score = (1.0 * mobility_bonus) + \
                          (1.0 * attack_bonus) - \
                          (3.0 * danger_penalty) - \
                          (3.0 * trap_penalty)

        # --- 4. 应用绝对惩罚 (Pro 规则) ---
        # (必须在所有评分之后应用，确保它总是否决反向移动)
        if REVERSE_FORBID and self.last_action and move == OPPOSITE.get(self.last_action):
            final_score -= REVERSE_PENALTY_SCORE  # 减去一个巨大值

        return final_score

    # --- 核心决策函数 (保留) ---
    def get_next_best_move(self, state, danger_map, enemies_list, tanks_pos_set):
        # (此函数保留不变, 'danger_map' 参数现在由新函数提供)
        me = state['self']
        my_pos = (me['x'], me['y'])
        w, h = state['map_width'], state['map_height']
        walls = set(tuple(wloc) for wloc in state.get('walls', []))

        # 1. 过滤
        candidates = {}
        for move, (dx, dy) in DIRS.items():
            if REVERSE_FORBID and self.last_action and move == OPPOSITE.get(self.last_action):
                continue
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if (nx, ny) in walls:
                continue
            if (nx, ny) in tanks_pos_set:
                continue
            candidates[move] = (nx, ny)

        # 2. 评分
        if not candidates:
            return None

        scored_moves = []
        for move, pos in candidates.items():
            # [修改]：传递 w, h, walls 用于 LOS 射线检测
            score = self.score_move(
                move,
                pos,
                enemies_list,
                danger_map,
                w,
                h,
                walls  # 'walls' 已经是一个 set
            )
            scored_moves.append((score, move))

        # 3. 决策
        if not scored_moves:
            return None

        best_move = max(scored_moves, key=lambda item: item[0])[1]
        return best_move

    # ----------------- 统一的规则校验器（保留） -----------------
    def validate_and_sanitize_action(self, action, state):
        # (此函数保留不变)
        me = state.get('self')
        if not me:
            return self.last_action if self.last_action in DIR_LIST else "UP"

        w, h = state['map_width'], state['map_height']
        walls = set(tuple(wloc) for wloc in state.get('walls', []))
        tanks_alive = [t for t in state.get('tanks', []) if t['alive']]
        tanks_pos_set = {(t['x'], t['y']) for t in tanks_alive}
        my_pos = (me['x'], me['y'])

        if action not in DIR_LIST:
            action = None

        non_reverse_valid = []
        for d in DIR_LIST:
            if REVERSE_FORBID and self.last_action and d == OPPOSITE.get(self.last_action):
                continue
            dx, dy = DIRS[d]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if not (0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls):
                continue
            if (nx, ny) in tanks_pos_set:
                continue
            non_reverse_valid.append(d)

        if action and action in non_reverse_valid:
            return action

        if self.last_action in DIR_LIST:
            dx, dy = DIRS[self.last_action]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls and (nx, ny) not in tanks_pos_set:
                return self.last_action

        if non_reverse_valid:
            for pref in ["UP", "LEFT", "RIGHT", "DOWN"]:
                if pref in non_reverse_valid:
                    return pref

        if self.last_action in DIR_LIST:
            return self.last_action

        for d in DIR_LIST:
            if REVERSE_FORBID and self.last_action and d == OPPOSITE.get(self.last_action):
                continue
            return d

        return "UP"


# ----------------- 管道模式主循环 -----------------
if __name__ == "__main__":
    ai = TankAI()
    if sys.version_info >= (3, 7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        state = None
        action = None

        try:
            state = json.loads(line)
            action = ai.get_action(state)
        except Exception:
            # (异常回退逻辑保留不变)
            try:
                if state is None:
                    state = json.loads(line)
                me = state['self']
                my_pos = (me['x'], me['y'])
                w = state['map_width'];
                h = state['map_height']
                walls = set(tuple(wloc) for wloc in state.get('walls', []))
                tanks_alive = [t for t in state.get('tanks', []) if t['alive']]
                tanks_pos_set = {(t['x'], t['y']) for t in tanks_alive}
                danger = [[0.0] * h for _ in range(w)]  # 使用 0 危险图
                action = ai._find_smart_fallback_move(my_pos, w, h, walls, tanks_pos_set, danger)
            except Exception:
                action = ai.last_action

        # (最终校验逻辑保留不变)
        try:
            if state is None:
                state = json.loads(line)
        except Exception:
            action = ai.last_action if ai.last_action in DIR_LIST else "UP"
            if state is None:
                print(action)
                sys.stdout.flush()
                ai.last_action = action
                continue

        action = ai.validate_and_sanitize_action(action, state)

        print(action)
        sys.stdout.flush()

        if state:
            ai.last_action = action
            if state.get('self'):
                ai.last_pos = (state['self']['x'], state['self']['y'])
                ai.last_hp = state['self']['hp']
            ai.history.append(action)