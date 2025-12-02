# Coordinate systems

## Internal coordinate system inside LAr volume

The internal coordinate system used for detector positions is centered at the
**center of the cryostat** at the level of the **top copper plate** (more
precisely, the top surface of the copper moderator/inner cryostat).

### Coordinate axes

- **Origin**: Center of the detector array, at the top surface of the copper
  moderator
- **Z-axis**: Vertical axis
  - Positive direction: **Downward** into the liquid argon
  - z = 0: Top surface of the copper moderator
  - Negative z: Above the copper plate (rare, only for some calibration
    components)
- **X-axis and Y-axis**: Horizontal plane
  - Form a right-handed coordinate system with the Z-axis
  - Azimuthal angles are measured from the positive X-axis
  - 0° = +X axis direction
  - 90° = +Y axis direction
  - 180° = -X axis direction
  - 270° = -Y axis direction

### Radial and azimuthal coordinates

For cylindrically symmetric components (strings, calibration tubes), positions
are often specified using:

- **r** (radius): Distance from the Z-axis in the XY plane (mm)
- **φ** (phi, angle): Azimuthal angle measured from +X axis in degrees

**Example**: A string at `radius_in_mm: 500` and `angle_in_deg: 45` is
positioned at:

- Cartesian: (353.6, 353.6, z) mm
- Located at 45° between +X and +Y axes

### Vertical positions

Detector unit positions along strings are specified by:

- **String position index**: 1, 2, 3, ... (counted from top to bottom)
- **Vertical spacing**: Defined by `units.l` parameter in config (typically ~140
  mm)
- **Z coordinate**: Calculated as `top_plate_z_pos + position_index × spacing`

## Global coordinate system

The global coordinate system (used when watertank and cavern are included)
extends the internal coordinate system:

### World volume

The world volume is a large box filled with vacuum (G4_Galactic) that contains
all geometry components.

### Water tank positioning

The water tank is positioned such that:

- Its center aligns with the cryostat center in the XY plane
- The vertical positioning is adjusted so the cryostat sits at the appropriate
  height within the tank
- The tank extends both above and below the cryostat

### Cavern and laboratory

When included (detail levels that don't omit these components), the underground
laboratory structure:

- Surrounds the water tank
- Uses the same coordinate origin
- Extends to represent the rock overburden and experimental hall

## Coordinate transformations

### From configuration to internal coordinates

When specifying detector positions in `special_metadata.yaml`:

1. **String center positions**:

   ```
   x = radius_in_mm × cos(angle_in_deg × π/180)
   y = radius_in_mm × sin(angle_in_deg × π/180)
   ```

2. **Detector vertical positions**:

   ```
   z = position_index × vertical_spacing
   ```

   (measured from top copper plate surface downward)

3. **Calibration tube positions**: Similar to string positions, using
   tube-specific radius and angle

### Thermal contraction

Components inside the cryostat at liquid argon temperature (88.8 K) experience
thermal contraction:

- **Copper rods**: "Warm" lengths specified in metadata are multiplied by a
  contraction factor (<1)
- **Support structures**: Dimensions account for operating temperature
- This is handled automatically in the geometry construction

## Units

**All distances are in millimeters (mm)** unless explicitly stated otherwise.

- Lengths, radii, heights: mm
- Angles: degrees (°)
- Temperature: Kelvin (K) for material properties
- Pressure: Pascal (Pa) for material properties

## Usage in simulation

### Vertex generation

When generating particle vertices for simulation:

- Use volume names to select regions
- Coordinates follow the internal system (Z positive downward)
- For uniform distribution in a string, generate Z uniformly over detector
  extent

### Calibration source positioning

Calibration sources deployed via calibration tubes:

- Z coordinate increases downward from top plate
- Horizontal position (X, Y) matches the calibration tube location
- Source height specifications in metadata are relative to top plate

## Coordinate system summary

| Component         | Origin                           | Z direction              | Typical usage                        |
| ----------------- | -------------------------------- | ------------------------ | ------------------------------------ |
| Internal (LAr)    | Cryostat center, top plate level | Down into LAr            | Detector positions, string layout    |
| Global (World)    | Same as internal                 | Down (consistent)        | Full geometry including tank, cavern |
| Calibration tubes | Same as internal                 | Down from top plate      | Source deployment                    |
| HPGe strings      | Same as internal                 | Down, detector positions | Detector array layout                |

## Examples

### Example 1: String at specific location

```yaml
hpge_strings:
  1:
    radius_in_mm: 500
    angle_in_deg: 0
```

This places string 1 at:

- Cartesian: (500, 0, variable z) mm
- On the positive X-axis
- 500 mm from the center

### Example 2: Calibration tube between strings

For 8 strings at 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°:

```yaml
calibration:
  1:
    radius_in_mm: 650
    angle_in_deg: 22.5 # Halfway between 0° and 45°
```

### Example 3: Detector vertical position

For a detector at position 3 in a string with 140.1 mm spacing:

- Z coordinate ≈ 3 × 140.1 = 420.3 mm below the top plate
- Measured from origin (top of copper moderator) downward

## Notes for developers

- When adding new components, use the existing coordinate system
- Z positive downward is consistent throughout the internal geometry
- Physical volumes inherit coordinates from their placement
- Surface normals follow pyg4ometry conventions
- Rotation matrices use right-handed convention
