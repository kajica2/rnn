"""VerletPhysics3D — 3D mass-spring cloth simulation (Jakobsen 2001 style).

A pure-numpy port of Karsten Schmidt's toxiclibs.physics.VerletPhysics3D
(Karsten Schmidt, 2008). The algorithm uses position-based dynamics:

  * Each particle stores (x, x_prev) instead of (x, v).
  * Integration: x_new = x + (x - x_prev) * damping + a * dt²
  * Constraint relaxation: for each spring, project both ends toward
    the rest length by ±(k/2) * (current - rest) * direction.

Bending constraints span 3-particle chains and preserve the rest
angle; the floor is a hard plane (y >= 0) with restitution.

The 2D version is `toxi_openframeworks/ParticleSpring2D`. This is the
3D extension.
"""
from __future__ import annotations

import numpy as np


class VerletPhysics3D:
    """3D Verlet mass-spring system with cloth-grid initializer."""

    def __init__(self, n_grid=14, size=4.0, gravity=0.3, damping=0.98,
                 iterations=12, stiffness=1.0, wind=0.0, seed=0):
        self.n = n_grid
        self.size = size
        self.gravity = gravity
        self.damping = damping
        self.iterations = iterations
        self.stiffness = stiffness
        self.wind = wind
        self.rng = np.random.default_rng(seed)

        # Build a square cloth grid in the XZ plane at y = size/2.
        spacing = size / n_grid
        half = size / 2
        coords = np.array(
            [[(i - n_grid/2) * spacing, half, (j - n_grid/2) * spacing]
             for j in range(n_grid) for i in range(n_grid)],
            dtype=np.float32,
        )
        n_particles = n_grid * n_grid
        self.n_particles = n_particles
        self.pos = coords.copy()
        self.pos_prev = coords.copy()
        # Pin the four corners (so the cloth hangs)
        self.locked = np.zeros(n_particles, dtype=bool)
        for (i, j) in [(0, 0), (n_grid-1, 0), (0, n_grid-1), (n_grid-1, n_grid-1)]:
            self.locked[j * n_grid + i] = True
        # Slight initial perturbation so the relaxation has something to do
        self.pos += self.rng.normal(0, 0.01, size=self.pos.shape).astype(np.float32)

        # Build springs: structural (4-neighbors) + shear (diagonals)
        # + bending (skip-one neighbors). Each is a (a, b) pair.
        springs = []
        for j in range(n_grid):
            for i in range(n_grid):
                idx = j * n_grid + i
                if i + 1 < n_grid:
                    springs.append((idx, j * n_grid + (i + 1)))
                if j + 1 < n_grid:
                    springs.append((idx, (j + 1) * n_grid + i))
                if i + 1 < n_grid and j + 1 < n_grid:
                    springs.append((idx, (j + 1) * n_grid + (i + 1)))
                if i + 2 < n_grid:
                    springs.append((idx, j * n_grid + (i + 2)))
                if j + 2 < n_grid:
                    springs.append((idx, (j + 2) * n_grid + i))
        self.spring_a = np.array([s[0] for s in springs], dtype=np.int32)
        self.spring_b = np.array([s[1] for s in springs], dtype=np.int32)
        # Precompute rest lengths
        d = self.pos[self.spring_a] - self.pos[self.spring_b]
        self.rest_length = np.linalg.norm(d, axis=1)
        self.t = 0

    def step(self, n=1):
        """Advance n timesteps."""
        for _ in range(n):
            self._integrate()
            for _ in range(self.iterations):
                self._satisfy_constraints()
            self._collide_floor()
            self.t += 1
        return self.pos

    def _integrate(self):
        # x_new = x + (1 - damping_loss) * (x - x_prev) + a * dt²
        # We treat damping as velocity-damping: v *= damping.
        # In Verlet form: x_new = x + damping * (x - x_prev) + a
        vel = (self.pos - self.pos_prev) * self.damping
        a = np.array([self.wind, -self.gravity, 0.0], dtype=np.float32)
        # Same acceleration on every particle (gravity + wind)
        a_per_particle = np.broadcast_to(a, self.pos.shape).copy()
        self.pos_prev = self.pos.copy()
        self.pos = self.pos + vel + a_per_particle * 0.016
        # Locked particles don't move
        self.pos[self.locked] = self.pos_prev[self.locked]

    def _satisfy_constraints(self):
        a_idx, b_idx = self.spring_a, self.spring_b
        pa = self.pos[a_idx]
        pb = self.pos[b_idx]
        delta = pa - pb
        d = np.linalg.norm(delta, axis=1, keepdims=True) + 1e-9
        # Guard against NaN: if a particle ended up at NaN (e.g. numerical
        # blow-up at start), reset it to its previous position.
        if not np.isfinite(self.pos).all():
            self.pos = np.where(np.isfinite(self.pos), self.pos, self.pos_prev)
        diff = (d[:, 0] - self.rest_length) / d[:, 0]
        # Move each end by ±(k/2) along the normalized direction.
        k = self.stiffness * 0.5
        move = delta * diff[:, None] * k
        np.add.at(self.pos, a_idx, -move)
        np.add.at(self.pos, b_idx,  move)
        # Re-pin locked particles
        self.pos[self.locked] = self.pos_prev[self.locked]

    def _collide_floor(self):
        below = self.pos[:, 1] < 0
        if below.any():
            self.pos[below, 1] = 0
            # Reflect velocity (damped) along Y
            vel = self.pos[below] - self.pos_prev[below]
            vel[:, 1] = -vel[:, 1] * 0.3
            self.pos_prev[below] = self.pos[below] - vel

    def mesh(self):
        """Return vertex positions and a triangulated face list."""
        verts = self.pos.copy()
        faces = []
        n = self.n
        for j in range(n - 1):
            for i in range(n - 1):
                a = j * n + i
                b = j * n + (i + 1)
                c = (j + 1) * n + (i + 1)
                d = (j + 1) * n + i
                faces.append([a, b, c])
                faces.append([a, c, d])
        return verts, np.array(faces, dtype=np.int32)

    def render(self, size=400, color_top=(0.85, 0.4, 0.95), color_bot=(0.15, 0.0, 0.4)):
        """Render the cloth as a 2D projection (front view) with the mesh drawn
        as colored line segments, plus vertex dots.
        """
        verts, faces = self.mesh()
        # Clamp NaN/Inf to 0 (defensive: relaxations can blow up before settling)
        verts = np.where(np.isfinite(verts), verts, 0.0)
        H = W = size
        img = np.zeros((H, W, 3), dtype=np.float32)

        def to_screen(x, y, z):
            """Project (x, y, z) → screen (px, py, t) where t is the height-tint."""
            px = int((x / self.size + 0.5) * (W - 1))
            py = int((z / self.size + 0.5) * (H - 1))
            t = float(np.clip((y / self.size + 0.5), 0, 1))
            return px, py, t

        # Draw the structural springs as line segments
        # (diagonals + bending lines are omitted to keep the image readable).
        seen = set()
        for f in faces:
            for k in range(3):
                a, b = int(f[k]), int(f[(k + 1) % 3])
                key = (min(a, b), max(a, b))
                if key in seen:
                    continue
                seen.add(key)
                x0, y0, z0 = verts[a]
                x1, y1, z1 = verts[b]
                px0, py0, t0 = to_screen(x0, y0, z0)
                px1, py1, t1 = to_screen(x1, y1, z1)
                # Bresenham-ish simple line draw
                steps = max(abs(px1 - px0), abs(py1 - py0), 1)
                for s in range(steps + 1):
                    f_ = s / steps
                    px = int(px0 + f_ * (px1 - px0))
                    py = int(py0 + f_ * (py1 - py0))
                    t = t0 + f_ * (t1 - t0)
                    if 0 <= px < W and 0 <= py < H:
                        col = tuple(color_bot[i] * (1 - t) + color_top[i] * t for i in range(3))
                        img[py, px] = col
        return (img * 255).clip(0, 255).astype(np.uint8)


if __name__ == '__main__':
    sim = VerletPhysics3D(n_grid=16, size=4.0, gravity=0.15, damping=0.99,
                         iterations=8, stiffness=0.5, seed=42)
    for _ in range(60):
        sim.step(1)
    img = sim.render(size=400)
    print('image:', img.shape, 'nonzero:', int((img.sum(axis=-1) > 0).sum()))
    print('pos range:', sim.pos.min(), sim.pos.max())
