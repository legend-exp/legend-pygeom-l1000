# Geometry Components

The LEGEND-1000 geometry consists of multiple assemblies, each representing a
major structural or functional component of the detector. This page describes
the key components, their naming conventions, materials, and physical
characteristics.

## Overview of Assemblies

The geometry is organized into the following main assemblies:

- **World**: The outermost container volume filled with vacuum (G4_Galactic)
- **Cavern and Labs**: Underground laboratory infrastructure
- **Water Tank**: Outer water shield and supporting structure
- **Water Tank Instrumentation**: PMTs and optical detectors in the water
- **Cryostat**: Multi-layer cryogenic containment system
- **Liquid Argon**: Active LAr veto volume
- **WLSR**: Wavelength-shifting reflector system
- **HPGe Strings**: High-purity germanium detector arrays
- **Calibration System**: Radioactive source deployment system
- **Fibers**: Light guide system

## Detail Levels

Each assembly can be constructed at different levels of detail. The available
detail levels are:

### Simple

Minimal geometry with basic shapes and materials. Suitable for:

- Quick visualization checks
- Fast simulation for testing
- Preliminary studies

### Radiogenic (Default)

Includes all components relevant for radiogenic background studies:

- Accurate material compositions
- Key structural elements that contribute to backgrounds
- Proper surface treatments where relevant
- Balance between completeness and simulation speed

### Full

Complete geometry with maximum detail:

- All structural elements included
- Detailed material compositions
- Fine surface treatments
- Hardware mounting structures
- Most realistic representation (slower simulation)

## Major Components

### Water Tank

**Purpose**: Outer active muon veto and passive shielding

**Materials**:

- Tank body: Stainless steel (metal_steel)
  - Composition: Fe (65.75%), Cr (17.5%), Ni (11.5%), Mo (2.25%), Mn (2%), Si
    (1%)
  - Density: 7.9 g/cm³
- Water: Ultra-pure water with optical properties
  - Optical absorption and scattering included
  - Refractive index wavelength-dependent

**Geometry Features**:

- Cylindrical base section
- Bulge sections for additional volume
- Multiple flanges for access ports
- Manhole covers for maintenance access

**Detail-dependent features**:

- `simple`: Basic cylinder, no flanges or manholes
- `radiogenic`: Includes major structural features
- `full`: All flanges, manholes, and detailed features

**Naming Convention**:

- Tank volume: `tank`
- Water volume: `tank_water`
- Individual flanges: `tank_flange_N` (where N is the flange number)

### Cryostat

**Purpose**: Thermal isolation and containment for liquid argon

**Structure**: Multi-layer system consisting of:

1. **Outer Cryostat**:
   - Material: Stainless steel (metal_steel)
   - Complex polycone shape with neck and barrel sections
   - Contains vacuum gap for insulation

2. **Vacuum Gap**:
   - Material: Vacuum (G4_Galactic)
   - Provides thermal insulation between outer and inner cryostats

3. **Inner Cryostat**:
   - Material: Copper (metal_copper)
   - Density: 8.96 g/cm³
   - Direct contact with liquid argon
   - Includes moderator sections

4. **Top Copper Plates**:
   - Material: Copper
   - Thick plates for structural support and detector mounting
   - Includes cutouts for detector strings

**Naming Convention**:

- Outer cryostat: `outercryostat`
- Vacuum gap: `vacuum_gap`
- Inner cryostat: `innercryostat`
- Copper moderator: `moderator`
- Top plates: `top_copper_plate`

### Liquid Argon

**Purpose**: Active veto medium and cooling

**Material**: Liquid argon (LiquidArgon)

- Density: 1.390 g/cm³
- Temperature: 88.8 K
- Pressure: 1.0 bar

**Optical Properties**:

- Refractive index: wavelength-dependent, ~1.23 at 128 nm
- Attenuation length: temperature-dependent
- Scintillation properties:
  - Primary emission at 128 nm
  - Singlet lifetime: ~6 ns
  - Triplet lifetime: ~1.5 μs (using LEGEND-200 LLAMA measurements)

**Naming Convention**:

- Main LAr volume: `LArCavity` or `lar_cavity`

### WLSR (Wavelength-Shifting Reflector)

**Purpose**: Convert VUV scintillation light to visible and reflect it toward
detectors

**Structure**: Two-layer system

1. **TPB Layer** (Inner layer):
   - Material: TPB on Tetratex (tpb_on_tetratex)
   - Function: Wavelength shifting from 128 nm to ~420 nm
   - Tetraphenyl butadiene coating on reflective substrate

2. **Tetratex Layer** (Outer layer):
   - Material: Expanded PTFE (tetratex)
   - Function: High reflectivity in visible range
   - Diffuse reflector

**Configurations**:

- **Inner WLSR**: Inside the LAr volume, surrounds detector array
- **Outer WLSR**: In atmospheric pressure region outside inner cryostat

**Optical Surfaces**:

- LAr to TPB interface: Absorption and re-emission
- TPB to Tetratex interface: Reflective properties
- Tetratex to surrounding medium: High reflectivity

**Naming Convention**:

- Inner TPB: `wls_tpb_inner_argon_lv`
- Inner Tetratex: `wls_tetratex_inner_argon_lv`
- Outer TPB: `wls_tpb_outer_atmospheric_lv`
- Outer Tetratex: `wls_tetratex_outer_atmospheric_lv`

### HPGe Detector Strings

**Purpose**: Primary signal detectors for neutrinoless double-beta decay search

**Components**:

1. **HPGe Detectors**:
   - Material: Enriched germanium (metal_germanium_enr)
   - Enrichment: ~86% Ge-76
   - Various geometries: ICPC, BEGe, PPC, Coaxial
   - Can use real detector geometries from legend-metadata

2. **Mini-Shrouds** (NMS):
   - Material: Copper (metal_copper)
   - Purpose: Local shielding and support
   - Cylindrical structure around each detector or detector pair
   - Configurable radius per string

3. **Support Rods**:
   - Material: Copper
   - Connect detectors to top copper plate
   - Length adjusts with temperature (thermal contraction factor applied)

4. **Baseplates**:
   - Material: PEN (polyethylene naphthalate) with optical properties
   - Sizes: small, medium, large, xlarge
   - Support and insulate detectors

**String Configuration**:

- Radial position: Defined in special_metadata per string
- Azimuthal angle: Defined in special_metadata per string
- Number of strings: Configurable
- Detectors per string: Configurable

**Naming Convention**:

- String assembly: `string_N` (where N is the string number)
- Individual detector: `det_DETECTOR_NAME` (from channelmap)
- Mini-shroud: `nms_N_M` (string N, position M)
- Support rods: `rod_N_M`

### Calibration System

**Purpose**: Deploy radioactive sources for detector calibration

**Components**:

1. **Calibration Tubes**:
   - Material: Typically aluminum or copper
   - Vertical tubes positioned around detector array
   - Extend from top copper plate downward

2. **Source Holders**:
   - Material: Various (depending on source type)
   - Deployable along calibration tubes

**Configuration**:

- Number of tubes: Configurable
- Radial positions: Defined in special_metadata
- Azimuthal angles: Defined in special_metadata
- Tube radius: Configurable per tube
- Tube length: Configurable per tube

**Naming Convention**:

- Calibration tube: `calibration_tube_N`
- Source holder: `source_holder_N`

### Water Tank Instrumentation

**Purpose**: Detect Cherenkov light from muons in water

**Components**:

1. **PMTs** (Photomultiplier Tubes):
   - Optical properties for quartz windows
   - Realistic geometries or simplified cylinders
   - Arranged on tank walls

2. **Tyvek Reflector**:
   - Material: Reflective Tyvek
   - Purpose: Enhance light collection
   - Configuration: Polycone shape dividing tank

**Configuration**:

- PMT positions: Defined in channelmap
- Tyvek geometry: Faces, radius defined in special_metadata

**Naming Convention**:

- PMTs: `pmt_N`
- Tyvek: `tyvek`

### Fiber System

**Purpose**: Transport scintillation/Cherenkov light to SiPMs

**Material**: Optical fibers with:

- Core: PMMA or polystyrene with refractive index
- Cladding: Lower refractive index for total internal reflection
- Optical properties from pygeomoptics.fibers

**Naming Convention**:

- Fiber bundles: `fiber_bundle_N`
- Individual fibers: `fiber_N_M`

## Material Summary

### Metals

| Material                        | Density (g/cm³) | Key Properties                           | Usage                   |
| ------------------------------- | --------------- | ---------------------------------------- | ----------------------- |
| Copper (metal_copper)           | 8.96            | High purity, excellent thermal conductor | Cryostat, shields, rods |
| Stainless Steel (metal_steel)   | 7.9             | Corrosion resistant                      | Tank, outer cryostat    |
| Germanium (metal_germanium_enr) | 5.323           | 86% Ge-76 enriched                       | Detectors               |
| Aluminum (metal_aluminum)       | 2.70            | Lightweight structural                   | Various supports        |
| Silicon (metal_silicon)         | 2.33            | Semiconductor                            | SiPMs (if implemented)  |
| Tantalum (metal_tantalum)       | 16.69           | High density                             | Shielding               |

### Optical Materials

| Material     | Key Optical Properties                | Usage              |
| ------------ | ------------------------------------- | ------------------ |
| Liquid Argon | n≈1.23 @ 128nm, scintillation @ 128nm | Active veto        |
| TPB          | Wavelength shifter 128nm→420nm        | WLSR inner layer   |
| Tetratex     | High reflectivity, diffuse            | WLSR outer layer   |
| PEN          | Transparent, wavelength shifter       | Baseplates         |
| Water        | n≈1.33, Cherenkov medium              | Muon veto          |
| Nylon        | Transparent, low background           | Various structures |

### Structural Materials

| Material             | Density (g/cm³)          | Usage               |
| -------------------- | ------------------------ | ------------------- |
| Vacuum (G4_Galactic) | ~0                       | World, vacuum gaps  |
| Air                  | Standard air composition | Atmospheric regions |

## Surface Properties

The geometry implements several optical surface types:

1. **to_copper**: Metal surfaces on copper components
2. **to_tyvek**: Reflective surfaces on Tyvek
3. **lar_to_tpb**: LAr to TPB interface with wavelength shifting
4. **wlsr_tpb_to_tetratex**: TPB to Tetratex interface

These surfaces control optical photon behavior at boundaries, including:

- Reflection (specular, diffuse, or mixed)
- Absorption
- Wavelength shifting
- Detection efficiency

## Assembly Selection

When using `--assemblies`, you can select specific components:

```console
legend-pygeom-l1000 --assemblies watertank,cryo,hpge_strings l1000.gdml
```

This generates only the specified assemblies, which is useful for:

- Focused visualization of specific components
- Faster generation for testing specific areas
- Reduced file size for simplified simulations
- Debugging individual assembly construction

## Customization

See the [Metadata Documentation](metadata.md) for details on customizing:

- String positions and configurations
- Detector types and arrangements
- Calibration tube locations
- Material properties via custom plugins

## Coordinate System

The geometry uses the following coordinate system:

- **Origin**: Center of the detector array at the cryostat center
- **Z-axis**: Vertical, pointing upward
- **X-axis and Y-axis**: Horizontal plane
- **Units**: Millimeters (mm) for lengths

## Naming Conventions

General naming patterns:

- Physical volumes: Descriptive names with underscores (e.g., `tank_water`)
- Multiple instances: Append number or identifier (e.g., `string_1`,
  `det_V000001A`)
- Material prefix: `metal_`, `optical_` to indicate type
- Assembly groups: Logical grouping for selective construction

## Further Reading

- For metadata configuration details: [Metadata Documentation](metadata.md)
- For visualization: [Visualization Guide](visualization.md)
- For CLI usage: [CLI Usage Guide](cli_usage.md)
