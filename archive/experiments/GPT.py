import sys
import json
from collections import deque

# ================= 配置常量 =================
# 评分系统
SCORE_INVALID = -float('inf')  # 绝对不可行的操作（撞墙、反向）
SCORE_BULLET_HIT = -100000.0  # 被子弹击中（极度危险，但优于立即撞墙）
SCORE_TRAP_BASE = -50000.0  # 陷入死胡同的基础惩罚

# 奖励系数
WEIGHT_SURVIVAL_DEPTH = 1000.0  # 在死胡同里，每多活一步的价值
WEIGHT_MOBILITY = 10.0  # 自由度权重
WEIGHT_CENTER = 2.0  # 控图权重（靠近中心）
WEIGHT_AIM = 50.0  # 瞄准敌人奖励
WEIGHT_CONTINUITY = 5.0  # 保持方向奖励（减少抖动）

# 基础方向
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}


class TankAI:
    def __init__(self):
        self.last_action = None
        self.was_alive = False

        # 缓存数据
        self.map_w = 0
        self.map_h = 0
        self.walls = set()
        self.static_map_initialized = False

        # 记忆化搜索缓存 (每一帧清空或复用)
        self.memo_depth = {}

    def _reset_state(self):
        """复活时重置状态，防止Pro规则误判"""
        self.last_action = None
        self.memo_depth = {}

    def _update_static_map(self, w, h, walls_list):
        """仅当地图变化时更新静态信息"""
        current_walls = set(tuple(p) for p in walls_list)
        if (self.map_w == w and self.map_h == h and
                self.walls == current_walls and self.static_map_initialized):
            return

        self.map_w = w
        self.map_h = h
        self.walls = current_walls
        self.static_map_initialized = True

    # ================= 核心物理判定 =================

    def _is_valid_move(self, x, y, move, check_reverse=True):
        """检查动作是否符合 Pro 规则（不撞墙、不越界、不反向）"""
        # 1. 检查越界
        if not (0 <= x < self.map_w and 0 <= y < self.map_h):
            return False

        # 2. 检查撞墙
        if (x, y) in self.walls:
            return False

        # 3. 检查反向 (Pro规则)
        if check_reverse and self.last_action:
            if move == OPPOSITE.get(self.last_action):
                return False

        return True

    def _will_hit_bullet(self, my_next_pos, bullets, my_name):
        """
        精准子弹判定：
        1. 子弹速度为2，分两步检测。
        2. 考虑墙壁遮挡：如果子弹第一步撞墙，它就消失了，不会进行第二步判定。
        """
        mx, my = my_next_pos

        for b in bullets:
            if b['owner'] == my_name: continue

            bx, by = b['x'], b['y']
            dx, dy = b['dx'], b['dy']

            # --- 子弹第 1 步 ---
            s1_x, s1_y = bx + dx, by + dy
            # 如果子弹越界或撞墙，这颗子弹销毁，不再造成威胁
            if not (0 <= s1_x < self.map_w and 0 <= s1_y < self.map_h) or (s1_x, s1_y) in self.walls:
                continue

            # 如果子弹第1步撞到我
            if (s1_x, s1_y) == (mx, my):
                return True

            # --- 子弹第 2 步 ---
            s2_x, s2_y = s1_x + dx, s1_y + dy
            # 同理，检查第2步是否被墙挡住
            if not (0 <= s2_x < self.map_w and 0 <= s2_y < self.map_h) or (s2_x, s2_y) in self.walls:
                continue

            # 如果子弹第2步撞到我
            if (s2_x, s2_y) == (mx, my):
                return True

        return False

    # ================= 绝境寻路算法 (DFS Longest Path) =================

    def _get_survival_depth(self, start_pos, start_move, max_depth=20):
        """
        计算从 (start_pos) 开始，按照 start_move 走，最多能活多少步。
        用于：螺旋地图、死胡同、被包围时的最优解选择。
        """
        # 栈结构: (x, y, last_move, current_depth, visited_set)
        # 为了性能，visited 使用 frozenset 或路径列表
        # 这里为了速度，只记录当前路径上的点避免回环

        stack = [(start_pos, start_move, 0, {start_pos})]
        max_survival = 0

        while stack:
            (cx, cy), l_move, depth, visited = stack.pop()

            if depth > max_survival:
                max_survival = depth

            # 剪枝：如果已经够深了，不需要无限算下去
            if depth >= max_depth:
                return max_depth

            rev = OPPOSITE.get(l_move)

            # 尝试所有方向
            can_move = False
            for move, (dx, dy) in DIRS.items():
                if move == rev: continue  # 不反向

                nx, ny = cx + dx, cy + dy

                # 基础物理检查
                if not (0 <= nx < self.map_w and 0 <= ny < self.map_h): continue
                if (nx, ny) in self.walls: continue
                if (nx, ny) in visited: continue  # 不走回头路 (避免死循环)

                # 放入栈
                # 注意：这里需要复制 visited 集合，虽然慢一点但在复杂死路中是必须的
                new_visited = visited.copy()
                new_visited.add((nx, ny))
                stack.append(((nx, ny), move, depth + 1, new_visited))
                can_move = True

            if not can_move:
                # 死路
                pass

        return max_survival

    # ================= 战术辅助 =================

    def _bfs_mobility(self, start_pos):
        """计算当前位置的机动性（BFS扩散格数）"""
        q = deque([(start_pos, 0)])
        visited = {start_pos}
        count = 0
        limit = 8  # 只看附近8步

        while q:
            curr, d = q.popleft()
            if d >= limit: continue

            count += 1
            for dx, dy in DIRS.values():
                nx, ny = curr[0] + dx, curr[1] + dy
                if 0 <= nx < self.map_w and 0 <= ny < self.map_h and \
                        (nx, ny) not in self.walls and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    q.append(((nx, ny), d + 1))
        return count

    def _is_aiming_enemy(self, my_pos, move, enemies_pos):
        """简单的瞄准判定"""
        dx, dy = DIRS[move]
        cx, cy = my_pos[0] + dx, my_pos[1] + dy
        # 也是要检测墙壁遮挡
        dist = 0
        while 0 <= cx < self.map_w and 0 <= cy < self.map_h and dist < 10:
            if (cx, cy) in self.walls: return False
            if (cx, cy) in enemies_pos: return True
            cx += dx
            cy += dy
            dist += 1
        return False

    # ================= 主逻辑 =================

    def get_action(self, state):
        try:
            me = state['self']

            # 1. 状态监测与重置 (Requirement 4)
            if not me['alive']:
                self.was_alive = False
                return "UP"  # 死了随便回

            if not self.was_alive and me['alive']:
                # 刚复活
                self._reset_state()

            self.was_alive = True

            # 2. 更新环境
            self._update_static_map(state['map_width'], state['map_height'], state['walls'])

            my_x, my_y = me['x'], me['y']
            my_pos = (my_x, my_y)
            bullets = state['bullets']

            enemies = [t for t in state['tanks'] if t['name'] != me['name'] and t['alive']]
            enemies_pos = {(t['x'], t['y']) for t in enemies}

            candidates = []

            # 3. 遍历所有动作并评分
            for move in DIR_LIST:
                dx, dy = DIRS[move]
                nx, ny = my_x + dx, my_y + dy

                score = 0.0

                # --- [Tier 1] 绝对规则判定 (Requirement 1) ---
                if not self._is_valid_move(nx, ny, move, check_reverse=True):
                    # 记录为负无穷，直接丢弃
                    score = SCORE_INVALID
                    candidates.append((score, move))
                    continue

                # --- [Tier 2] 物理生存判定 (Requirement 3) ---
                # 检查子弹 (考虑墙壁遮挡的精准判定)
                if self._will_hit_bullet((nx, ny), bullets, me['name']):
                    score += SCORE_BULLET_HIT  # 既然不得不死，选这条也行，但尽量别选

                # --- [Tier 3] 绝境长路径判定 (Requirement 2) ---
                # 无论是不是螺旋图，都计算一下如果不回头能活多久
                # 如果这个值很小，说明进入了死胡同
                survival_steps = self._get_survival_depth((nx, ny), move, max_depth=15)

                if survival_steps < 15:
                    # 说明进入了死胡同或封闭空间
                    # 此时评分主要由 survival_steps 决定
                    # 公式：基础负分 + 活得越久分越高
                    score += SCORE_TRAP_BASE + (survival_steps * WEIGHT_SURVIVAL_DEPTH)
                else:
                    # --- [Tier 4] 常规战术评分 ---
                    # 既然不是死路，就看战术价值

                    # A. 撞人判定 (简单的博弈)
                    if (nx, ny) in enemies_pos:
                        # 简化：撞人通常不好，除非不得不
                        score -= 500.0

                    # B. 机动性 (BFS)
                    mobility = self._bfs_mobility((nx, ny))
                    score += mobility * WEIGHT_MOBILITY

                    # C. 控图 (靠近中心)
                    dist_center = abs(nx - self.map_w // 2) + abs(ny - self.map_h // 2)
                    score -= dist_center * WEIGHT_CENTER

                    # D. 进攻
                    if self._is_aiming_enemy((nx, ny), move, enemies_pos):
                        score += WEIGHT_AIM

                    # E. 惯性 (防止原地抖动)
                    if self.last_action == move:
                        score += WEIGHT_CONTINUITY

                candidates.append((score, move))

            # 4. 决策输出
            # 按分数降序排列
            candidates.sort(key=lambda x: x[0], reverse=True)

            best_score, best_move = candidates[0]

            # 如果最高分都是 INVALID (实际上不可能，除非被卡死在墙里)，防止崩溃
            if best_score == SCORE_INVALID:
                # 这种情况下，尝试不做反向检查，只求不撞墙
                for move in DIR_LIST:
                    dx, dy = DIRS[move]
                    nx, ny = my_x + dx, my_y + dy
                    if self._is_valid_move(nx, ny, move, check_reverse=False):
                        best_move = move
                        break

            self.last_action = best_move
            return best_move

        except Exception as e:
            # 最终兜底，防止报错被判负
            # 这里的兜底尽量保持不动或向上，避免报错导致 crash
            return "UP"


# 标准输入输出接口
if __name__ == "__main__":
    ai = TankAI()
    if sys.version_info >= (3, 7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    while True:
        line = sys.stdin.readline()
        if not line: break
        try:
            state = json.loads(line)
            action = ai.get_action(state)
            print(action)
            sys.stdout.flush()
        except:
            print("UP")
            sys.stdout.flush()