"""SuperEllipsoid — parametric 3D primitive (sphere ↔ box morph).

A pure-numpy port of Karsten Schmidt's toxiclibs.geom.SuperEllipsoid
(2010). The implicit form uses two shape parameters (e1, e2) to morph
between a sphere, a box, a pillow, an astroid, and other shapes.

  x(η, ω) = sign(cos(η)) * |cos(η)|^e1 * sign(cos(ω)) * |cos(ω)|^e2
  y(η, ω) = sign(cos(η)) * |cos(η)|^e1 * sign(sin(ω)) * |sin(ω)|^e2
  z(η, ω) = sign(sin(η)) * |sin(η)|^e1

  η ∈ [-π/2, π/2]   (latitude)
  ω ∈ [-π, π]       (longitude)

  e1 = e2 = 1   →   sphere
  e1 = e2 = 4   →   box (rounded)
  e1 < 1, e2 < 1 → pinched / astroid
  e1 = 0.5, e2 = 1 → lemon
  e1 = 1, e2 = 0.5 → egg

This is the same parameterization used in Ken Perlin's 1980s
'Ken-ipercival' supershapes and the original Macintosh 'S' icon
(Susan Kare, 1984, e1 ≈ e2 ≈ 4).
"""
from __future__ import annotations

import numpy as np


def superellipsoid_points(e1, e2, M, N, scale=1.0):
    """Return (M*N, 3) vertex array for a super-ellipsoid."""
    omega = np.linspace(-np.pi, np.pi, M, endpoint=False)
    eta = np.linspace(-np.pi / 2, np.pi / 2, N)
    O, E = np.meshgrid(omega, eta, indexing='xy')
    # sign-preserving power: sign(x) * |x|^e
    def spow(x, e):
        return np.sign(x) * np.abs(x) ** e
    cx, sx = spow(np.cos(E), e1), spow(np.sin(E), e1)
    cox, sox = spow(np.cos(O), e2), spow(np.sin(O), e2)
    x = cx * cox
    y = cx * sox
    z = sx
    verts = np.stack([x.ravel(), y.ravel(), z.ravel()], axis=1) * scale
    return verts, O, E


def superellipsoid_faces(M, N):
    """Return triangulated face index list (M*N, 3) sized."""
    faces = []
    for j in range(N - 1):
        for i in range(M - 1):
            a = j * M + i
            b = j * M + (i + 1)
            c = (j + 1) * M + (i + 1)
            d = (j + 1) * M + i
            faces.append([a, b, c])
            faces.append([a, c, d])
    # Wrap the longitude seam
    for j in range(N - 1):
        a = j * M + (M - 1)
        b = j * M
        c = (j + 1) * M
        d = (j + 1) * M + (M - 1)
        faces.append([a, b, c])
        faces.append([a, c, d])
    return np.array(faces, dtype=np.int32)


def vertex_normals(V, F):
    """Average face normals at each vertex."""
    normals = np.zeros_like(V)
    for f in F:
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        n = np.cross(b - a, c - a)
        normals[f[0]] += n
        normals[f[1]] += n
        normals[f[2]] += n
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / (norms + 1e-9)


class SuperEllipsoid:
    """Animated super-ellipsoid (morphs e1, e2 over time)."""

    def __init__(self, e1=1.0, e2=1.0, M=64, N=32, scale=1.0,
                 e1_speed=0.5, e2_speed=0.3, seed=0):
        self.e1_init = e1
        self.e2_init = e2
        self.M = M
        self.N = N
        self.scale = scale
        self.e1_speed = e1_speed
        self.e2_speed = e2_speed
        self.rng = np.random.default_rng(seed)
        self.t = 0.0
        self.F = superellipsoid_faces(M, N)

    def step(self, n=1):
        for _ in range(n):
            self.t += 0.016
        return self.mesh()

    def mesh(self):
        e1 = max(0.1, self.e1_init + 1.5 * np.sin(self.t * self.e1_speed))
        e2 = max(0.1, self.e2_init + 1.5 * np.cos(self.t * self.e2_speed))
        V, _, _ = superellipsoid_points(e1, e2, self.M, self.N, self.scale)
        return V, self.F

    def render(self, size=400):
        V, F = self.mesh()
        normals = vertex_normals(V, F)
        H = W = size
        img = np.zeros((H, W, 3), dtype=np.float32)
        for f in F:
            for k in range(3):
                vi = f[k]
                x, y, z = V[vi]
                px = int((x * 0.4 + 0.5) * (W - 1))
                py = int((y * 0.4 + 0.5) * (H - 1))
                if 0 <= px < W and 0 <= py < H:
                    # Shade by the z-normal
                    shade = (normals[vi, 2] + 1) * 0.5
                    img[py, px] = (shade * 0.6, shade * 0.2, shade * 0.9)
        return (img * 255).clip(0, 255).astype(np.uint8)


if __name__ == '__main__':
    sim = SuperEllipsoid(e1=1.0, e2=1.0, M=64, N=32)
    V, F = sim.mesh()
    print('verts:', V.shape, 'faces:', F.shape)
    img = sim.render(size=400)
    print('image:', img.shape, 'nonzero:', int((img.sum(axis=-1) > 0).sum()))
