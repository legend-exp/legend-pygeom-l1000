# Dummy-metadata and legend-metadata

This repository comes with some dummy-detector-metadata, which will be used by
default to create the geometry. This means that a working setup of
[`legend-metadata`](https://github.com/legend-exp/legend-metadata) should not be
required for the usage of this package.

## Dummy-metadata

This package adds the option `legend-pygeom-l1000 --generate-metadata`. This
option will use the `config.json` file found in `src/pygeoml1000/configs/` to
create the essential `channelmap.json` and `special_metadata.yaml` file in the
formerly named folder. The content of these files massively governs the geometry
creation. Especially the `special_metadata.yaml` file contains plenty of
specific setup options, that can easily be changed.

### Quick Start with Metadata Generation

To generate default metadata files:

```console
legend-pygeom-l1000 --generate-metadata
```

This creates `channelmap.json` and `special_metadata.yaml` in the
`src/pygeoml1000/configs/` directory based on the default `config.json`.

To generate metadata and create a geometry in one step:

```console
legend-pygeom-l1000 --generate-metadata l1000.gdml
```

In case that the user directly creates a geometry without previously generating
these files, the `config.json` file will be used to create the essential
`channelmap` and `special_metadata` information on the fly, without creating any
files.

### Custom Metadata Configuration

You can provide a custom configuration file to override the default settings:

```console
legend-pygeom-l1000 --generate-metadata --metadata-config my_config.json
```

You can also specify custom output paths:

```console
legend-pygeom-l1000 --generate-metadata \
  --metadata-config my_config.json \
  --output-special-metadata my_special.yaml \
  --output-channelmap my_channelmap.json
```

### Configuration File Structure

The `config.json` file controls several aspects of the geometry:

#### Detector String Configuration

The `string` section defines the detector array layout:

```json
{
  "string": {
    "units": {
      "n": 8,
      "l": 140.1
    },
    "copper_rods": {
      "r": 1.5,
      "r_offset_from_center": 51
    }
  }
}
```

- `units.n`: Number of detector units per string
- `units.l`: Vertical spacing between units (mm)
- `copper_rods.r`: Radius of the copper support rods (mm)
- `copper_rods.r_offset_from_center`: Radial offset of rods from string center
  (mm)

To change the number of detectors per string or their spacing, modify these
values in your custom config file.

#### Detail Level Definitions

The `detail` section defines what components are included at each detail level:

```json
{
  "detail": {
    "radiogenic": {
      "cavern": "omit",
      "labs": "omit",
      "watertank": "omit",
      "watertank_instrumentation": "omit",
      "cryostat": "simple",
      "nm_plastic": "simple",
      "nm_holding_structure": "simple",
      "fiber_curtain": "detailed",
      "front-end_and_insulators": "place",
      "PEN_plates": "stl",
      "HPGe_dets": "metadata"
    }
  }
}
```

Options for each component:

- `omit`: Component not included
- `simple`: Basic geometry
- `detailed`/`place`/`stl`: More detailed implementations
- `metadata`: Use real detector geometries from metadata

#### Water Tank PMT Positioning

The `pmts_pos` section controls PMT placement in the water tank:

```json
{
  "pmts_pos": {
    "floor": {
      "row1": {
        "id": 1,
        "n": 50,
        "r": 3800
      }
    },
    "wall": {
      "row1": {
        "id": 1,
        "n": 35,
        "z": 1811.1
      }
    },
    "tyvek": {
      "faces": 15,
      "r": 4000
    }
  }
}
```

- `floor.rowN`: PMTs on the tank floor
  - `n`: Number of PMTs in this row
  - `r`: Radial distance from center (mm)
- `wall.rowN`: PMTs on the tank walls
  - `n`: Number of PMTs at this height
  - `z`: Height position (mm)
- `tyvek`: Tyvek reflector configuration
  - `faces`: Number of faces for polycone shape
  - `r`: Radius of tyvek structure (mm)

#### Dummy Detector Specifications

The `dummy_dets` section defines the properties of dummy detectors:

```json
{
  "dummy_dets": {
    "hpge": {
      "name": "V00_dummy",
      "type": "icpc",
      "geometry": {
        "height_in_mm": 100,
        "radius_in_mm": 42.0,
        "borehole": {
          "radius_in_mm": 5.0,
          "depth_in_mm": 60.0
        }
      }
    }
  }
}
```

You can modify these to change the dimensions and characteristics of the dummy
detectors.

The `--generate-metadata` option has four additional arguments. The first three
arguments should only ever be used by very experienced users (as i can not
really think of a usecase for them...). They take the path to the input and
output files, defaulting to the path in the config folder where they are
expected to be... The fourth argument lets the user choose a HPGe detector from
the [`legend-metadata`](https://github.com/legend-exp/legend-metadata) package,
which will be used to replace all HPGe detectors in the geometry.

### Advanced Options

The `--generate-metadata` command accepts several optional arguments:

- `--metadata-config`: Path to custom configuration file (default:
  `configs/config.json`)
- `--output-special-metadata`: Path for generated special metadata file
  (default: `configs/special_metadata.yaml`)
- `--output-channelmap`: Path for generated channelmap file (default:
  `configs/channelmap.json`)
- `--dets-from-metadata`: Use specific HPGe detector from legend-metadata (see
  below)

These options allow advanced users to:

- Use multiple configuration files for different geometry variants
- Store metadata files in different locations
- Generate metadata independently from geometry creation

## Legend-metadata

As previously mentioned, geometries can be created with this package without any
access to the `legend-metadata`. But for users with access, there is the option
to replace the dummy HPGe detectors in the setup with actual detectors from the
metadata. For this the user has to create the corresponding `channelmap`
themselves before creating the geometry. This is done via the command

```console
legend-pygeom-l1000 --generate-metadata --dets-from-metadata '{"hpge": "V000000A"}'
```

Where `"V000000A"` has to be replaced with the name of the detector in the
`legend-metadata`. This will cause every single HPGe detector in the geometry to
be replaced by that detector. It is currently not possible to place multiple
different HPGe detectors within one geometry.

```{note}
While it would be possible to also replace the `spms` or `pmts`, due to the impact of individual optical detector models being beyond the simulation, this command is currently restricted to only replace hpge detectors.
```

## The special metadata

The `special_metadata.yaml` file contains some specific information about how to
create the geometry. First it consists of the detail levels. These detail levels
are described in the [Geometry Components](geometry_components.md#detail-levels)
documentation.

Additionally there is more information about detailed structures in there.

### Structure Overview

The special metadata file typically contains the following sections:

1. **Detail levels**: Component-specific detail settings (inherited from
   config.json)
2. **HPGe string configuration**: Positions and properties of detector strings
3. **HPGe detector unit configuration**: Individual detector settings
4. **Calibration tube configuration**: Calibration system layout
5. **Watertank instrumentation**: PMT and optical detector setup

### Editing Special Metadata

After generating the special metadata file, you can edit it directly to
customize the geometry. The file uses YAML format for easy manual editing.

**Example workflow:**

1. Generate initial metadata:

   ```console
   legend-pygeom-l1000 --generate-metadata
   ```

2. Edit the generated `src/pygeoml1000/configs/special_metadata.yaml`

3. Create geometry using your modified metadata:
   ```console
   legend-pygeom-l1000 l1000.gdml
   ```

The geometry generation will automatically read the modified
special_metadata.yaml file.

### Global HPGe string configuration

The HPGe string section defines the spatial arrangement of detector strings:

- `hpge_string` → HPGe string number (e.g., `1`, `2`, `3`, ...)
  - `radius_in_mm` → radial distance from the center of the cryostat to the
    string axis
  - `angle_in_deg` → azimuthal position of the string with respect to the
    positive x-direction (0° = +x axis, 90° = +y axis)
  - `minishroud_radius_in_mm` → radius of the minishroud (NMS) of this string
  - `minishroud_delta_length_in_mm` → modification of the default length of a
    NMS. If unspecified, 0 will be used.
  - `rod_radius_in_mm` → placement radius of the support rod of this string

**Example configuration:**

```yaml
hpge_strings:
  1:
    radius_in_mm: 500
    angle_in_deg: 0
    minishroud_radius_in_mm: 80
    minishroud_delta_length_in_mm: 0
    rod_radius_in_mm: 51
  2:
    radius_in_mm: 500
    angle_in_deg: 45
    minishroud_radius_in_mm: 80
    minishroud_delta_length_in_mm: 5
    rod_radius_in_mm: 51
```

**Tips for customization:**

- **Adding strings**: Simply add new numbered entries with the required
  parameters
- **Radial positions**: Increase `radius_in_mm` to move strings further from
  center
- **Angular distribution**: Space strings evenly by dividing 360° by the number
  of strings
  - For 8 strings: 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°
  - For 12 strings: 0°, 30°, 60°, 90°, etc.
- **Minishroud size**: Increase `minishroud_radius_in_mm` for larger detectors
  or to add shielding
- **Custom length**: Use `minishroud_delta_length_in_mm` to extend or shorten
  specific minishrouds

### HPGe detector unit configuration

Individual detector properties can be customized for each detector:

- `hpges` → HPGe detector name (matches detector name from channelmap)
  - `rodlength_in_mm` → length of the copper rods next to this detector. This is
    a "warm" length, i.e. it is multiplied by a factor < 1 to get the shorter
    rod length in the cryostat due to thermal contraction.
  - `baseplate` → size of the PEN plate below this detector (one value out of
    `small`, `medium`, `large`, `xlarge`)

    Depending on the other detector properties, the value might be transformed,
    i.e. for Ortec ICPCs to `medium_ortec`.

**Example configuration:**

```yaml
hpges:
  V000001A:
    rodlength_in_mm: 140.1
    baseplate: medium
  V000002A:
    rodlength_in_mm: 145.0
    baseplate: large
  V000003B:
    rodlength_in_mm: 135.5
    baseplate: small
```

**Baseplate sizes:**

The baseplate size affects both the physical dimensions and optical properties:

- `small`: For compact detector arrangements
- `medium`: Standard size for most detectors
- `large`: For larger detectors or increased optical coupling
- `xlarge`: Maximum size for special configurations

**Rod length considerations:**

- Longer rods: Increase detector separation, useful for background studies
- Shorter rods: Compact array, useful for maximizing detector density
- Thermal contraction: The specified "warm" length is automatically scaled for
  cryogenic temperatures
- Typical values: 120-150 mm depending on detector size and configuration

### Calibration tube configuration

The calibration system allows deployment of radioactive sources for detector
calibration:

- `calibration` → Calibration tube number
  - `radius_in_mm` → radial distance from the center of the cryostat to the
    calibration tube axis
  - `angle_in_deg` → azimuthal position of the calibration tube with respect to
    the positive x-direction
  - `tube_radius_in_mm` → inner radius of the tube itself
  - `length_in_mm` → length of the calibration tube below the top copper plate

**Example configuration:**

```yaml
calibration:
  1:
    radius_in_mm: 650
    angle_in_deg: 22.5
    tube_radius_in_mm: 10
    length_in_mm: 1500
  2:
    radius_in_mm: 650
    angle_in_deg: 67.5
    tube_radius_in_mm: 10
    length_in_mm: 1500
```

**Positioning guidelines:**

- **Radial distance**: Typically outside the detector array (larger than string
  radius)
  - Standard: 600-700 mm for arrays with strings at ~500 mm
- **Angular position**: Place between detector strings for uniform coverage
  - For 8 strings at 0°, 45°, 90°, etc., place calibration tubes at 22.5°,
    67.5°, etc.
- **Tube radius**: Must accommodate source holder dimensions
  - Typical: 8-12 mm inner radius
- **Length**: Should extend to lowest detector position
  - Calculate from: (number of detectors × vertical spacing) + margin
  - Typical: 1200-1800 mm

### Watertank instrumentation

Configuration for the reflective tyvek foil and PMT placement:

- `tyvek` → The reflective tyvek foil planned to split the water tank in two
  sections
  - `faces` → Number of faces, as it is a polycone and not a cylinder
  - `r` → radius of the tyvek polycone in mm

**Example configuration:**

```yaml
tyvek:
  faces: 15
  r: 4000
```

**Customization tips:**

- **Number of faces**: More faces create a smoother, more cylindrical shape
  - Minimum: 6 (hexagonal)
  - Typical: 12-20 for good approximation
  - Higher values increase geometry complexity but improve realism
- **Radius**: Should fit within the water tank
  - Must be less than inner radius of water tank
  - Affects light collection uniformity
  - Typical: 3500-4500 mm depending on tank size

**PMT configuration** is handled through the `pmts_pos` section in config.json
(see above).

## Common Customization Examples

### Example 1: Compact Detector Array

Reduce the radial spread of the detector array:

In `special_metadata.yaml`, modify string radii:

```yaml
hpge_strings:
  1:
    radius_in_mm: 400 # Reduced from default 500
    angle_in_deg: 0
```

### Example 2: Additional Calibration Positions

Add more calibration tubes for better spatial coverage:

```yaml
calibration:
  1:
    radius_in_mm: 650
    angle_in_deg: 30
    tube_radius_in_mm: 10
    length_in_mm: 1500
  2:
    radius_in_mm: 650
    angle_in_deg: 90
    tube_radius_in_mm: 10
    length_in_mm: 1500
  3:
    radius_in_mm: 650
    angle_in_deg: 150
    tube_radius_in_mm: 10
    length_in_mm: 1500
  # Add more as needed
```

### Example 3: Custom Detector Spacing

In `config.json`, adjust the vertical spacing:

```json
{
  "string": {
    "units": {
      "n": 10,
      "l": 120.0
    }
  }
}
```

Then regenerate metadata:

```console
legend-pygeom-l1000 --generate-metadata --metadata-config config.json
```

### Example 4: Modified PMT Layout

In `config.json`, customize PMT positions:

```json
{
  "pmts_pos": {
    "floor": {
      "row1": {
        "n": 40,
        "r": 3500
      },
      "row2": {
        "n": 25,
        "r": 2500
      }
    }
  }
}
```

## Workflow Summary

**Standard workflow:**

1. Start with default config.json
2. Generate metadata: `legend-pygeom-l1000 --generate-metadata`
3. Create geometry: `legend-pygeom-l1000 l1000.gdml`

**Custom configuration workflow:**

1. Copy and modify config.json
2. Generate metadata with custom config:
   `legend-pygeom-l1000 --generate-metadata --metadata-config my_config.json`
3. (Optional) Manually edit generated special_metadata.yaml
4. Create geometry: `legend-pygeom-l1000 l1000.gdml`

**Quick iteration workflow:**

1. Edit special_metadata.yaml directly
2. Create new geometry: `legend-pygeom-l1000 l1000_v2.gdml`
3. Visualize to verify: `legend-pygeom-l1000 --visualize l1000_v2.gdml`
