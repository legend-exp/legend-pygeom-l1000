# Naming conventions

This document describes our naming convention for geometry parts (solids,
volumes, materials, surfaces, ...).

## Volume names

- **snake_case**: Use lowercase with underscores, e.g., `lar`, `fiber_module`,
  `tank_water`
  - **Exception**: Detector names are used as-is from metadata, e.g., `V01234A`,
    `S035`

- **Prefixing related components**: Volumes named after other components should
  prefix their own name to simplify regex selection
  - Example: The PEN plate for detector `V01234A` should be named `pen_V01234A`
  - Example: Mini-shroud for string 1: `nms_1_upper`
  - Example: Support rod for string 2: `rod_2_lower`

- **Multiple instances**: Use numerical suffixes or identifiers
  - Example: `string_1`, `string_2`, `string_3`
  - Example: `calibration_tube_1`, `calibration_tube_2`
  - Example: `pmt_floor_1`, `pmt_wall_15`

## Solids, logical volumes, and physical volumes

- **Naming consistency**: Corresponding solids, logical volumes, and physical
  volumes in GDML should usually have the same name
  - **Exception**: Multiple placements of one logical volume need unique
    physical volume names
  - Example: `tank_water` solid → `tank_water` logical volume → `tank_water`
    physical volume

- **Python variable names**: These don't have to match geometry names but should
  when possible
  - Internal python variables can be more descriptive
  - Example: `lar_cavity_lv` for a logical volume variable that produces
    geometry named `lar`

- **Unique placements**: When placing the same logical volume multiple times,
  append identifiers to physical volume names
  - Example: `fiber_core_inner_1`, `fiber_core_inner_2`, etc.

## Detector names

Detector names follow LEGEND conventions and are preserved from metadata:

- **HPGe detectors**: Format like `V01234A`, `B00089B`, `P00664A`
  - First letter indicates type: V (inverted coaxial), B (BEGe), P (PPC), C
    (coaxial)
  - Numbers identify the specific detector
  - Letter suffix indicates version/configuration

- **SiPMs/Optical detectors**: Format like `S001`, `S035`
  - Numbered sequentially

- **PMTs**: Format like `PMT001`, `PMT_floor_001`
  - May include position information in name

## Materials

Material names use **snake_case** with descriptive prefixes:

- **Metals**: `metal_` prefix
  - Examples: `metal_copper`, `metal_steel`, `metal_aluminum`,
    `metal_germanium_enr`

- **Optical materials**: Often use package names or descriptive terms
  - Examples: `tetratex`, `tpb_on_tetratex`, `liquidargon`, `water`

- **Structural materials**: Descriptive names
  - Examples: `pen`, `nylon`, `kapton`

- **Elements**: Capitalized element names
  - Examples: `Hydrogen`, `Copper`, `Germanium`

## Optical surfaces

Surface names follow specific patterns to indicate their function:

- **OpticalSurface property definitions**: `surface_{from}_to_{to}`
  - Example: `surface_lar_to_tpb`
  - Example: `surface_copper_to_lar`

- **BorderSurface instances**: `bsurface_{from}_{to}` or more descriptive
  - Example: `bsurface_lar_tpb`
  - Example: `bsurface_fiber_core_lar_1`

- **SkinSurface instances**: `ssurface_{volume}` or descriptive name
  - Example: `ssurface_copper_plate`
  - Example: `tank_steel_surface`

## Assembly and component groups

For selective geometry construction:

- **Assembly names**: Single descriptive words or short phrases
  - Examples: `strings`, `calibration`, `watertank`, `cryo`, `fibers`, `wlsr`

- **Grouped components**: Use common prefixes for related volumes
  - Fiber system: `fiber_inner_*`, `fiber_outer_*`
  - HPGe support: `hpge_support_copper_*`, `pen_*`, `nms_*`
  - Calibration: `calibration_tube_*`, `source_*`

## Regular expression patterns

Design names to enable simple regex patterns for volume selection in simulation:

- **All detectors**: `^[VBPC][0-9]{5}[A-Z]$` or `^V.*` for only inverted coaxial
- **All copper structures**: `.*copper.*` or more specific
  `hpge_support_copper.*`
- **All fibers in inner barrel**: `^fiber_inner_.*`
- **All PEN plates**: `^pen_.*`
- **All calibration sources**: `^source_.*` or `^calibration_.*`

## Prefixes for physical volume groups

Use consistent prefixes to enable wildcards:

- **Fibers**:
  - `fiber_inner_` for inner barrel fibers
  - `fiber_outer_` for outer barrel fibers
  - Followed by component type: `tpb`, `core`, `cladding1`, `cladding2`

- **HPGe support structures**:
  - `hpge_support_copper_` for copper rods
  - `pen_` for PEN baseplates
  - `nms_` for nylon mini-shrouds

- **Calibration**:
  - `calibration_tube_` for tubes
  - `source_` for source volumes

- **Water tank instrumentation**:
  - `pmt_floor_` for PMTs on tank floor
  - `pmt_wall_` for PMTs on tank walls
  - `tyvek` for reflector

## Examples

### Good naming practices

```python
# Detector and its components
detector_name = "V01234A"  # From metadata
pen_name = f"pen_{detector_name}"  # → pen_V01234A
rod_name = f"rod_string1_{detector_name}"  # → rod_string1_V01234A

# String components
string_assembly = f"string_{string_number}"  # → string_1
minishroud = f"nms_{string_number}_lower"  # → nms_1_lower

# Fibers with detailed identification
fiber_pv_name = f"fiber_inner_core_straight_length150_idx042"

# Materials
copper_material = "metal_copper"
lar_material = "liquidargon"

# Surfaces
lar_tpb_surface = "surface_lar_to_tpb"
border_surface = "bsurface_lar_tpb_inner_1"
```

### Regex selection examples

For use in remage or other simulation tools:

```python
# Select all HPGe detectors
"^[VBPC][0-9]{5}[A-Z]$"

# Select all PEN plates
"^pen_.*"

# Select all inner barrel fibers
"^fiber_inner_.*"

# Select all copper support structures
".*copper.*"

# Select specific detector type (inverted coaxial)
"^V[0-9]{5}[A-Z]$"

# Select all calibration sources
"^source_.*"
```

## Special cases

### Multiple detail levels

Some volumes may have different implementations at different detail levels but
should maintain consistent naming:

```python
# Same name regardless of detail level
"tank"  # Whether simple cylinder or detailed with flanges
"cryostat"  # Whether simple or with all features
```

### Temporary or construction volumes

Internal construction volumes (not in final geometry) can use more flexible
naming:

```python
# These are used during construction but may not appear in final GDML
temp_union_solid = "temp_union"
construction_volume = "construction_helper"
```

### Version tracking

For geometries with multiple versions, consider:

```python
# Include version or configuration in filename, not volume names
# filename: l1000_v2.3_full.gdml
# volumes still use standard names: "lar", "strings", etc.
```

## Naming checklist

When adding new components, ensure:

- [ ] Volume names use snake_case
- [ ] Related components share common prefix
- [ ] Names enable regex selection where needed
- [ ] Detector names preserved from metadata
- [ ] Material names include type prefix where appropriate
- [ ] Surface names indicate direction/interaction
- [ ] Multiple instances have clear identifiers
- [ ] Naming is consistent with existing components

## References

- For assembly options: See [CLI Usage Guide](cli_usage.md)
- For component descriptions: See [Geometry Components](geometry_components.md)
- For metadata naming: See [Metadata Documentation](metadata.md)
