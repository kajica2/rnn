# toxi_toxiclibs — Karsten Schmidt's toxiclibs / thi.ng

Four algorithms drawn from the **toxiclibs** ecosystem by Karsten
Schmidt (toxi / postspectacular.com, 2007–2015, now continued as
**thi.ng** at codeberg.org/thi.ng). Material collected from the
[2011 toxiclibs.org web archive](https://web.archive.org/web/20111026052555/http://toxiclibs.org/)
and the original blog posts linked from there.

This is the **library / spec** side of the toxiclibs canon — the
Java / JS classes that defined the creative-coding toolkit, not the
openFrameworks demos (those live in `../toxi_openframeworks/`).
Items here tend to be **3D geometry, physics, and procedural fields**;
the oF items are more 2D, color, and pixel-focused.

| # | Sketch | Year | From | Notes |
|---|--------|------|------|-------|
| 1 | `AdditiveWaves3D`  | 2009 | [toxiclibs blog: "Additive waves"](https://web.archive.org/web/2011/http://toxiclibs.org/2009/12/additive-waves/) | 3D heightfield = sum of sine wave generators + FBM noise |
| 2 | `VerletPhysics3D`  | 2008 | [toxiclibs.physics](https://github.com/postspectacular/toxiclibs/tree/master/src.core/toxi/physics/verlet) | Mass-spring 3D cloth, Jakobsen position-based dynamics |
| 3 | `WingedEdgeMesh`   | 2010 | [toxiclibs blog: "Winged-Edge mesh"](https://web.archive.org/web/2011/http://toxiclibs.org/2010/08/wingededge-mesh/) | Half-edge data structure, Loop subdivision, noise displacement |
| 4 | `SuperEllipsoid`   | 2010 | [toxiclibs.geom.SuperEllipsoid](https://codeberg.org/thi.ng/geom) | Sphere ↔ box morphing primitive (e1, e2) |

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

Four `reference.py` modules (pure numpy, no Java / oF dependency),
four `spec.json` files, four `sample.png` files, plus this `README.md`
and a top-level `summary.md`. Total ~4 source modules, ~13 KB of JSON,
4 PNGs.

## Source provenance

The 2011 web archive of toxiclibs.org lists the six original Java
sub-libraries (`audioutils`, `colorutils`, `simutils`, `toxiclibscore`,
`verletphysics`, `volumeutils`) and the blog posts announcing each
major class. Where possible, each item in this collection cites the
specific blog post or github path that introduced the algorithm.

The library continued as **thi.ng** (https://thi.ng) and now lives at
codeberg.org/thi.ng. Several items here (e.g. `SuperEllipsoid`) are
direct ancestors of current `@thi.ng/geom` classes.
