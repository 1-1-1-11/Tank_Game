import sys, json
from collections import deque

# ================= V1 CONFIG (保持原味) =================
SCORE_SURVIVAL = 0.0
SCORE_SUICIDE = -99999.0  # 必死操作（撞墙、反向、撞现有子弹）

# [动态战术评分]
BASE_TRADE_PENALTY = -2000.0

# [危险感知]
POTENTIAL_AIM_PENALTY = 200.0  # 处于敌人枪口下的风险
TRAP_PENALTY = 10000.0  # 死胡同（V1的核心避险逻辑）

# [奖励]
MOBILITY_WEIGHT = 15.0  # 移动空间权重
AIM_BONUS = 150.0  # 瞄准敌人奖励
POSITION_BONUS = 5.0  # 控图奖励

# [基础常量]
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}


class TankAI:
    def __init__(self):
        self.last_action = None
        self.was_alive = False
        self.static_walls = None
        self.mobility_map = None
        self.trap_lookup = {}
        self._dfs_memo = {}

        # [新增] 图5 专用标记
        self.is_spiral_map = False

        # --- 1. 静态地图分析 (V1逻辑 + 螺旋检测) ---

    def _rebuild_static_maps(self, w, h, walls):
        self.static_walls = walls

        # === V1 原有逻辑 ===
        self.mobility_map = [[0] * h for _ in range(w)]
        self.trap_lookup = {}

        for x in range(w):
            for y in range(h):
                if (x, y) not in walls:
                    self.mobility_map[x][y] = self._bfs_mobility((x, y), w, h, walls)

        self._dfs_memo = {}
        for x in range(w):
            for y in range(h):
                if (x, y) in walls: continue
                for move in DIR_LIST:
                    # V1 的陷阱检测：深度15，判断是否进死胡同
                    if not self._can_escape_dfs((x, y), move, w, h, walls, set(), 0, max_depth=15):
                        self.trap_lookup[((x, y), move)] = True

        # === [新增] 螺旋地图检测 (基于拓扑剥离) ===
        self._check_if_spiral(w, h, walls)

    def _check_if_spiral(self, w, h, walls):
        """
        判断是否为图5那种全图死路。
        方法：剥洋葱算法。如果剥完所有死胡同后，地图上没有剩下的点（没有环），
        说明这是一张全死路地图（螺旋图）。
        """
        degree = {}
        graph = {}
        for x in range(w):
            for y in range(h):
                if (x, y) not in walls:
                    neighbors = []
                    for dx, dy in DIRS.values():
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls:
                            neighbors.append((nx, ny))
                    graph[(x, y)] = neighbors
                    degree[(x, y)] = len(neighbors)

        # 移除度数<=1的点（死胡同），直到不能移除
        queue = deque([n for n, d in degree.items() if d <= 1])
        removed = set()
        while queue:
            u = queue.popleft()
            if u in removed: continue
            removed.add(u)
            if u in graph:
                for v in graph[u]:
                    if v not in removed:
                        degree[v] -= 1
                        if degree[v] == 1:
                            queue.append(v)

        # 如果所有空格子都被移除了，说明全图都是死路 -> 螺旋模式开启
        # 为了容错，如果剩余节点极少(<2)，也视为螺旋
        total_free = len(graph)
        remaining = total_free - len(removed)

        if remaining < 2:
            self.is_spiral_map = True
        else:
            self.is_spiral_map = False

    # --- V1 辅助函数 ---
    def _bfs_mobility(self, start, w, h, walls):
        q = deque([(start, 0)])
        visited = {start}
        cnt = 0
        while q:
            curr, d = q.popleft()
            if d >= 6: continue
            cnt += 1
            for dx, dy in DIRS.values():
                nx, ny = curr[0] + dx, curr[1] + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    q.append(((nx, ny), d + 1))
        return cnt

    def _can_escape_dfs(self, pos, last_move, w, h, walls, visiting, depth, max_depth=15):
        state = (pos, last_move)
        # 1. 记忆化剪枝：如果该状态（位置+来源方向）之前算过，直接查表返回结果
        if state in self._dfs_memo:
            return self._dfs_memo[state]
        # 2. 环路检测：如果在当前递归路径中又回到了自己，说明有环路，视为可无限生存
        if state in visiting:
            return True
        # 3. 深度截止：如果递归超过最大步数（例如15步）还没有撞墙，视为进入开阔地（安全）
        if depth > max_depth:
            return True
        # 标记当前节点正在访问中（防止成环死循环）
        visiting.add(state)
        can_escape = False
        rev = OPPOSITE.get(last_move)  # 获取反方向，防止AI走“回头路”
        for move, (dx, dy) in DIRS.items():
            if move == rev: continue  # 规则：不能立刻掉头
            nx, ny = pos[0] + dx, pos[1] + dy
            # 检查边界与撞墙
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls:
                # 递归：只要有一个邻居能通向逃生之路，当前点就算安全 (OR逻辑)
                if self._can_escape_dfs((nx, ny), move, w, h, walls, visiting, depth + 1, max_depth):
                    can_escape = True
                    break
        # 回溯：移除当前节点的访问标记，方便其他路径再次访问
        visiting.remove(state)
        # 记录计算结果到缓存，供下次直接使用
        self._dfs_memo[state] = can_escape
        return can_escape
    # ---  图5 专用生存计算  ---
    def _get_spiral_survival_steps(self, start_pos, first_move, w, h, walls):
        """
        DFS 暴力搜索：如果我往这边走，最多能活多少步？
        """
        max_depth = 0
        # 栈元素: (pos, last_move, depth, visited_set)
        # 注意：这里不用回溯 visited，因为是找单条最长路径，且不反向
        stack = [(start_pos, first_move, 0, {start_pos})]
        LIMIT = 60  # 螺旋图很长，稍微看远点

        while stack:
            curr, last_move, depth, visited = stack.pop()
            if depth > max_depth: max_depth = depth
            if depth >= LIMIT: continue

            rev = OPPOSITE.get(last_move)
            for move, (dx, dy) in DIRS.items():
                if move == rev: continue
                nx, ny = curr[0] + dx, curr[1] + dy

                if 0 <= nx < w and 0 <= ny < h and \
                        (nx, ny) not in walls and \
                        (nx, ny) not in visited:
                    new_visited = visited.copy()
                    new_visited.add((nx, ny))
                    stack.append(((nx, ny), move, depth + 1, new_visited))

        return max_depth

    # --- 物理碰撞逻辑 ---
    def _will_hit_bullet(self, next_pos, state, my_name):
        nx, ny = next_pos
        w, h = state['map_width'], state['map_height']
        walls = set(tuple(p) for p in state['walls'])

        for b in state.get('bullets', []):
            if b['owner'] == my_name: continue

            bx, by = b['x'], b['y']
            bdx, bdy = b['dx'], b['dy']

            # Step 1
            s1_x, s1_y = bx + bdx, by + bdy
            if not (0 <= s1_x < w and 0 <= s1_y < h) or (s1_x, s1_y) in walls: continue
            if (s1_x, s1_y) == (nx, ny): return True

            # Step 2
            s2_x, s2_y = s1_x + bdx, s1_y + bdy
            if not (0 <= s2_x < w and 0 <= s2_y < h) or (s2_x, s2_y) in walls: continue
            if (s2_x, s2_y) == (nx, ny): return True

        return False

    def _get_enemy_threat_map(self, state, w, h, walls, my_name):
        threat_map = [[0.0] * h for _ in range(w)]
        enemies = [t for t in state['tanks'] if t['name'] != my_name and t['alive']]

        for e in enemies:
            ex, ey = e['x'], e['y']
            for move in DIR_LIST:
                dx, dy = DIRS[move]
                cx, cy = ex + dx, ey + dy
                dist = 0
                while 0 <= cx < w and 0 <= cy < h and dist < 6:
                    if (cx, cy) in walls: break
                    threat_map[cx][cy] += POTENTIAL_AIM_PENALTY
                    cx += dx
                    cy += dy
                    dist += 1
        return threat_map

    def _get_aim_bonus(self, my_pos, move, enemies_pos_set, w, h, walls):
        dx, dy = DIRS[move]
        cx, cy = my_pos[0] + dx * 2, my_pos[1] + dy * 2
        found_target = False
        dist = 0
        while 0 <= cx < w and 0 <= cy < h and dist < 10:
            if (cx, cy) in walls: break
            if (cx, cy) in enemies_pos_set:
                found_target = True
                break
            cx += dx
            cy += dy
            dist += 1
        return AIM_BONUS if found_target else 0

    # ================= 主决策循环 =================
    def get_action(self, state):
        try:
            me = state['self']
            if not self.was_alive and me['alive']: self.last_action = None
            self.was_alive = me['alive']
            if not me['alive']: return "UP"

            w, h = state['map_width'], state['map_height']
            walls = set(tuple(p) for p in state['walls'])
            my_pos = (me['x'], me['y'])

            enemies_list = [t for t in state['tanks'] if t['name'] != me['name'] and t['alive']]
            enemies_pos = {(t['x'], t['y']) for t in enemies_list}

            # 重建地图 + 检测是否为螺旋图
            if self.static_walls != walls: self._rebuild_static_maps(w, h, walls)

            threat_map = self._get_enemy_threat_map(state, w, h, walls, me['name'])

            candidates = []

            for move in DIR_LIST:
                dx, dy = DIRS[move]
                nx, ny = my_pos[0] + dx, my_pos[1] + dy

                score = SCORE_SURVIVAL

                # --- 1. 绝对规则 (V1 基础) ---
                is_out = not (0 <= nx < w and 0 <= ny < h)
                is_wall = (nx, ny) in walls
                is_reverse = (self.last_action and move == OPPOSITE.get(self.last_action))

                if is_out or is_wall or is_reverse:
                    score += SCORE_SUICIDE  # 必死
                else:
                    # --- 2. 物理级躲避 (V1 核心) ---
                    # 无论什么图，都不能撞子弹
                    if self._will_hit_bullet((nx, ny), state, me['name']):
                        score += SCORE_SUICIDE + 1

                        # --- 3. 策略分支 ---
                    elif self.is_spiral_map:
                        # [螺旋图专用逻辑]
                        # 忽略所有 trap 判定（因为全是 trap），只看哪条路最长
                        steps = self._get_spiral_survival_steps((nx, ny), move, w, h, walls)
                        score += steps * 1000.0  # 步数即正义

                    else:
                        # [常规图逻辑 - 完全沿用 V1]

                        # 撞人博弈
                        if (nx, ny) in enemies_pos:
                            target_hp = 3
                            for e in enemies_list:
                                if e['x'] == nx and e['y'] == ny: target_hp = e['hp']; break
                            if me['hp'] > target_hp:
                                score += 500.0
                            elif me['hp'] == target_hp:
                                score += BASE_TRADE_PENALTY
                            else:
                                score += SCORE_SUICIDE
                        else:
                            # 宏观评分
                            if self.trap_lookup.get(((nx, ny), move), False):
                                score -= TRAP_PENALTY  # V1 的核心：死胡同回避

                            score -= threat_map[nx][ny]

                            if score > -5000:
                                score += self.mobility_map[nx][ny] * MOBILITY_WEIGHT
                                score -= (abs(nx - w // 2) + abs(ny - h // 2)) * POSITION_BONUS
                                score += self._get_aim_bonus((nx, ny), move, enemies_pos, w, h, walls)
                                if self.last_action == move: score += 5.0

                candidates.append((score, move))

            # 排序决策
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_move = candidates[0][1]

            self.last_action = best_move
            return best_move

        except Exception:
            return "UP"


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