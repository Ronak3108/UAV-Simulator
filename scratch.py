"""
The purpose of this file was to run the physics engine about a hundred time to
identify the time taken (cost) for different configurations. With the help of results
recieved from this, we devised the value of proportionality constant in estimate_cost() in engine.py
"""


from simulator.state import SimConfig
from simulator.engine import run, estimate_cost, clear_cache
from pandas import DataFrame

# ring/spiral/nested/random accept any n_uav >= 1 (per valid_count), so they're
# the easiest formations to vary n_uav freely without hitting validate() errors.
# square/diamond need perfect squares; x needs even numbers.
CONFIGS = [
    SimConfig(formation="nested", n_uav=26, grid_points=151, n_snapshots=10),
    SimConfig(formation="x", n_uav=64, grid_points=101, n_snapshots=2),
    SimConfig(formation="nested", n_uav=47, grid_points=101, n_snapshots=1),
    SimConfig(formation="random", n_uav=27, grid_points=301, n_snapshots=6, seed=8479),
    SimConfig(formation="square", n_uav=49, grid_points=61, n_snapshots=1),
    SimConfig(formation="x", n_uav=6, grid_points=121, n_snapshots=6),
    SimConfig(formation="spiral", n_uav=17, grid_points=101, n_snapshots=8),
    SimConfig(formation="square", n_uav=64, grid_points=121, n_snapshots=2),
    SimConfig(formation="square", n_uav=49, grid_points=301, n_snapshots=8),
    SimConfig(formation="spiral", n_uav=31, grid_points=51, n_snapshots=5),
    SimConfig(formation="spiral", n_uav=28, grid_points=175, n_snapshots=10),
    SimConfig(formation="spiral", n_uav=61, grid_points=301, n_snapshots=2),
    SimConfig(formation="square", n_uav=16, grid_points=101, n_snapshots=3),
    SimConfig(formation="nested", n_uav=39, grid_points=351, n_snapshots=1),
    SimConfig(formation="spiral", n_uav=57, grid_points=151, n_snapshots=1),
    SimConfig(formation="ring", n_uav=5, grid_points=301, n_snapshots=1),
    SimConfig(formation="nested", n_uav=61, grid_points=101, n_snapshots=4),
    SimConfig(formation="diamond", n_uav=25, grid_points=61, n_snapshots=6),
    SimConfig(formation="spiral", n_uav=48, grid_points=175, n_snapshots=2),
    SimConfig(formation="spiral", n_uav=6, grid_points=251, n_snapshots=2),
    SimConfig(formation="spiral", n_uav=10, grid_points=301, n_snapshots=10),
    SimConfig(formation="ring", n_uav=39, grid_points=81, n_snapshots=1),
    SimConfig(formation="random", n_uav=55, grid_points=121, n_snapshots=3, seed=2088),
    SimConfig(formation="ring", n_uav=42, grid_points=71, n_snapshots=8),
    SimConfig(formation="spiral", n_uav=61, grid_points=401, n_snapshots=4),
    SimConfig(formation="x", n_uav=6, grid_points=175, n_snapshots=8),
    SimConfig(formation="random", n_uav=29, grid_points=71, n_snapshots=5, seed=4092),
    SimConfig(formation="random", n_uav=15, grid_points=301, n_snapshots=5, seed=4114),
    SimConfig(formation="spiral", n_uav=47, grid_points=301, n_snapshots=1),
    SimConfig(formation="ring", n_uav=16, grid_points=71, n_snapshots=10),
    SimConfig(formation="diamond", n_uav=49, grid_points=61, n_snapshots=1),
    SimConfig(formation="random", n_uav=17, grid_points=81, n_snapshots=4, seed=2296),
    SimConfig(formation="nested", n_uav=26, grid_points=51, n_snapshots=8),
    SimConfig(formation="random", n_uav=59, grid_points=51, n_snapshots=2, seed=4533),
    SimConfig(formation="square", n_uav=36, grid_points=61, n_snapshots=8),
    SimConfig(formation="ring", n_uav=57, grid_points=61, n_snapshots=10),
    SimConfig(formation="nested", n_uav=8, grid_points=61, n_snapshots=8),
    SimConfig(formation="ring", n_uav=45, grid_points=301, n_snapshots=2),
    SimConfig(formation="random", n_uav=34, grid_points=81, n_snapshots=5, seed=3510),
    SimConfig(formation="ring", n_uav=27, grid_points=61, n_snapshots=4),
    SimConfig(formation="spiral", n_uav=36, grid_points=71, n_snapshots=10),
    SimConfig(formation="x", n_uav=16, grid_points=101, n_snapshots=2),
    SimConfig(formation="nested", n_uav=45, grid_points=201, n_snapshots=5),
    SimConfig(formation="square", n_uav=25, grid_points=251, n_snapshots=5),
    SimConfig(formation="diamond", n_uav=49, grid_points=351, n_snapshots=2),
    SimConfig(formation="spiral", n_uav=5, grid_points=201, n_snapshots=2),
    SimConfig(formation="ring", n_uav=64, grid_points=201, n_snapshots=1),
    SimConfig(formation="diamond", n_uav=36, grid_points=101, n_snapshots=1),
    SimConfig(formation="x", n_uav=8, grid_points=61, n_snapshots=8),
    SimConfig(formation="diamond", n_uav=64, grid_points=401, n_snapshots=3),
    SimConfig(formation="square", n_uav=9, grid_points=81, n_snapshots=3),
    SimConfig(formation="x", n_uav=32, grid_points=301, n_snapshots=3),
    SimConfig(formation="spiral", n_uav=18, grid_points=61, n_snapshots=2),
    SimConfig(formation="ring", n_uav=40, grid_points=121, n_snapshots=10),
    SimConfig(formation="spiral", n_uav=29, grid_points=351, n_snapshots=10),
    SimConfig(formation="random", n_uav=49, grid_points=251, n_snapshots=8, seed=5930),
    SimConfig(formation="spiral", n_uav=34, grid_points=61, n_snapshots=5),
    SimConfig(formation="ring", n_uav=61, grid_points=401, n_snapshots=2),
    SimConfig(formation="ring", n_uav=27, grid_points=351, n_snapshots=6),
    SimConfig(formation="nested", n_uav=61, grid_points=201, n_snapshots=4),
    SimConfig(formation="spiral", n_uav=5, grid_points=51, n_snapshots=10),
    SimConfig(formation="ring", n_uav=6, grid_points=51, n_snapshots=6),
    SimConfig(formation="x", n_uav=10, grid_points=175, n_snapshots=6),
    SimConfig(formation="random", n_uav=44, grid_points=301, n_snapshots=5, seed=5180),
    SimConfig(formation="spiral", n_uav=30, grid_points=61, n_snapshots=4),
    SimConfig(formation="x", n_uav=10, grid_points=301, n_snapshots=4),
    SimConfig(formation="ring", n_uav=31, grid_points=251, n_snapshots=2),
    SimConfig(formation="ring", n_uav=14, grid_points=101, n_snapshots=4),
    SimConfig(formation="x", n_uav=8, grid_points=301, n_snapshots=10),
    SimConfig(formation="spiral", n_uav=9, grid_points=101, n_snapshots=8),
    SimConfig(formation="spiral", n_uav=9, grid_points=121, n_snapshots=5),
    SimConfig(formation="spiral", n_uav=52, grid_points=175, n_snapshots=8),
    SimConfig(formation="x", n_uav=40, grid_points=121, n_snapshots=1),
    SimConfig(formation="x", n_uav=8, grid_points=251, n_snapshots=6),
    SimConfig(formation="ring", n_uav=29, grid_points=151, n_snapshots=10),
    SimConfig(formation="square", n_uav=9, grid_points=201, n_snapshots=1),
    SimConfig(formation="spiral", n_uav=18, grid_points=201, n_snapshots=8),
    SimConfig(formation="spiral", n_uav=4, grid_points=51, n_snapshots=6),
    SimConfig(formation="ring", n_uav=6, grid_points=351, n_snapshots=3),
    SimConfig(formation="spiral", n_uav=50, grid_points=51, n_snapshots=2),
    SimConfig(formation="ring", n_uav=47, grid_points=151, n_snapshots=1),
    SimConfig(formation="random", n_uav=42, grid_points=101, n_snapshots=3, seed=9038),
    SimConfig(formation="ring", n_uav=11, grid_points=121, n_snapshots=3),
    SimConfig(formation="spiral", n_uav=61, grid_points=121, n_snapshots=2),
    SimConfig(formation="square", n_uav=4, grid_points=51, n_snapshots=2),
    SimConfig(formation="nested", n_uav=19, grid_points=101, n_snapshots=4),
    SimConfig(formation="x", n_uav=24, grid_points=351, n_snapshots=4),
    SimConfig(formation="x", n_uav=48, grid_points=301, n_snapshots=2),
    SimConfig(formation="spiral", n_uav=27, grid_points=301, n_snapshots=10),
    SimConfig(formation="x", n_uav=8, grid_points=301, n_snapshots=5),
    SimConfig(formation="nested", n_uav=41, grid_points=61, n_snapshots=8),
    SimConfig(formation="spiral", n_uav=6, grid_points=121, n_snapshots=1),
    SimConfig(formation="nested", n_uav=61, grid_points=401, n_snapshots=10),
    SimConfig(formation="ring", n_uav=4, grid_points=101, n_snapshots=6),
    SimConfig(formation="square", n_uav=36, grid_points=101, n_snapshots=6),
    SimConfig(formation="spiral", n_uav=36, grid_points=81, n_snapshots=5),
    SimConfig(formation="nested", n_uav=18, grid_points=71, n_snapshots=4),
    SimConfig(formation="random", n_uav=25, grid_points=101, n_snapshots=3, seed=8900),
    SimConfig(formation="x", n_uav=8, grid_points=51, n_snapshots=6),
    SimConfig(formation="ring", n_uav=5, grid_points=81, n_snapshots=2),
]

clear_cache()

cost_data = {
    'n_uav': [],
    'grid_points': [],
    'n_snapshots': [],
    'actual_cost': []
}

count = 1

for cfg in CONFIGS:
    print(f"Running Test {count}")
    result = run(cfg)
    actual = result.compute_ms

    cost_data['n_uav'].append(cfg.n_uav)
    cost_data['grid_points'].append(cfg.grid_points)
    cost_data['n_snapshots'].append(cfg.n_snapshots)
    cost_data['actual_cost'].append(actual)

    count += 1

df = DataFrame(cost_data)

df.to_csv("cost_data.csv", index=False)
print("The cost is in milliseconds (ms).")