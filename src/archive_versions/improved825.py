
"""
improved_ai.py
====================
改进版坦克AI - 多步预测 + 战术视野 + 自适应
- 符合 README 的 AI 接口（提供 TankAI 类）
- 同时兼容管道模式（stdin 输入 state，stdout 输出方向）
"""

import sys
import json
from collections import deque, defaultdict

# -----------------------------
# 工具函数
# -----------------------------
DIRS = {
    "UP":    (0, -1),
    "DOWN":  (0,  1),
    "LEFT":  (-1, 0),
    "RIGHT": (1,  0),
}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# -----------------------------
# 威胁场（当前 + 未来 + 潜在火线）
# -----------------------------
class ImprovedThreatField:
    """改进的威胁场：
    1) 当前子弹威胁（预测 3 步）
    2) 未来子弹威胁（预测 5 步，从 2 步后开始）
    3) 敌方“潜在火线”威胁：假设敌人可能在4个方向开火（被墙阻挡则停止）
    """
    def __init__(self, w, h, walls_set):
        self.w = w
        self.h = h
        self.walls = walls_set
        self.cur = [[0.0]*h for _ in range(w)]
        self.fut = [[0.0]*h for _ in range(w)]

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def calculate(self, bullets, tanks, my_name):
        # 重置
        for x in range(self.w):
            for y in range(self.h):
                self.cur[x][y] = 0.0
                self.fut[x][y] = 0.0

        # 子弹威胁：当前与未来
        for b in bullets:
            if b.get("owner") != my_name:
                self._propagate_bullet(b, current=True)
                self._propagate_bullet(b, current=False)

        # 敌坦近身威胁（近距离活动区）
        for t in tanks:
            if t.get("alive") and t.get("name") != my_name:
                self._propagate_enemy_body(t, current=True)
                self._propagate_enemy_body(t, current=False)

        # 敌人潜在火线：假设敌人可能转向任何方向并开火（被墙阻隔）
        for t in tanks:
            if t.get("alive") and t.get("name") != my_name:
                self._propagate_potential_fire_lines((t["x"], t["y"]))

        return self.cur, self.fut

    def _propagate_bullet(self, b, current=True):
        x, y = b["x"], b["y"]
        dx, dy = b["dx"], b["dy"]
        start_step = 0 if current else 2
        end_step = 3 if current else 5
        base = 15.0 if current else 10.0
        target = self.cur if current else self.fut

        # 子弹速度为坦克 2 倍，这里按 step*2 近似推进
        for step in range(start_step, end_step):
            nx = x + dx * step * 2
            ny = y + dy * step * 2
            if (nx, ny) in self.walls:
                break
            if not self.in_bounds(nx, ny):
                break
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
                if not self.in_bounds(nx, ny):
                    continue
                d = abs(dx) + abs(dy)
                if d <= rng:
                    target[nx][ny] += base / (d + 1.0)

    def _propagate_potential_fire_lines(self, enemy_pos):
        """敌人潜在火线（博弈式保守假设）：
        - 敌人可能向4个方向开火
        - 每条直线直到遇墙或边界
        - 威胁随距离衰减，加入到未来威胁图
        """
        ex, ey = enemy_pos
        base = 6.0  # 低于真实子弹，但能体现潜在威胁
        for dname, (dx, dy) in DIRS.items():
            cx, cy = ex, ey
            dist = 0
            while True:
                cx += dx
                cy += dy
                dist += 1
                if (cx, cy) in self.walls or not self.in_bounds(cx, cy):
                    break
                self.fut[cx][cy] += base / (dist + 0.5)


# -----------------------------
# 战术评估：逃生空间、掩体、视线等
# -----------------------------
class TacticalEvaluator:
    def __init__(self, w, h, walls_set):
        self.w = w
        self.h = h
        self.walls = walls_set

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def is_free(self, x, y, tanks_alive):
        if (x, y) in self.walls:
            return False
        if not self.in_bounds(x, y):
            return False
        for t in tanks_alive:
            if t["x"] == x and t["y"] == y:
                return False
        return True

    def cover_bonus(self, x, y):
        """与墙相邻可获得少量“掩体”加分（减少被直线击中的机会）。"""
        adj = 0
        for dx, dy in DIRS.values():
            if (x+dx, y+dy) in self.walls:
                adj += 1
        # 每面墙给一个小幅奖励
        return 0.6 * adj

    def safe_neighbors_count(self, x, y, cur_map, fut_map, threshold=12.0):
        cnt = 0
        for dx, dy in DIRS.values():
            nx, ny = x+dx, y+dy
            if self.in_bounds(nx, ny):
                if cur_map[nx][ny] + 0.4*fut_map[nx][ny] < threshold:
                    cnt += 1
        return cnt

    def safe_area_size(self, start, cur_map, fut_map, tanks_alive, threshold=12.0, max_depth=5):
        """在威胁阈值下的可达空间大小（逃生空间）。"""
        sx, sy = start
        if cur_map[sx][sy] + 0.4*fut_map[sx][sy] >= threshold:
            return 0
        q = deque([(sx, sy, 0)])
        seen = {(sx, sy)}
        count = 1
        while q:
            x, y, d = q.popleft()
            if d >= max_depth:
                continue
            for dx, dy in DIRS.values():
                nx, ny = x+dx, y+dy
                if (nx, ny) in seen:
                    continue
                if not self.in_bounds(nx, ny):
                    continue
                # 不穿墙，不穿坦克
                if (nx, ny) in self.walls:
                    continue
                blocked = False
                for t in tanks_alive:
                    if t["x"] == nx and t["y"] == ny and t["alive"]:
                        blocked = True
                        break
                if blocked:
                    continue
                # 威胁阈值
                if cur_map[nx][ny] + 0.4*fut_map[nx][ny] < threshold:
                    seen.add((nx, ny))
                    q.append((nx, ny, d+1))
                    count += 1
        return count

    def los_clear(self, a, b):
        """同一行或同一列且无墙阻隔则视线通畅"""
        ax, ay = a
        bx, by = b
        if ax == bx:
            y1, y2 = sorted([ay, by])
            for y in range(y1+1, y2):
                if (ax, y) in self.walls:
                    return False
            return True
        if ay == by:
            x1, x2 = sorted([ax, bx])
            for x in range(x1+1, x2):
                if (x, ay) in self.walls:
                    return False
            return True
        return False


# -----------------------------
# 自适应策略（加强版）
# -----------------------------
class AdaptiveStrategy:
    def __init__(self):
        self.mode = "balanced"  # "evasion" / "balanced" / "aggressive"

    def update(self, my_hp, enemy_count, high_threat_here, escape_neighbors):
        # 基于局面切换模式而非仅线性权重
        if my_hp <= 1 or high_threat_here:
            self.mode = "evasion"
        elif enemy_count >= 3 and escape_neighbors <= 1:
            self.mode = "evasion"
        elif enemy_count == 1 and my_hp >= 3:
            self.mode = "aggressive"
        else:
            self.mode = "balanced"

    def weights(self):
        if self.mode == "evasion":
            return {"survival": 0.85, "attack": 0.15}
        if self.mode == "aggressive":
            return {"survival": 0.45, "attack": 0.55}
        return {"survival": 0.65, "attack": 0.35}


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
        self.hazard_memory = defaultdict(int)  # (x,y) -> 衰减计数

    # --- 兼容 README：提供 TankAI 类 ---
class TankAI(ImprovedTankAI):
    pass

# 为了兼容旧引用名称
AI = TankAI

# -----------------------------
# 逻辑实现放到 TankAI 之下（mixin风格）
# -----------------------------
def _get_action_impl(self, state):
    me = state["self"]
    w = state["map_width"]
    h = state["map_height"]
    my_name = me["name"]
    my_pos = (me["x"], me["y"])
    my_hp = me["hp"]

    walls_set = {(x, y) if isinstance(x, int) else tuple(x) for x, y in state["walls"]} if state["walls"] else set()
    # 兼容 walls 可能是 [[x,y],...] 的情况
    if not walls_set and state["walls"]:
        walls_set = {tuple(w) for w in state["walls"]}

    tanks_alive = [t for t in state["tanks"] if t["alive"]]

    # 更新短期记忆：若掉血，标记上一次位置为“危险”（衰减记忆）
    if self.last_hp is not None and my_hp < self.last_hp and self.last_pos is not None:
        self.hazard_memory[self.last_pos] = 6  # 6 回合内降低该格评分

    # 衰减记忆
    keys_to_del = []
    for k in list(self.hazard_memory.keys()):
        self.hazard_memory[k] -= 1
        if self.hazard_memory[k] <= 0:
            keys_to_del.append(k)
    for k in keys_to_del:
        del self.hazard_memory[k]

    # 威胁场
    tf = ImprovedThreatField(w, h, walls_set)
    cur_map, fut_map = tf.calculate(state["bullets"], state["tanks"], my_name)

    te = TacticalEvaluator(w, h, walls_set)

    # 模式更新
    high_threat_here = cur_map[my_pos[0]][my_pos[1]] + 0.4*fut_map[my_pos[0]][my_pos[1]] > 18.0
    escape_neighbors = te.safe_neighbors_count(my_pos[0], my_pos[1], cur_map, fut_map, threshold=12.0)
    self.strategy.update(my_hp, len([t for t in state["tanks"] if t["alive"] and t["name"] != my_name]), high_threat_here, escape_neighbors)
    weights = self.strategy.weights()

    # 候选第一步
    candidates = []
    for d in DIR_LIST:
        dx, dy = DIRS[d]
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if not (0 <= nx < w and 0 <= ny < h):
            continue
        # 不能撞墙或撞坦克
        invalid = False
        if (nx, ny) in walls_set:
            invalid = True
        for t in tanks_alive:
            if t["x"] == nx and t["y"] == ny:
                invalid = True
                break
        if invalid:
            continue
        candidates.append((d, (nx, ny)))

    if not candidates:
        # 原地或无法移动时，返回一个合法方向（按规则只返回方向即可）
        self.last_action = "UP"
        self.last_pos = my_pos
        self.last_hp = my_hp
        self.history.append(self.last_action)
        return "UP"

    def attack_value_at(pos, move_dir):
        """考虑：
        1) 与敌人距离（越近越高，但避免贴脸）
        2) 低血敌人加分
        3) 若对齐且视线无墙阻隔（沿 move_dir 方向），加大加分（本回合自动开火）
        """
        x, y = pos
        val = 0.0
        # 距离项 + 残血奖励
        for t in state["tanks"]:
            if not t["alive"] or t["name"] == my_name:
                continue
            ex, ey = t["x"], t["y"]
            d = abs(ex - x) + abs(ey - y)
            if d <= 6:
                base = 14.0 / (d + 1.0)
                if t["hp"] <= 1:
                    base += 12.0
                elif t["hp"] == 2:
                    base += 4.0
                val += base

        # 沿朝向检查直线火力机会
        dx, dy = DIRS[move_dir]
        cx, cy = x, y
        dist = 0
        while True:
            cx += dx
            cy += dy
            dist += 1
            if (cx, cy) in walls_set or not (0 <= cx < w and 0 <= cy < h):
                break
            # 直线上若有敌人且无遮挡，则给显著奖励（越近越高）
            hit_any = False
            for t in state["tanks"]:
                if t["alive"] and t["name"] != my_name and t["x"] == cx and t["y"] == cy:
                    hit_any = True
                    # 敌人越近越好，残血再加分
                    bonus = 16.0 / (dist + 0.5)
                    if t["hp"] <= 1:
                        bonus += 10.0
                    val += bonus
                    break
            if hit_any:
                # 第一目标足够
                break
        return val

    def survival_penalty(pos):
        x, y = pos
        # 非线性：若威胁超过门槛，重罚
        mix = cur_map[x][y] + 0.4*fut_map[x][y]
        if mix > 22.0:
            base = 40.0 + (mix - 22.0) * 2.0
        else:
            base = mix * 1.2
        # 被包围风险（逃生口少）
        esc = te.safe_neighbors_count(x, y, cur_map, fut_map, threshold=12.0)
        if esc <= 1:
            base += 8.0
        # 危险记忆
        if (x, y) in self.hazard_memory:
            base += 6.0
        # 掩体小幅降低风险
        base -= te.cover_bonus(x, y) * 0.8
        return max(0.0, base)

    def mobility_bonus(pos):
        # 逃生空间越大越好（避免“被合围”的战略盲点）
        size = te.safe_area_size(pos, cur_map, fut_map, tanks_alive, threshold=12.0, max_depth=5)
        return min(10.0, size * 0.6)

    # 轻量两步前瞻：第一步 + 第二步贪心（使用未来威胁近似第二步风险）
    best_dir = candidates[0][0]
    best_score = -1e18
    for d1, p1 in candidates:
        # 第一层评分
        attack1 = attack_value_at(p1, d1)
        surv1 = survival_penalty(p1)
        mobi1 = mobility_bonus(p1)

        # 简单环路惩罚：避免与上一步相反来回横跳
        loop_pen = 0.0
        if len(self.history) >= 1:
            last = self.history[-1]
            opp = {"UP":"DOWN","DOWN":"UP","LEFT":"RIGHT","RIGHT":"LEFT"}[last]
            if d1 == opp:
                loop_pen += 3.5
        if self.last_action is not None and d1 == self.last_action:
            loop_pen += 1.5  # 轻微避免重复

        # 第二步：在 p1 处再挑一个方向做粗略估值（不考虑敌我更新，仅用 fut_map 近似）
        second_best = -1e18
        for d2, (dx2, dy2) in [(k, v) for k, v in DIRS.items()]:
            qx, qy = p1[0] + dx2, p1[1] + dy2
            if not (0 <= qx < w and 0 <= qy < h):
                continue
            if (qx, qy) in walls_set:
                continue
            blocked = False
            for t in tanks_alive:
                if t["x"] == qx and t["y"] == qy:
                    blocked = True
                    break
            if blocked:
                continue
            # 使用未来威胁 fut_map 作为第二步风险近似
            attack2 = attack_value_at((qx, qy), d2)
            # 第二步的生存惩罚：主要使用 fut_map
            mix2 = cur_map[qx][qy]*0.4 + 1.0*fut_map[qx][qy]
            surv2 = mix2 * 1.0
            score2 = weights["attack"] * attack2 - weights["survival"] * surv2 + 0.3 * mobility_bonus((qx, qy))
            if score2 > second_best:
                second_best = score2
        if second_best == -1e18:
            second_best = 0.0

        score1 = weights["attack"] * attack1 - weights["survival"] * surv1 + 0.7 * mobi1 - loop_pen
        total = score1 + 0.6 * second_best

        if total > best_score:
            best_score = total
            best_dir = d1

    self.last_action = best_dir
    self.last_pos = my_pos
    self.last_hp = my_hp
    self.history.append(best_dir)
    return best_dir

# 将实现函数绑定到类
TankAI.get_action = _get_action_impl
ImprovedTankAI.get_action = _get_action_impl

# -----------------------------
# 管道模式（stdin/stdout）
# -----------------------------
def main_loop():
    ai = TankAI()
    # 处理编码兼容
    if sys.version_info >= (3,7):
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

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

if __name__ == "__main__":
    main_loop()
