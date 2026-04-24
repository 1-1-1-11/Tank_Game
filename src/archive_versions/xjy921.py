# xjy.py
"""
Y. L. Tank Game — 改进版 AI（按路线图实现）
- 风险感知 A*（danger_map 参与代价）
- 硬性规则：禁止立即反方向、撞墙/越界视为非法
- 两步前瞻作为 A* 失败时的备援
- 性能保护：A* 展开上限、集合查找、可调常量
"""
import sys
import json
import heapq
from collections import deque, defaultdict
import time

# -----------------------------
# 参数（可调）
# -----------------------------
DEFAULT_MODE = "balanced"   # "balanced" / "aggressive" / "evasion"
FUTURE_WEIGHT = 0.4
HARD_THREAT_THRESHOLD = 22.0
REVERSE_FORBID = True
DANGER_K = 0.1
ASTAR_MAX_EXPAND = 1200
ASTAR_GOAL_RADIUS = 6       # 搜目标时的初始半径
HAZARD_MEMORY_DECAY = 6
DEBUG = False               # 在本地用 True 打开少量诊断输出（不要在 judge 中打开）

# -----------------------------
# 基本常量
# -----------------------------
DIRS = {
    "UP":    (0, -1),
    "DOWN":  (0,  1),
    "LEFT":  (-1, 0),
    "RIGHT": (1,  0),
}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}

# -----------------------------
# 工具
# -----------------------------
def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def dir_from(a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    for k,v in DIRS.items():
        if v == (dx, dy):
            return k
    return None

# -----------------------------
# 威胁场（与之前实现兼容）
# -----------------------------
class ImprovedThreatField:
    def __init__(self, w, h, walls_set):
        self.w = w; self.h = h; self.walls = walls_set
        self.cur = [[0.0]*h for _ in range(w)]
        self.fut = [[0.0]*h for _ in range(w)]

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def calculate(self, bullets, tanks, my_name):
        for x in range(self.w):
            for y in range(self.h):
                self.cur[x][y] = 0.0
                self.fut[x][y] = 0.0

        for b in bullets:
            if b.get("owner") != my_name:
                self._propagate_bullet(b, current=True)
                self._propagate_bullet(b, current=False)

        for t in tanks:
            if t.get("alive") and t.get("name") != my_name:
                self._propagate_enemy_body(t, current=True)
                self._propagate_enemy_body(t, current=False)

        for t in tanks:
            if t.get("alive") and t.get("name") != my_name:
                self._propagate_potential_fire_lines((t["x"], t["y"]))

        return self.cur, self.fut

    def _propagate_bullet(self, b, current=True):
        x, y = b["x"], b["y"]; dx, dy = b["dx"], b["dy"]
        start_step = 0 if current else 2; end_step = 3 if current else 5
        base = 15.0 if current else 10.0
        target = self.cur if current else self.fut
        for step in range(start_step, end_step):
            nx = x + dx * step * 2
            ny = y + dy * step * 2
            if (nx, ny) in self.walls: break
            if not self.in_bounds(nx, ny): break
            threat = base / (step + 1.0)
            target[nx][ny] += threat

    def _propagate_enemy_body(self, t, current=True):
        tx, ty = t["x"], t["y"]
        target = self.cur if current else self.fut
        rng = 3 if current else 4
        base = 8.0 if current else 6.0
        for dx in range(-rng, rng+1):
            for dy in range(-rng, rng+1):
                nx, ny = tx + dx, ty + dy
                if not self.in_bounds(nx, ny): continue
                d = abs(dx) + abs(dy)
                if d <= rng:
                    target[nx][ny] += base / (d + 1.0)

    def _propagate_potential_fire_lines(self, enemy_pos):
        ex, ey = enemy_pos
        base = 6.0
        for (dx, dy) in DIRS.values():
            cx, cy = ex, ey; dist = 0
            while True:
                cx += dx; cy += dy; dist += 1
                if (cx, cy) in self.walls or not self.in_bounds(cx, cy): break
                self.fut[cx][cy] += base / (dist + 0.5)

# -----------------------------
# 战术评估（保留）
# -----------------------------
class TacticalEvaluator:
    def __init__(self, w, h, walls_set):
        self.w = w; self.h = h; self.walls = walls_set

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def cover_bonus(self, x, y):
        adj = 0
        for dx,dy in DIRS.values():
            if (x+dx, y+dy) in self.walls: adj += 1
        return 0.6 * adj

    def safe_neighbors_count(self, x, y, cur_map, fut_map, threshold=12.0):
        cnt = 0
        for dx,dy in DIRS.values():
            nx, ny = x+dx, y+dy
            if self.in_bounds(nx, ny) and cur_map[nx][ny] + FUTURE_WEIGHT * fut_map[nx][ny] < threshold:
                cnt += 1
        return cnt

    def safe_area_size(self, start, cur_map, fut_map, tanks_alive, threshold=12.0, max_depth=5):
        sx, sy = start
        if cur_map[sx][sy] + FUTURE_WEIGHT * fut_map[sx][sy] >= threshold: return 0
        q = deque([(sx, sy, 0)]); seen = {(sx, sy)}; count = 1
        while q:
            x,y,d = q.popleft()
            if d >= max_depth: continue
            for dx,dy in DIRS.values():
                nx, ny = x+dx, y+dy
                if (nx, ny) in seen: continue
                if not self.in_bounds(nx, ny): continue
                if (nx, ny) in self.walls: continue
                blocked = False
                for t in tanks_alive:
                    if t["x"] == nx and t["y"] == ny and t["alive"]: blocked = True; break
                if blocked: continue
                if cur_map[nx][ny] + FUTURE_WEIGHT * fut_map[nx][ny] < threshold:
                    seen.add((nx, ny)); q.append((nx, ny, d+1)); count += 1
        return count

    def los_clear(self, a, b):
        ax, ay = a; bx, by = b
        if ax == bx:
            y1,y2 = sorted([ay,by])
            for y in range(y1+1, y2):
                if (ax, y) in self.walls: return False
            return True
        if ay == by:
            x1,x2 = sorted([ax,bx])
            for x in range(x1+1, x2):
                if (x, ay) in self.walls: return False
            return True
        return False

# -----------------------------
# 简单自适应策略
# -----------------------------
class AdaptiveStrategy:
    def __init__(self):
        self.mode = DEFAULT_MODE

    def update(self, my_hp, enemy_count, high_threat_here, escape_neighbors):
        if my_hp <= 1 or high_threat_here:
            self.mode = "evasion"
        elif enemy_count >= 3 and escape_neighbors <= 1:
            self.mode = "evasion"
        elif enemy_count == 1 and my_hp >= 3:
            self.mode = "aggressive"
        else:
            self.mode = "balanced"

    def weights(self):
        if self.mode == "evasion": return {"survival":0.85,"attack":0.15}
        if self.mode == "aggressive": return {"survival":0.45,"attack":0.55}
        return {"survival":0.65,"attack":0.35}

# -----------------------------
# 主体 AI
# -----------------------------
class ImprovedTankAI:
    def __init__(self):
        self.strategy = AdaptiveStrategy()
        self.last_action = None
        self.history = deque(maxlen=8)
        self.last_hp = None
        self.last_pos = None
        self.hazard_memory = defaultdict(int)

class TankAI(ImprovedTankAI): pass
AI = TankAI

# -----------------------------
# A*（风险感知）
# -----------------------------
def astar_path(start, goals, w, h, walls_set, tanks_alive, danger_map, forbid_reverse=None, max_expand=ASTAR_MAX_EXPAND):
    def in_bounds(x,y): return 0 <= x < w and 0 <= y < h
    def is_blocked(x,y):
        if not in_bounds(x,y): return True
        if (x,y) in walls_set: return True
        for t in tanks_alive:
            if t["x"] == x and t["y"] == y: return True
        return False

    if start in goals:
        return [start]

    open_heap = []
    gscore = {start: 0.0}
    parent = {}
    # initial heuristic: distance to nearest goal
    init_h = min(manhattan(start, gg) for gg in goals) if goals else 0
    heapq.heappush(open_heap, (init_h, 0.0, start[0], start[1]))
    closed = set()
    expands = 0

    while open_heap and expands < max_expand:
        f, g, x, y = heapq.heappop(open_heap)
        expands += 1
        cur = (x,y)
        if cur in closed: continue
        closed.add(cur)

        if cur in goals:
            # reconstruct
            path = []
            node = cur
            while node in parent:
                path.append(node)
                node = parent[node]
            path.append(start)
            path.reverse()
            return path

        for d, (dx,dy) in DIRS.items():
            nx, ny = x+dx, y+dy
            if is_blocked(nx, ny): continue
            # forbid immediate reverse
            if forbid_reverse:
                last_action, last_pos = forbid_reverse
                if last_action is not None and last_pos is not None:
                    opp = OPPOSITE.get(last_action)
                    if opp and (last_pos[0] + DIRS[opp][0], last_pos[1] + DIRS[opp][1]) == (nx, ny):
                        continue
            tentative_g = g + (1.0 + danger_map[nx][ny] )* DANGER_K
            if (nx,ny) in gscore and tentative_g >= gscore[(nx,ny)]: continue
            gscore[(nx,ny)] = tentative_g
            parent[(nx,ny)] = (x,y)
            h = min(manhattan((nx,ny), gg) for gg in goals) if goals else 0
            fval = tentative_g + h
            heapq.heappush(open_heap, (fval, tentative_g, nx, ny))
    return None

# -----------------------------
# 主逻辑（按路线图实现）
# -----------------------------
def _get_action_impl(self, state):
    me = state["self"]
    w = state["map_width"]; h = state["map_height"]
    my_name = me["name"]
    my_pos = (me["x"], me["y"]); my_hp = me["hp"]

    # normalize walls
    walls_set = set()
    if state.get("walls"):
        for wloc in state["walls"]:
            walls_set.add(tuple(wloc))

    tanks_all = state.get("tanks", [])
    tanks_alive = [t for t in tanks_all if t["alive"]]

    # hazard memory update if damaged last turn
    if self.last_hp is not None and my_hp < self.last_hp and self.last_pos is not None:
        self.hazard_memory[self.last_pos] = HAZARD_MEMORY_DECAY

    # decay hazard memory
    to_del = []
    for k in list(self.hazard_memory.keys()):
        self.hazard_memory[k] -= 1
        if self.hazard_memory[k] <= 0: to_del.append(k)
    for k in to_del: del self.hazard_memory[k]

    # threat fields
    tf = ImprovedThreatField(w, h, walls_set)
    cur_map, fut_map = tf.calculate(state.get("bullets", []), tanks_all, my_name)
    te = TacticalEvaluator(w, h, walls_set)

    high_threat_here = cur_map[my_pos[0]][my_pos[1]] + FUTURE_WEIGHT * fut_map[my_pos[0]][my_pos[1]] > 18.0
    escape_neighbors = te.safe_neighbors_count(my_pos[0], my_pos[1], cur_map, fut_map, threshold=12.0)
    enemy_count = len([t for t in tanks_all if t["alive"] and t["name"] != my_name])
    self.strategy.update(my_hp, enemy_count, high_threat_here, escape_neighbors)
    weights = self.strategy.weights()

    # build danger_map
    danger_map = [[0.0]*h for _ in range(w)]
    for x in range(w):
        for y in range(h):
            base = cur_map[x][y] + FUTURE_WEIGHT * fut_map[x][y]
            if (x,y) in self.hazard_memory:
                base += 6.0 + self.hazard_memory[(x,y)]
            danger_map[x][y] = base

    # helper validators (fast)
    tanks_pos_set = {(t["x"], t["y"]) for t in tanks_alive}
    def in_bounds(x,y): return 0 <= x < w and 0 <= y < h
    def is_valid_target(px,py):
        if not in_bounds(px,py): return False
        if (px,py) in walls_set: return False
        if (px,py) in tanks_pos_set: return False
        return True

    # choose goals
    goals = set()
    if self.strategy.mode == "aggressive" and enemy_count > 0:
        # add enemy-adjacent valid cells
        for t in tanks_all:
            if not t["alive"] or t["name"] == my_name: continue
            ex, ey = t["x"], t["y"]
            for dx, dy in DIRS.values():
                gx, gy = ex+dx, ey+dy
                if is_valid_target(gx, gy): goals.add((gx, gy))
    # otherwise find low-danger safe cells within radius
    if not goals:
        R = ASTAR_GOAL_RADIUS
        for dx in range(-R, R+1):
            for dy in range(-R, R+1):
                gx, gy = my_pos[0]+dx, my_pos[1]+dy
                if not is_valid_target(gx, gy): continue
                if danger_map[gx][gy] < HARD_THREAT_THRESHOLD - 2.0:
                    goals.add((gx, gy))
    if not goals:
        R2 = ASTAR_GOAL_RADIUS * 2
        for dx in range(-R2, R2+1):
            for dy in range(-R2, R2+1):
                gx, gy = my_pos[0]+dx, my_pos[1]+dy
                if is_valid_target(gx, gy): goals.add((gx, gy))
    if not goals:
        # fallback neighbor cells
        for d in DIR_LIST:
            dx, dy = DIRS[d]; nx, ny = my_pos[0]+dx, my_pos[1]+dy
            if is_valid_target(nx, ny): goals.add((nx, ny))

    # run A*
    forbid_reverse = (self.last_action, self.last_pos) if REVERSE_FORBID else None
    t0 = time.time()
    path = astar_path(my_pos, goals, w, h, walls_set, tanks_alive, danger_map, forbid_reverse=forbid_reverse)
    t1 = time.time()
    if DEBUG: print("A* time:", round((t1-t0)*1000,2), "ms", "path_len:", len(path) if path else None)

    chosen = None
    if path and len(path) >= 2:
        next_cell = path[1]
        chosen = dir_from(my_pos, next_cell)
    else:
        # A* 失败 -> 备援评分器（两步）
        candidates = []
        for d in DIR_LIST:
            dx,dy = DIRS[d]; nx,ny = my_pos[0]+dx, my_pos[1]+dy
            if not is_valid_target(nx,ny): continue
            if REVERSE_FORBID and self.last_action is not None and d == OPPOSITE.get(self.last_action): continue
            if danger_map[nx][ny] >= HARD_THREAT_THRESHOLD: continue
            candidates.append((d,(nx,ny)))
        if not candidates:
            for d in DIR_LIST:
                dx,dy = DIRS[d]; nx,ny = my_pos[0]+dx, my_pos[1]+dy
                if is_valid_target(nx,ny): candidates.append((d,(nx,ny)))
        # scoring
        def attack_value_at(pos, move_dir):
            x,y = pos; val = 0.0
            for t in tanks_all:
                if not t["alive"] or t["name"] == my_name: continue
                ex,ey = t["x"], t["y"]; d = abs(ex-x)+abs(ey-y)
                if d <= 6:
                    base = 14.0/(d+1.0)
                    if t["hp"]<=1: base += 12.0
                    elif t["hp"]==2: base += 4.0
                    val += base
            dx,dy = DIRS[move_dir]; cx,cy = x,y; dist=0
            while True:
                cx+=dx; cy+=dy; dist+=1
                if (cx,cy) in walls_set or not in_bounds(cx,cy): break
                for t in tanks_all:
                    if t["alive"] and t["name"]!=my_name and t["x"]==cx and t["y"]==cy:
                        bonus = 16.0/(dist+0.5)
                        if t["hp"]<=1: bonus += 10.0
                        val += bonus; break
            return val

        def survival_penalty(pos):
            x,y = pos; mix = cur_map[x][y] + FUTURE_WEIGHT * fut_map[x][y]
            if mix > 22.0: base = 40.0 + (mix - 22.0)*2.0
            else: base = mix * 1.2
            esc = te.safe_neighbors_count(x,y,cur_map,fut_map,threshold=12.0)
            if esc <= 1: base += 8.0
            if (x,y) in self.hazard_memory: base += 6.0
            base -= te.cover_bonus(x,y) * 0.8
            return max(0.0, base)

        def mobility_bonus(pos):
            size = te.safe_area_size(pos, cur_map, fut_map, tanks_alive, threshold=12.0, max_depth=8)
            return min(10.0, size * 0.6)

        best_score = -1e18; best_dir = None
        for d,p in candidates:
            a = attack_value_at(p,d); s = survival_penalty(p); m = mobility_bonus(p)
            loop_pen = 0.0
            if len(self.history) >= 1:
                last = self.history[-1]; opp = OPPOSITE.get(last)
                if d == opp: loop_pen += 3.5
            if self.last_action is not None and d == self.last_action: loop_pen += 1.5
            score = weights["attack"] * a - weights["survival"] * s + 0.7 * m - loop_pen
            if score > best_score: best_score = score; best_dir = d
        chosen = best_dir if best_dir else (self.last_action if self.last_action else "UP")

    # final safety check before returning (double insurance)
    dx,dy = DIRS[chosen]; tx,ty = my_pos[0]+dx, my_pos[1]+dy
    if not is_valid_target(tx,ty) or (REVERSE_FORBID and self.last_action is not None and chosen == OPPOSITE.get(self.last_action)):
        fixed = None
        for d in DIR_LIST:
            dx,dy = DIRS[d]; nx,ny = my_pos[0]+dx, my_pos[1]+dy
            if is_valid_target(nx,ny) and not (REVERSE_FORBID and self.last_action is not None and d==OPPOSITE.get(self.last_action)):
                fixed = d; break
        chosen = fixed if fixed else (self.last_action if self.last_action else "UP")

    # update memory + history
    self.last_action = chosen; self.last_pos = my_pos; self.last_hp = my_hp
    self.history.append(chosen)
    return chosen

# bind
TankAI.get_action = _get_action_impl
ImprovedTankAI.get_action = _get_action_impl

# -----------------------------
# 管道模式（stdin/stdout）
# -----------------------------
def main_loop():
    ai = TankAI()
    if sys.version_info >= (3,7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    while True:
        line = sys.stdin.readline()
        if not line: break
        try:
            state = json.loads(line)
            action = ai.get_action(state)
            print(action); sys.stdout.flush()
        except Exception:
            print("UP"); sys.stdout.flush()

if __name__ == "__main__":
    main_loop()
