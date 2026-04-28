"""Constants shared by the rule-based tank bot."""

# Movement and search limits
BFS_MOBILITY_LIMIT: int = 8  # Max BFS depth - beyond this, mobility differences are negligible
DFS_MAX_DEPTH: int = 20  # Max DFS depth for trap detection - prevents infinite recursion
TRAP_SURVIVAL_THRESHOLD: int = 15  # Survival depth below which a position is considered a trap
BULLET_SPEED: int = 2  # Bullet moves 2 cells per frame

# Scoring constants
SCORE_INVALID = -float("inf")
SCORE_BULLET_HIT = -100000.0
SCORE_TRAP_BASE = -50000.0

WEIGHT_SURVIVAL_DEPTH = 1000.0
WEIGHT_MOBILITY = 10.0
WEIGHT_CENTER = 2.0
WEIGHT_AIM = 50.0
WEIGHT_CONTINUITY = 5.0

DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
DIR_LIST = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
CLOCKWISE_NEXT = {"UP": "RIGHT", "RIGHT": "DOWN", "DOWN": "LEFT", "LEFT": "UP"}

