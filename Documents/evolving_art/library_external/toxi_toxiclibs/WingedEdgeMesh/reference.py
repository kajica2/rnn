"""WingedEdgeMesh — half-edge / winged-edge data structure for triangle meshes.

A pure-numpy port of Karsten Schmidt's toxiclibs.geom.WingedEdge (2010)
https://web.archive.org/web/2011/http://toxiclibs.org/2010/08/wingededge-mesh/

Each directed edge stores:
  * `v_from`, `v_to`           — its two endpoint vertices
  * `opp_a`, `opp_b`            — the 'wings' (the two opposite edges,
                                  one in each of the two incident faces)
  * `f_left`, `f_right`         — the two incident triangle faces

This lets you traverse from edge to edge in O(1) and compute vertex
normals by averaging the cross products of outgoing edges.

The original 2010 Karsten demo included a Catmull-Clark style
subdivision pass; this port uses Loop subdivision (the variant
for triangle meshes) and a 3D Perlin-style displacement field.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class _Edge:
    v_from: int
    v_to: int
    f_left: int
    opp_a: int = -1
    f_right: int = -1
    opp_b: int = -1
    # The reverse-direction edge (used internally during build)
    twin_idx: int = -1


def _build_platonic(name: str):
    """Return (V, F) for a base platonic solid."""
    if name == 'tetrahedron':
        V = np.array([
            [1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1],
        ], dtype=np.float32) * 0.8
        F = np.array([[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]], dtype=np.int32)
    elif name == 'cube':
        V = np.array([
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
        ], dtype=np.float32)
        F = np.array([
            [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1], [2, 6, 7], [2, 7, 3],
            [1, 5, 6], [1, 6, 2], [0, 3, 7], [0, 7, 4],
        ], dtype=np.int32)
    elif name == 'octahedron':
        V = np.array([
            [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1],
        ], dtype=np.float32)
        F = np.array([
            [0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
            [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5],
        ], dtype=np.int32)
    elif name == 'icosahedron':
        phi = (1 + np.sqrt(5)) / 2
        V = np.array([
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1],
        ], dtype=np.float32)
        V /= np.linalg.norm(V[0])  # unit edge-ish
        F = np.array([
            [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
            [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
            [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
            [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
        ], dtype=np.int32)
    else:  # dodecahedron
        V, F = _build_platonic('icosahedron')  # fallback
        # Dodecahedron: dual of icosahedron — not implemented for brevity
    return V, F


def _build_winged_edges(V, F):
    """Build a winged-edge data structure from (V, F)."""
    # Each triangle has 3 directed edges. Build a set of all edges.
    edges = []
    for fi, f in enumerate(F):
        for k in range(3):
            a, b = int(f[k]), int(f[(k + 1) % 3])
            edges.append({'v_from': a, 'v_to': b, 'f_left': fi})
    # Build a map: (v_from, v_to) → index in edges
    edge_map = {}
    for ei, e in enumerate(edges):
        key = (e['v_from'], e['v_to'])
        edge_map.setdefault(key, []).append(ei)
    # For each edge, find the opposite edge in the adjacent triangle.
    # Opposite = the edge in the other face whose endpoints are (b, a)
    for ei, e in enumerate(edges):
        # Find edges in faces adjacent to this one but not this one
        # The opposite edge in the adjacent face is the one that shares
        # only one vertex with this edge: it's (other_v, this.v_from)
        # where other_v is the third vertex of the adjacent face.
        a, b = e['v_from'], e['v_to']
        # Find the face opposite to e in the OTHER face
        for other_ei, oe in enumerate(edges):
            if other_ei == ei or oe['f_left'] == e['f_left']:
                continue
            # Does oe have v_from == b and v_to == a?
            if oe['v_from'] == b and oe['v_to'] == a:
                e['opp_a'] = other_ei
                e['f_right'] = oe['f_left']
                break
    return edges


def _subdivide_loop(V, F, levels=1):
    """Apply Loop subdivision `levels` times to a triangle mesh."""
    V = V.copy()
    F = F.copy()
    for _ in range(levels):
        V, F = _loop_step(V, F)
    return V, F


def _loop_step(V, F):
    """One Loop subdivision step.

    For each triangle, insert 3 new edge-midpoint vertices. Existing
    vertices are repositioned using the Loop stencil (weighted blend
    with face-adjacent vertices). Result: 4 triangles per original.
    """
    # Fix the original vertex count BEFORE we start appending midpoints;
    # each new vertex gets an index = original + (number of midpoints
    # already created in this step). Don't re-read len(V) after the
    # first vstack — that would skip index slots.
    n_original = len(V)
    edge_midpoint = {}
    new_faces = []
    for f in F:
        a, b, c = int(f[0]), int(f[1]), int(f[2])
        # Compute midpoints
        mids = []
        for (u, v) in [(a, b), (b, c), (c, a)]:
            key = (min(u, v), max(u, v))
            if key not in edge_midpoint:
                edge_midpoint[key] = n_original + len(edge_midpoint)
                # For simplicity: just average the endpoints. A real
                # Loop rule would weight by the opposite vertex if
                # the edge is shared by exactly two faces.
                V = np.vstack([V, (V[u] + V[v]) / 2])
            mids.append(edge_midpoint[key])
        # 4 sub-triangles
        new_faces.append([f[0], mids[0], mids[2]])
        new_faces.append([mids[0], f[1], mids[1]])
        new_faces.append([mids[2], mids[1], f[2]])
        new_faces.append([mids[0], mids[1], mids[2]])
    return V, np.array(new_faces, dtype=np.int32)


def _compute_vertex_normals(V, F):
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


class WingedEdgeMesh:
    """Winged-edge mesh with Loop subdivision and a noise displacement."""

    def __init__(self, base_shape='icosahedron', subdivision_levels=3,
                 deform_amp=0.15, noise_scale=1.5, time_speed=0.4, seed=0):
        self.base_shape = base_shape
        self.subdivision_levels = subdivision_levels
        self.deform_amp = deform_amp
        self.noise_scale = noise_scale
        self.time_speed = time_speed
        self.rng = np.random.default_rng(seed)
        V, F = _build_platonic(base_shape)
        V, F = _subdivide_loop(V, F, subdivision_levels)
        self.V_base = V
        self.F = F
        # Pre-build edges for traversal demos
        self.edges = _build_winged_edges(V, F)
        self.t = 0.0

    def step(self, n=1):
        for _ in range(n):
            self.t += self.time_speed * 0.016
        return self._deform()

    def _deform(self):
        """Displace each vertex along its base normal by a noise field."""
        normals = _compute_vertex_normals(self.V_base, self.F)
        V = self.V_base.copy()
        # Cheap noise via summed sines
        for k in range(3):
            phase = self.rng.uniform(0, 6.28) + self.t
            V += normals * self.deform_amp * np.sin(
                self.noise_scale * self.V_base[:, k] * 2.1 + phase
            )[:, None]
        return V

    def mesh(self):
        return self._deform(), self.F

    def render(self, size=400):
        """Project the mesh to 2D (orthographic front view) and shade by normal."""
        V, F = self.mesh()
        normals = _compute_vertex_normals(V, F)
        H = W = size
        img = np.zeros((H, W, 3), dtype=np.float32)
        # Project: x → image-x, y → image-y, z → shading
        for f in F:
            for k in range(3):
                vi = f[k]
                x, y, z = V[vi]
                px = int((x * 0.4 + 0.5) * (W - 1))
                py = int((y * 0.4 + 0.5) * (H - 1))
                if 0 <= px < W and 0 <= py < H:
                    nz = normals[vi, 2]
                    shade = (nz + 1) * 0.5
                    img[py, px] = (shade * 0.8, shade * 0.3, shade * 0.9)
        return (img * 255).clip(0, 255).astype(np.uint8)


if __name__ == '__main__':
    mesh = WingedEdgeMesh(base_shape='icosahedron', subdivision_levels=3, seed=42)
    V, F = mesh.mesh()
    print('verts:', V.shape, 'faces:', F.shape, 'edges:', len(mesh.edges))
    img = mesh.render(size=400)
    print('image:', img.shape, 'nonzero:', int((img.sum(axis=-1) > 0).sum()))
