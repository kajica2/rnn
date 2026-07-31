# toxi_toxiclibs — summary

Four algorithms / data structures from the original toxiclibs Java
library by Karsten Schmidt, hand-picked from the 2011 web archive of
toxiclibs.org. Each is a pure-numpy Python port.

| # | Sketch | Year | Math | Complexity | Notes |
|---|--------|------|------|------------|-------|
| 1 | `AdditiveWaves3D` | 2009 | Σ wᵢ(x,y,t) + FBM noise → heightfield | low | the canonical "additive waves" demo from the 2009 blog post |
| 2 | `VerletPhysics3D` | 2008 | Verlet integration + Jakobsen PBD constraint relaxation | medium | 3D mass-spring cloth; 2D sibling in `toxi_openframeworks/ParticleSpring2D` |
| 3 | `WingedEdgeMesh`  | 2010 | Half-edge data structure + Loop subdivision + noise displacement | medium | per-edge `opp_a/opp_b` pointers; Catmull-Clark → Loop on triangle meshes |
| 4 | `SuperEllipsoid`  | 2010 | sign(cos η)^e1 · sign(cos ω)^e2 parametric form | low | sphere (e=1) ↔ box (e≈4) morph; same parameterization as the 1984 Mac "S" icon |

## Code layout

```
library_external/toxi_toxiclibs/
  README.md
  summary.md
  AdditiveWaves3D/             {reference.py, spec.json, sample.png}
  VerletPhysics3D/             {reference.py, spec.json, sample.png}
  WingedEdgeMesh/              {reference.py, spec.json, sample.png}
  SuperEllipsoid/              {reference.py, spec.json, sample.png}
```

Four `reference.py` modules, four `spec.json` files, four
`sample.png` files, plus this `summary.md` and a top-level
`README.md`.

## Source provenance

- `AdditiveWaves3D` — Karsten Schmidt, [toxiclibs.org blog,
  December 21 2009](https://web.archive.org/web/2011/http://toxiclibs.org/2009/12/additive-waves/).
  Originally packaged with the `toxiclibscore-0011` release as a
  "wave-driven 3D terrain" demo. The algorithm is the canonical
  "additive waves" pattern: sum of sine generators with different
  freq / phase / speed, plus an FBM noise layer.

- `VerletPhysics3D` — Karsten Schmidt, [toxiclibs.physics, 2008](https://github.com/postspectacular/toxiclibs/tree/master/src.core/toxi/physics/verlet).
  Pure Verlet integration of a 3D mass-spring system with Jakobsen
  position-based dynamics constraint relaxation. Algorithm after
  Thomas Jakobsen, "Hitman — A New Cloth Simulation" (GDC 2001).
  The 2D version is in `toxi_openframeworks/ParticleSpring2D`.

- `WingedEdgeMesh` — Karsten Schmidt, [toxiclibs.org blog, August 7
  2010](https://web.archive.org/web/2011/http://toxiclibs.org/2010/08/wingededge-mesh/).
  The Winged-Edge data structure was Bruce Baumgart's 1975
  Stanford AI memo "Winged-Edge Polyhedron Representation" — a
  half-edge-style adjacency graph. Karsten's Java port added
  Loop subdivision (the triangle-mesh sibling of Catmull-Clark)
  and a 3D Perlin displacement field.

- `SuperEllipsoid` — Heinrich Piening / Karsten Schmidt,
  [toxiclibs.geom.SuperEllipsoid, 2010](https://codeberg.org/thi.ng/geom).
  Originally popularised by Ken Perlin in the 1980s as a
  generalisation of the super-quadric; famously used by Susan Kare
  in the 1984 Macintosh "S" icon. The two exponents (e1, e2)
  smoothly morph a sphere → box → astroid.
