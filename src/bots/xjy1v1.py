import sys, json
from collections import deque

# ================= CONFIG =================
# [死亡价值链]
SCORE_SURVIVAL = 0.0
SCORE_TRADE_LIVES = -5000.0
SCORE_SUICIDE = -99999.0

# [战术评分]
MOBILITY_WEIGHT = 10.0  # 空间权重
DANGER_PENALTY = 5000.0  # 潜在危险区域（未来几帧可能被打中）
TRAP_PENALTY = 20000.0  # 死胡同
AIM_BONUS = 50.0  # 进攻奖励
CIRCLE_BONUS = 8.0  # 螺旋走位奖励

# [基础常量]
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
CLOCKWISE_NEXT = {'UP': 'RIGHT', 'RIGHT': 'DOWN', 'DOWN': 'LEFT', 'LEFT': 'UP'}


class TankAI:
    def __init__(self):
        self.last_action = None
        self.was_alive = False
        self.static_walls = None
        self.mobility_map = None
        self.trap_lookup = {}
        self._dfs_memo = {}

    # --- 1. 静态分析 (保持不变) ---
    def _rebuild_static_maps(self, w, h, walls):
        self.static_walls = walls
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
                    if not self._can_escape_dfs((x, y), move, w, h, walls, set(), 0):
                        self.trap_lookup[((x, y), move)] = True

    def _bfs_mobility(self, start, w, h, walls):
        q = deque([(start, 0)]);
        visited = {start};
        cnt = 0
        while q:
            curr, d = q.popleft()
            if d >= 8: continue
            cnt += 1
            for dx, dy in DIRS.values():
                nx, ny = curr[0] + dx, curr[1] + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls and (nx, ny) not in visited:
                    visited.add((nx, ny));
                    q.append(((nx, ny), d + 1))
        return cnt

    def _can_escape_dfs(self, pos, last_move, w, h, walls, visiting, depth):
        state = (pos, last_move)
        if state in self._dfs_memo: return self._dfs_memo[state]
        if state in visiting: return True
        if depth > 60: return True
        visiting.add(state);
        can_escape = False
        rev = OPPOSITE.get(last_move)
        for move, (dx, dy) in DIRS.items():
            if move == rev: continue
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls:
                if self._can_escape_dfs((nx, ny), move, w, h, walls, visiting, depth + 1):
                    can_escape = True;
                    break
        visiting.remove(state);
        self._dfs_memo[state] = can_escape
        return can_escape

    # --- 2. 物理级子弹判定 (新增核心) ---
    def _will_hit_bullet(self, next_pos, state, my_name):
        """
        精确计算下一帧我移动到 next_pos 时，是否会被场上任何子弹击中。
        考虑子弹速度=2，即子弹会覆盖其路径上的 2 个格子。
        """
        nx, ny = next_pos
        w, h = state['map_width'], state['map_height']
        walls = set(tuple(p) for p in state['walls'])

        for b in state.get('bullets', []):
            if b['owner'] == my_name: continue  # 忽略自己的子弹(假设不会打中自己，或者还没飞回来)

            bx, by = b['x'], b['y']
            bdx, bdy = b['dx'], b['dy']

            # 模拟子弹接下来的两步 (每帧移动两次)
            # 第一步
            s1_x, s1_y = bx + bdx, by + bdy
            if not (0 <= s1_x < w and 0 <= s1_y < h) or (s1_x, s1_y) in walls:
                continue  # 子弹撞墙销毁，安全

            if (s1_x, s1_y) == (nx, ny):
                return True  # 第一步就撞上我

            # 第二步
            s2_x, s2_y = s1_x + bdx, s1_y + bdy
            if not (0 <= s2_x < w and 0 <= s2_y < h) or (s2_x, s2_y) in walls:
                continue

            if (s2_x, s2_y) == (nx, ny):
                return True  # 第二步撞上我

        return False

    def _get_danger_map(self, state, w, h, walls, my_name):
        # 这是一个宏观的危险图，用于“不要走进枪线”，区别于上面的“下一帧必死判定”
        dmap = [[0.0] * h for _ in range(w)]
        for b in state.get('bullets', []):
            if b['owner'] == my_name: continue
            bx, by, bdx, bdy = b['x'], b['y'], b['dx'], b['dy']
            cx, cy = bx, by
            while 0 <= cx < w and 0 <= cy < h:
                if (cx, cy) in walls: break
                dmap[cx][cy] += DANGER_PENALTY
                cx += bdx;
                cy += bdy
        return dmap

    def _get_aim_value(self, my_pos, move, enemies, w, h, walls):
        dx, dy = DIRS[move]
        cx, cy = my_pos[0] + dx, my_pos[1] + dy
        while 0 <= cx < w and 0 <= cy < h:
            if (cx, cy) in walls: return 0
            if (cx, cy) in enemies: return AIM_BONUS
            cx += dx;
            cy += dy
        return 0

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
            enemies = {(t['x'], t['y']) for t in state['tanks'] if t['name'] != me['name'] and t['alive']}

            if self.static_walls != walls: self._rebuild_static_maps(w, h, walls)
            danger_map = self._get_danger_map(state, w, h, walls, me['name'])

            candidates = []
            for move in DIR_LIST:
                dx, dy = DIRS[move]
                nx, ny = my_pos[0] + dx, my_pos[1] + dy

                score = SCORE_SURVIVAL

                # [1. 绝对规则判断]
                is_out = not (0 <= nx < w and 0 <= ny < h)
                is_wall = (nx, ny) in walls
                is_reverse = (self.last_action and move == OPPOSITE.get(self.last_action))

                if is_out or is_wall or is_reverse:
                    score += SCORE_SUICIDE
                else:
                    # [2. 物理生存判断 (Fix: 2x Speed Check)]
                    # 如果这一步走过去，会被子弹的第一步或第二步击中，视为必死
                    if self._will_hit_bullet((nx, ny), state, me['name']):
                        score += SCORE_SUICIDE  # 这里不是Penalty，是直接判死刑

                    # 撞人判断
                    elif (nx, ny) in enemies:
                        score += SCORE_TRADE_LIVES

                    else:
                        # [3. 宏观生存评分]
                        if danger_map[nx][ny] > 0: score -= danger_map[nx][ny]
                        if self.trap_lookup.get(((nx, ny), move), False): score -= TRAP_PENALTY

                        # [4. 战术价值]
                        if score > -100:
                            score += self._get_aim_value((nx, ny), move, enemies, w, h, walls)
                            score += self.mobility_map[nx][ny] * MOBILITY_WEIGHT
                            if self.last_action and move == CLOCKWISE_NEXT.get(self.last_action):
                                score += CIRCLE_BONUS

                candidates.append((score, move))

            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

        except Exception:
            return "UP"


if __name__ == "__main__":
    ai = TankAI()
    if sys.version_info >= (3, 7):
        try:
            sys.stdin.reconfigure(encoding='utf-8'); sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    while True:
        line = sys.stdin.readline()
        if not line: break
        try:
            state = json.loads(line)
            action = ai.get_action(state)
            print(action);
            sys.stdout.flush()
            ai.last_action = action
        except:
            print("UP");
            sys.stdout.flush()