"""Analyst charts for code-to-3d: backend census + Agentworth ladder."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "/Users/saurabh/code/motionvector/media-scratch/code-to-3d-charts"
plt.rcParams.update({"figure.dpi": 150, "font.size": 9})

# --- Data (census, Sep 2026; prices approx, stars verified) ---
backends = ["Three.js", "Blender", "Babylon.js", "PlayCanvas", "Godot",
            "Unity", "Unreal", "Houdini", "C4D", "Maya"]
stars_k = [113, 0, 0, 16, 0, 0, 0, 0, 0, 0]  # GitHub stars (k); 0 = not web-tracked
human_ease = [5, 2, 3, 3, 3, 2, 1, 1, 3, 1]   # 5 = gentle ... 1 = cliff
agent_aff  = [5, 4, 3, 2, 2, 2, 2, 3, 1, 1]   # training footprint + native format
free =       [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]   # 1 = free/open

# 1) Human ease vs agent affinity, grouped
y = np.arange(len(backends))
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(y + 0.2, human_ease, 0.4, label="Human ease (5=gentle)")
ax.barh(y - 0.2, agent_aff, 0.4, label="Agent affinity (5=native)")
ax.set_yticks(y, backends)
ax.set_xlabel("score (1–5)")
ax.set_title("code-to-3d backend census: who is it easy FOR?")
ax.legend(loc="lower right")
ax.set_xlim(0, 5.5)
fig.tight_layout()
fig.savefig(f"{OUT}/affinity.png")

# 2) Web-tracked popularity (log) + free marker
mask = [s > 0 for s in stars_k]
names = [b for b, m in zip(backends, mask) if m]
vals = [s for s, m in zip(stars_k, mask) if m]
fig, ax = plt.subplots(figsize=(7, 3))
ax.bar(names, vals, color=["#2ca02c"] * len(names))
ax.set_yscale("log")
ax.set_ylabel("GitHub stars (k, log scale)")
ax.set_title("Web 3D mindshare is a monopoly (Three.js 113k vs PlayCanvas 16k)")
for n, v in zip(names, vals):
    ax.text(n, v * 1.15, f"{v}k", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(f"{OUT}/popularity.png")

# 3) Ladder: sessions vs cost per rung (week, 467 sessions, $4480)
rungs = ["r5 CI", "r4 commit", "r3 test", "r2 artifact", "r0 unflown"]
sess = [7, 222, 12, 36, 190]
cost = [466, 3546, 91, 118, 260]
x = np.arange(len(rungs))
fig, ax1 = plt.subplots(figsize=(8, 4))
ax1.bar(x - 0.2, sess, 0.4, label="sessions")
ax1.set_ylabel("sessions")
ax2 = ax1.twinx()
ax2.bar(x + 0.2, cost, 0.4, color="orange", label="cost USD")
ax2.set_ylabel("cost USD")
ax1.set_xticks(x, rungs)
ax1.set_title("Agentworth week: sessions vs spend per rung (r4 eats 79% of $)")
fig.tight_layout()
fig.savefig(f"{OUT}/ladder.png")
print("wrote affinity.png popularity.png ladder.png")
