# Naming conventions

This document defines the naming convention for geometry parts: solids, volumes,
materials and surfaces. The convention mirrors {doc}`legend-pygeom-l200:naming`.
Regular expressions written for one geometry therefore also should work on the
other.

- **volume names**:
  - Use snake_case, for example `cavern_air` or `hpge_cable_hv`.
    - Exception: use **detector names** as they are, for example `V0101`,
      `S0101T` or `PMT0101`.
  - Follow the scheme `[<group>_]<component>[_<material>][_<extra>]`. Start with
    the group, then the component, for example `hpge_string_support_rod_copper`
    for the copper support rods that hold a detector string. This lets _remage_
    select all volumes of one type with a simple wildcard or regular expression.
  - The material is a token of its own. A regex such as `.*_copper_.*` therefore
    selects every copper part in every subsystem. The same pattern works for any
    material token.
- **corresponding solids, logical volumes and physical volumes** in GDML usually
  share one name.
  - Exception: several placements of one logical volume need unique physical
    volume names.
  - Exception: the intermediate solids of a boolean chain carry a step suffix,
    for example `_outer_bound`, `_inner_bound`, `_part1`, `_step1` or
    `_wo_buffer`. Only the final solid of the chain carries the name of the
    logical volume.
- **surfaces**:
  - `surface_{from}_to_{to}` for OpticalSurfaces (property definition)
  - `bsurface_{from}_{to}` for border surfaces, `ssurface_{to}` for skin
    surfaces

## Group prefixes used in this geometry

| group prefix                              | scope                                                                   |
| ----------------------------------------- | ----------------------------------------------------------------------- |
| `hpge_assembly_`                          | parts of a single detector unit (PEN plate, clamps, ASIC, insulators)   |
| `hpge_string_support_`                    | per-string support structure (hanger, tristar, rods, weldments)         |
| `hpge_cable_`                             | signal and HV cables of a detector unit                                 |
| `fiber_`                                  | the fiber curtain itself (cladding, core, TPB coating)                  |
| `larinstr_undergroundlar_`                | non-optical LAr instrumentation hardware (SiPMs and their copper wraps) |
| `larinstr_atmosphericlar_`                | (not yet implemented)                                                   |
| `waterinstr_`                             | water tank instrumentation (Tyvek reflector, PMTs)                      |
| `cryostat_`                               | cryostat vessels, insulation vacuum, skirt and foot                     |
| `reentrance_tube_`                        | the reentrance tube and its metal layers                                |
| `underground_wlsr_` / `atmospheric_wlsr_` | the two wavelength-shifting reflectors                                  |
| `liquid_argon_`                           | the two liquid argon volumes                                            |
| `watertank_`                              | the water tank steel shell and the water inside it                      |
| `cavern_`                                 | the cavern air volume                                                   |
| `neutron_moderator_`                      | the neutron moderator                                                   |
| _(no prefix)_                             | `world`, `rock`, and all detector/channel names                         |
