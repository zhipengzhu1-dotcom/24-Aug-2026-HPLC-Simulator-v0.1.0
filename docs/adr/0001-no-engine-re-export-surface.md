---
status: accepted
date: 2026-09-04
ticket: "#88 — architecture review 2026-09-04"
---

# The engine has no top-level re-export surface

`src/hplcsim/__init__.py` exports only `__version__`. Callers import each name
from the submodule that defines it (`hplcsim.model`, `hplcsim.retention`,
`hplcsim.fit`, `hplcsim.width`, `hplcsim.resolution`, `hplcsim.dead_time`,
`hplcsim.session`). The 2026-09-04 architecture review (#88) proposed giving the
engine a flat top-level interface — an `__all__` in the package `__init__`
re-exporting the public names — and rejected it. This record exists so the next
review does not re-suggest it.

## Why it was rejected

- **It would not shrink the interface, only relocate it.** Measured on
  2026-09-04 across `app/`, `streamlit_app.py`, `tests/` and `scripts/`:
  59 distinct engine symbols on 81 `from hplcsim… import` lines (the review's
  own count, before #92 and #93 landed, was 57 across 76). A flat `__all__`
  leaves every one of those names in use; it changes only the string after
  `from`.
- **It would hide where a name lives.** `hplcsim.dead_time.POROSITY` tells the
  reader which module owns the constant and which SPEC section governs it;
  `hplcsim.POROSITY` does not. The module path is documentation the re-export
  would erase.
- **The interface of record already exists.** SPEC §9's module map lists each
  engine module with its exported entry points and return types. A second,
  flat listing in `__init__.py` would have to be kept in step with it by hand
  and would drift.
- **The deep-module case does not apply.** A re-export layer adds no behaviour
  behind a smaller interface; it is a shallow module by construction — its
  interface is the whole of its implementation.

## Consequences

- `__init__.py` stays as it is: a docstring, the package's own version, nothing
  else. Adding a public name to the engine means adding it to a submodule and,
  if it is an entry point, to SPEC §9's map.
- `from hplcsim import model` (importing a submodule as a namespace) remains
  fine; it is not a re-export.
- Revisit only if the engine grows a caller outside this repo that needs a
  stability contract narrower than "the submodules". That caller does not exist
  in v0.2.
