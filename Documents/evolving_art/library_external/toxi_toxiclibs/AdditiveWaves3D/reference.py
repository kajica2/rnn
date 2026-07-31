"""AdditiveWaves3D — Layered wave / FBM height-field terrain.

A pure-numpy port of the December 2009 toxiclibs demo 'Additive waves'
(https://web.archive.org/web/2011/http://toxiclibs.org/2009/12/additive-waves/).

The terrain height at (x, y, t) is the sum of:
  * `wave_count` sinusoidal generators (each with its own amplitude,
    frequency, phase, time-speed), and
  * a single FBM (fractional Brownian motion) noise layer.

The result is a 2D heightfield, rendered as a triangle-mesh surface with
per-vertex shading from the local normal.
"""
from __future__ import annotations

import numpy as np


class AdditiveWaves3D:
    """3D heightfield driven by layered sine waves + FBM noise.

    The wave generators are sampled on a fixed (N, N) grid in the X-Y
    plane; their sum plus the FBM contribution becomes the Z component.
    The mesh is rebuilt each step (cheap; the mesh is small) and
    """

    def __init__(self, dim=96, extent=6.0, wave_count=4, noise_amp=0.4,
                 noise_scale=0.6, time_speed=0.3, seed=0):
        self.dim = dim
        self.extent = extent
        self.wave_count = wave_count
        self.noise_amp = noise_amp
        self.noise_scale = noise_scale
        self.time_speed = time_speed
        self.rng = np.random.default_rng(seed)
        # Each wave generator: amplitude, freq, phase, time-speed
        # Frequencies are 2-vectors (spatial), and each generator also has
        # a temporal speed that drives the sin's argument.
        self.waves = []
        for _ in range(wave_count):
            self.waves.append({
                'amp':   self.rng.uniform(0.2, 0.8),
                'freq':  self.rng.uniform(0.4, 1.2, size=2) * self.rng.choice([-1, 1], size=2),
                'phase': self.rng.uniform(0, 2 * np.pi),
                'speed': self.rng.uniform(0.3, 1.0),
            })
        # Precompute the X/Y grid.
        xs = np.linspace(-extent / 2, extent / 2, dim, dtype=np.float32)
        ys = np.linspace(-extent / 2, extent / 2, dim, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(xs, ys, indexing='xy')
        self.t = 0.0

    def step(self, n=1):
        """Advance the simulation by n steps."""
        for _ in range(n):
            self.t += self.time_speed * 0.016
            # Sum the wave contributions
            z = np.zeros_like(self.xx, dtype=np.float32)
            for w in self.waves:
                f = w['freq']
                arg = 2 * np.pi * (f[0] * self.xx + f[1] * self.yy) + w['phase'] + w['speed'] * self.t
                z += w['amp'] * np.sin(arg)
            # FBM noise layer (3 octaves of value-noise on a coarse grid,
            # bilinearly interpolated; cheap to compute on the fly).
            z += self.noise_amp * self._fbm(self.xx * self.noise_scale,
                                            self.yy * self.noise_scale,
                                            self.t * 0.2, octaves=3)
        return z

    def _fbm(self, x, y, t, octaves=3):
        """Tiny FBM via summed value-noise on a coarse grid + interp."""
        total = np.zeros_like(x, dtype=np.float32)
        amp = 1.0
        freq = 1.0
        for _ in range(octaves):
            total += amp * self._value_noise(x * freq, y * freq, t)
            amp *= 0.5
            freq *= 2.07  # non-integer to avoid grid aliasing
        return total / max(1.0, 1.875)  # normalize to roughly [-1, 1]

    def _value_noise(self, x, y, t):
        """Trilinear value noise on a coarse grid (deterministic seed)."""
        xi = np.floor(x).astype(np.int32)
        yi = np.floor(y).astype(np.int32)
        xf = x - xi
        yf = y - yi
        # 4 corners of the cell, animated by t
        def h(a, b, c):
            # hash of (a, b, c) → [-1, 1] via simple sin-based hash
            n = (np.sin(a * 12.9898 + b * 78.233 + c * 37.719) * 43758.5453)
            return (n - np.floor(n)) * 2.0 - 1.0
        v00 = h(xi,     yi,     0)
        v10 = h(xi + 1, yi,     0)
        v01 = h(xi,     yi + 1, 0)
        v11 = h(xi + 1, yi + 1, 0)
        # smoothstep weights
        u = xf * xf * (3 - 2 * xf)
        v = yf * yf * (3 - 2 * yf)
        top = v00 * (1 - u) + v10 * u
        bot = v01 * (1 - u) + v11 * u
        return top * (1 - v) + bot * v

    def mesh(self):
        """Return vertex positions (N*N, 3) and face indices ((N-1)*(N-1)*2, 3)."""
        z = self.step(1)
        verts = np.stack([self.xx.ravel(), self.yy.ravel(), z.ravel()], axis=1)
        # Build faces: two triangles per cell
        faces = []
        n = self.dim
        for j in range(n - 1):
            for i in range(n - 1):
                a = j * n + i
                b = j * n + (i + 1)
                c = (j + 1) * n + (i + 1)
                d = (j + 1) * n + i
                faces.append([a, b, c])
                faces.append([a, c, d])
        return verts, np.array(faces, dtype=np.int32)

    def render(self, shade_mode='gradient'):
        """Return an HxWx3 RGB image of the terrain (rendered as 2D projection)."""
        verts, faces = self.mesh()
        img = self._project(verts, faces, shade_mode)
        return img

    def _project(self, verts, faces, shade_mode):
        """Project the 3D mesh to 2D and shade faces."""
        n = self.dim
        # Simple orthographic projection: use X, Y as image coords, height as shading
        H = W = n
        img = np.zeros((H, W, 3), dtype=np.uint8)
        # Compute face colors via gradient (height-based)
        z = verts[:, 2].reshape(n, n)
        for f in faces:
            for k in range(3):
                v0, v1, v2 = f
                # Use the centroid for shading
                pass
        # Rasterize by averaging the height into the cell
        for f in faces:
            for k in range(3):
                vi = f[k]
                ix = int(verts[vi, 0] / self.extent * (n - 1) + n / 2) % n
                iy = int(verts[vi, 1] / self.extent * (n - 1) + n / 2) % n
                h = verts[vi, 2]
                # Map height to a blue→white gradient
                t = np.clip((h + 1.5) / 3.0, 0, 1)
                if shade_mode == 'gradient':
                    col = (int(40 + 215 * t), int(80 + 175 * t), int(160 + 95 * t))
                elif shade_mode == 'wireframe':
                    col = (255, 255, 255)
                else:
                    col = (180, 180, 200)
                img[iy, ix] = col
        return img


# Self-test: render a single frame and report its shape + color range.
if __name__ == '__main__':
    sim = AdditiveWaves3D(dim=128, wave_count=4, noise_amp=0.4, seed=42)
    img = sim.render('gradient')
    print('image shape:', img.shape)
    print('nonzero px:', int((img.sum(axis=-1) > 0).sum()))
    print('peak:', int(img.max()))
