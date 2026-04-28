"""Performance benchmark for TankAI decision-making."""

import json
import time
from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bots.xjy import TankAI
from bots.xjy1v1 import TankAI as TankAI1v1


def make_state(x, y, width=20, height=15, num_enemies=3, num_bullets=2, num_walls=50):
    """Create a test state with configurable complexity."""
    walls = [[i % width, i // width] for i in range(num_walls)]
    tanks = [{"name": "XJY", "x": x, "y": y, "hp": 3, "alive": True}]
    for i in range(num_enemies):
        tanks.append({
            "name": f"enemy{i}",
            "x": (x + 5 + i * 3) % width,
            "y": (y + 3 + i * 2) % height,
            "hp": 3,
            "alive": True,
        })
    bullets = []
    for i in range(num_bullets):
        bullets.append({
            "owner": f"enemy{i}",
            "x": (x + 7 + i) % width,
            "y": (y + 1) % height,
            "dx": 1 if i % 2 == 0 else -1,
            "dy": 0,
        })
    return {
        "self": tanks[0],
        "map_width": width,
        "map_height": height,
        "walls": walls,
        "tanks": tanks,
        "bullets": bullets,
    }


def benchmark(name, ai_class, state, iterations=1000):
    """Run benchmark and return results."""
    ai = ai_class()

    # Warm up (build static maps)
    ai.get_action(state)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        ai.get_action(state)
    elapsed = time.perf_counter() - start

    avg_us = (elapsed / iterations) * 1_000_000
    return {"name": name, "iterations": iterations, "total_s": elapsed, "avg_us": avg_us}


def main():
    print("=" * 70)
    print("TankAI Performance Benchmark")
    print("=" * 70)

    # Test scenarios
    scenarios = [
        ("Small map (10x8, 2 enemies, 1 bullet, 10 walls)", make_state(5, 4, 10, 8, 2, 1, 10)),
        ("Medium map (20x15, 3 enemies, 2 bullets, 50 walls)", make_state(10, 7, 20, 15, 3, 2, 50)),
        ("Large map (30x20, 5 enemies, 4 bullets, 100 walls)", make_state(15, 10, 30, 20, 5, 4, 100)),
        ("Heavy walls (20x15, 3 enemies, 2 bullets, 150 walls)", make_state(10, 7, 20, 15, 3, 2, 150)),
    ]

    results = []

    print(f"\n{'Scenario':<50} {'Avg (μs)':<12} {'Total (s)':<10}")
    print("-" * 70)

    for scenario_name, state in scenarios:
        # xjy bot
        r_xjy = benchmark(f"xjy: {scenario_name}", TankAI, state, iterations=500)
        # 1v1 bot
        r_1v1 = benchmark(f"xjy1v1: {scenario_name}", TankAI1v1, state, iterations=500)

        print(f"xjy: {scenario_name:<42} {r_xjy['avg_us']:>8.1f}   {r_xjy['total_s']:>8.3f}")
        print(f"1v1: {scenario_name:<42} {r_1v1['avg_us']:>8.1f}   {r_1v1['total_s']:>8.3f}")
        results.extend([r_xjy, r_1v1])

    print("-" * 70)

    # Summary stats
    print("\nSummary:")
    all_avg = [r["avg_us"] for r in results]
    print(f"  Overall avg: {sum(all_avg) / len(all_avg):.1f} μs/call")
    print(f"  Min: {min(all_avg):.1f} μs/call")
    print(f"  Max: {max(all_avg):.1f} μs/call")

    # Target: should be under 1ms (1000μs) per call for real-time gameplay
    real_time_target = 1000  # μs
    passing = all(r["avg_us"] < real_time_target for r in results)
    print(f"\n  Real-time target (<{real_time_target}μs/call): {'PASS' if passing else 'FAIL'}")

    return 0 if passing else 1


if __name__ == "__main__":
    sys.exit(main())