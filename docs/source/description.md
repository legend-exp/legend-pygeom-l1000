# Description of the geometry

This section provides detailed descriptions of the geometry components, with a
particular focus on the names of physical volumes and their organization.

```{note}
The geometry can be constructed at different detail levels. The descriptions here generally refer to the `radiogenic` or `full` detail levels. See {doc}`geometry_components` for detail level information.
```

## Assemblies overview

The LEGEND-1000 geometry is divided into several assemblies that can be
selectively included. See {doc}`cli_usage` for information on selecting specific
assemblies.

Available assemblies:

- `watertank`: Water tank and surrounding infrastructure
- `cryo`: Cryostat system (always included)
- `hpge_strings`: HPGe detector arrays
- `calibration`: Calibration system
- `wlsr`: Wavelength-shifting reflector
- `fibers`: Light guide system (if implemented)
- `watertank_instrumentation`: PMTs and optical detectors

## Cryostat system

The cryostat is the central component and is **always included** in the
geometry.

### Structure

The cryostat consists of multiple layers:

#### Outer cryostat

- **Physical volume**: `outercryostat`
- **Material**: Stainless steel (`metal_steel`)
- **Shape**: Complex polycone (neck and barrel sections)
- **Function**: Structural containment and vacuum boundary

#### Vacuum gap

- **Physical volume**: `vacuum_gap`
- **Material**: Vacuum (`G4_Galactic`)
- **Function**: Thermal insulation between cryostat layers

#### Inner cryostat

- **Physical volume**: `innercryostat`
- **Material**: Copper (`metal_copper`)
- **Shape**: Polycone matching internal argon volume
- **Function**: Direct contact with liquid argon, inner radiation shield

#### Copper moderator

- **Physical volume**: `moderator`
- **Material**: Copper (`metal_copper`)
- **Function**: Additional shielding and structural support
- **Location**: Top portion of inner cryostat

#### Top copper plates

- **Physical volumes**: `top_copper_plate`, `top_plate_upper`, etc.
- **Material**: Copper (`metal_copper`)
- **Function**: Support structure for detector strings
- **Features**: Includes cutouts for string passages

### Liquid argon

- **Physical volume**: `lar` or `LArCavity`
- **Material**: Liquid argon (`LiquidArgon`)
- **Properties**:
  - Density: 1.390 g/cm³
  - Temperature: 88.8 K
  - Active scintillation medium
  - Optical properties for light propagation

The LAr volume serves as the mother volume for most internal components
(detector strings, calibration tubes, WLSR, etc.).

## HPGe detector strings

The `strings` assembly contains the germanium detector array and support
structures.

### Detector naming

HPGe detectors use their **metadata names directly** as physical volume names:

- **Examples**: `V01234A`, `B00089B`, `P00664A`
- **Selection in remage**: Use detector names or patterns like `^V.*` for
  inverted coaxial detectors

### Support structures

#### PEN baseplates

- **Naming pattern**: `pen_{DETECTOR_NAME}`
- **Examples**: `pen_V01234A`, `pen_B00089B`
- **Material**: PEN (polyethylene naphthalate) with optical properties
- **Sizes**: `small`, `medium`, `large`, `xlarge` (configured per detector)
- **Function**: Detector support and optical coupling

#### Copper support rods

- **Naming pattern**: `rod_{STRING}_{POSITION}` or
  `hpge_support_copper_{STRING}_{POSITION}`
- **Material**: Copper (`metal_copper`)
- **Function**: Mechanical support connecting detectors to top plate
- **Note**: Lengths account for thermal contraction

#### Mini-shrouds (NMS)

- **Naming pattern**: `nms_{STRING}_upper`, `nms_{STRING}_lower`, etc.
- **Material**: Typically nylon or copper
- **Function**: Local shielding around detectors
- **Configuration**: Radius and length per string in special_metadata

### String organization

- **String assemblies**: `string_1`, `string_2`, `string_3`, ...
- **Positioning**: Radial and azimuthal coordinates from special_metadata
- **Detector count**: Configurable number of detectors per string
- **Vertical spacing**: Typically 140-150 mm between detector units

### Selection patterns

Useful regex patterns for string components:

- All HPGe detectors: `^[VBPC][0-9]{5}[A-Z]$`
- All PEN plates: `^pen_.*`
- All copper rods: `.*copper.*` or `^rod_.*`
- All minishrouds: `^nms_.*`
- Specific string: `.*string_1.*`

## Wavelength-shifting reflector (WLSR)

The `wlsr` assembly surrounds the detector array with wavelength-shifting and
reflective layers.

### Inner WLSR (in LAr)

#### TPB layer

- **Physical volumes**: `wls_tpb_inner_argon_lv` or similar
- **Material**: TPB on Tetratex (`tpb_on_tetratex`)
- **Function**: Wavelength shift from 128 nm (LAr scintillation) to ~420 nm
- **Configuration**: Cylindrical surface around detector array

#### Tetratex layer

- **Physical volumes**: `wls_tetratex_inner_argon_lv` or similar
- **Material**: Expanded PTFE (`tetratex`)
- **Function**: High reflectivity in visible spectrum
- **Properties**: Diffuse reflector

### Outer WLSR (atmospheric)

Similar two-layer structure in the atmospheric pressure region outside the inner
cryostat:

- **TPB layer**: `wls_tpb_outer_atmospheric_lv`
- **Tetratex layer**: `wls_tetratex_outer_atmospheric_lv`

### Optical surfaces

Critical interfaces between layers:

- `lar_to_tpb`: LAr/TPB interface with wavelength shifting
- `wlsr_tpb_to_tetratex`: TPB/Tetratex interface
- Additional surfaces for light collection optimization

## Calibration system

The `calibration` assembly provides radioactive source deployment capability.

### Calibration tubes

- **Naming pattern**: `calibration_tube_{NUMBER}`
- **Examples**: `calibration_tube_1`, `calibration_tube_2`
- **Material**: Typically aluminum or copper
- **Configuration**: Position (radius, angle) and dimensions from
  special_metadata
- **Function**: Guide tubes for source deployment

### Source holders and positions

- **Naming pattern**: `source_holder_{NUMBER}` or `source_{NUMBER}`
- **Configuration**: Deployment positions along tubes
- **Note**: Actual radioactive material not included in geometry; specified in
  simulation macros

### Positioning

- **Radial**: Typically outside detector array (e.g., 650 mm radius)
- **Azimuthal**: Between detector strings for uniform coverage
- **Vertical**: Extends from top plate to below lowest detectors
- **Configuration**: See {doc}`metadata` for customization

## Water tank

The `watertank` assembly provides muon veto and passive shielding.

### Tank structure

- **Physical volume**: `tank`
- **Material**: Stainless steel (`metal_steel`)
- **Shape**: Cylindrical with flanges and manholes (at higher detail levels)

### Water volume

- **Physical volume**: `tank_water`
- **Material**: Water with optical properties
- **Function**: Cherenkov radiator for muon detection

### Detail-dependent features

- **Simple**: Basic cylinder
- **Radiogenic/Full**: Includes flanges, manholes, support structures

## Water tank instrumentation

The `watertank_instrumentation` assembly includes optical detectors in the
water.

### PMTs

- **Naming pattern**: `pmt_floor_{NUMBER}`, `pmt_wall_{NUMBER}`
- **Configuration**: Positions from special_metadata (rows, radii, heights)
- **Material**: Optical properties for photocathode and window
- **Function**: Detect Cherenkov light from muons

### Tyvek reflector

- **Physical volume**: `tyvek`
- **Material**: Reflective Tyvek
- **Shape**: Polycone dividing tank into regions
- **Configuration**: Number of faces and radius from special_metadata
- **Function**: Enhance light collection uniformity

## Fiber system

If implemented in the geometry:

### Fiber modules

- **Naming pattern**: `fiber_inner_*`, `fiber_outer_*`
- **Components**: Core, cladding layers, TPB coating
- **Function**: Light guides for scintillation photons
- **Configuration**: Module positions and types

### SiPMs

- **Naming pattern**: Detector names (e.g., `S001`, `S035`)
- **Function**: Light detection at fiber ends
- **Material**: Silicon with optical detection properties

## Cavern and laboratories

When included (not omitted):

### Cavern structure

- **Physical volumes**: `cavern`, `rock`, etc.
- **Material**: Rock composition
- **Function**: Represent underground location

### Laboratory rooms

- **Physical volumes**: `lab_hall`, `clean_room`, etc.
- **Function**: Experimental hall structure
- **Detail**: Usually simplified geometry

## Volume hierarchy

Typical nesting structure:

```
world (G4_Galactic)
└── tank (metal_steel) [if included]
    └── tank_water (water) [if included]
        └── outercryostat (metal_steel)
            └── vacuum_gap (G4_Galactic)
                └── innercryostat (metal_copper)
                    └── lar (LiquidArgon)
                        ├── wlsr (TPB, Tetratex)
                        ├── string_1
                        │   ├── V01234A (detector)
                        │   ├── pen_V01234A (PEN)
                        │   ├── rod_1_upper (copper)
                        │   └── nms_1_lower (nylon/copper)
                        ├── string_2
                        │   └── ...
                        └── calibration_tube_1
```

## Tips for volume selection

### In remage macros

Select volumes by pattern for particle generation or scoring:

```
# All HPGe detectors
/RMG/Generator/Confinement/Physical/AddVolume ^[VBPC][0-9]{5}[A-Z]$

# All LAr volume
/RMG/Generator/Confinement/Physical/AddVolume ^lar$

# All copper structures
/RMG/Generator/Confinement/Physical/AddVolume .*copper.*

# Specific string
/RMG/Generator/Confinement/Physical/AddVolume .*string_1.*
```

### For visualization

Use volume name patterns to show/hide components:

```
# Hide all PEN plates
pen_.*: [0, 0, 0, 0]  # Fully transparent

# Show only detectors
^[VBPC].*: [default color, full opacity]
```

## Cross-references

- Component details: {doc}`geometry_components`
- Naming conventions: {doc}`naming`
- Coordinate system: {doc}`coordinate_systems`
- Configuration: {doc}`metadata`
- Visualization: {doc}`visualization`
