# CLI Usage

The `legend-pygeom-l1000` command-line interface (CLI) is the primary way to
interact with this package. It provides a range of options for generating
geometries, visualizing them, and managing metadata.

## Basic Usage

### Generating a Basic Geometry

To create a basic LEGEND-1000 geometry, run:

```console
legend-pygeom-l1000 l1000.gdml
```

This will generate a GDML file named `l1000.gdml` containing the complete
geometry using default settings.

### Quick Visualization

To visualize the geometry without saving a GDML file:

```console
legend-pygeom-l1000 --visualize
```

This opens an interactive VTK viewer window where you can inspect the geometry.

## Command-Line Options

### Global Options

#### Version Information

```console
legend-pygeom-l1000 --version
```

Displays the current version of the package.

#### Verbosity Control

- `--verbose` or `-v`: Increase verbosity to see detailed debug information from
  pygeoml1000
- `--debug` or `-d`: Maximum verbosity, showing all debug information from all
  components

Example:

```console
legend-pygeom-l1000 -v l1000.gdml
```

### Visualization Options

#### Interactive Visualization

```console
legend-pygeom-l1000 --visualize l1000.gdml
```

Creates the GDML file and immediately opens the VTK visualization viewer.

#### Custom Scene File

You can provide a custom visualization scene configuration:

```console
legend-pygeom-l1000 --visualize scene.json l1000.gdml
```

The scene file is a JSON file that can specify visualization settings such as
camera position, rendering options, and mesh quality. Example scene file:

```json
{
  "fine_mesh": true,
  "camera_position": [0, 0, 5000],
  "background_color": [1, 1, 1]
}
```

#### Generating Visualization Macros

Generate a Geant4 macro file with visualization attributes:

```console
legend-pygeom-l1000 --vis-macro-file vis.mac l1000.gdml
```

Generate a Geant4 macro file for remage with active detector definitions:

```console
legend-pygeom-l1000 --det-macro-file detectors.mac l1000.gdml
```

### Geometry Options

#### Detail Levels

Control the level of detail in the generated geometry using the `--detail`
option:

```console
legend-pygeom-l1000 --detail radiogenic l1000.gdml
```

Available detail levels (from simplest to most detailed):

- `simple`: Basic geometry with minimal detail, suitable for quick testing
- `radiogenic`: Includes relevant components for radiogenic background studies
  (default)
- `full`: Complete geometry with all details included

Example:

```console
legend-pygeom-l1000 --detail full l1000_detailed.gdml
```

#### Assembly Selection

Select specific assemblies to include in the geometry:

```console
legend-pygeom-l1000 --assemblies watertank,cryo,hpge_strings l1000.gdml
```

When `--assemblies` is specified, all unspecified assemblies are omitted from
the geometry. Available assemblies include:

- `watertank`: Water tank and surrounding infrastructure
- `cryo`: Cryostat components
- `hpge_strings`: HPGe detector strings
- `calibration`: Calibration system
- `wlsr`: Wavelength shifter reflectors
- Additional assemblies (see geometry components documentation)

#### Custom Configuration

Use a custom configuration file to override default geometry parameters:

```console
legend-pygeom-l1000 --config custom_config.json l1000.gdml
```

The configuration file is a JSON file that can specify various geometry
parameters, material choices, and component dimensions.

### Quality Control

#### Overlap Checking

Check for overlaps in the geometry using pyg4ometry:

```console
legend-pygeom-l1000 --check-overlaps l1000.gdml
```

```{note}
Overlap checking can be slow for complex geometries and may not catch all overlap issues. It's recommended to verify geometries with Geant4 as well.
```

### Optical Properties

#### Custom Optical Properties Plugin

Load custom material properties before geometry construction:

```console
legend-pygeom-l1000 --pygeom-optics-plugin my_materials.py l1000.gdml
```

This allows you to define or modify optical properties of materials used in the
geometry.

## Complete Examples

### Example 1: Full Geometry with Visualization

Generate a complete geometry with maximum detail and visualize it:

```console
legend-pygeom-l1000 --detail full --visualize l1000_full.gdml
```

### Example 2: Specific Assemblies with Macros

Generate geometry with only specific components and export macro files:

```console
legend-pygeom-l1000 \
  --assemblies watertank,cryo,hpge_strings \
  --vis-macro-file vis.mac \
  --det-macro-file detectors.mac \
  l1000_custom.gdml
```

### Example 3: Custom Configuration with Overlap Check

Use a custom configuration and check for overlaps:

```console
legend-pygeom-l1000 \
  --config my_config.json \
  --check-overlaps \
  --verbose \
  l1000_checked.gdml
```

### Example 4: Debugging with Maximum Verbosity

Generate geometry with full debug output:

```console
legend-pygeom-l1000 --debug --visualize l1000_debug.gdml
```

## Workflow Tips

### Rapid Prototyping

For quick testing and iteration:

1. Use `--visualize` without specifying an output file to preview changes
   quickly
2. Use `--detail simple` to speed up geometry generation
3. Use `--assemblies` to focus on specific components

### Production Geometries

For final, production-ready geometries:

1. Use `--detail full` for complete detail
2. Run with `--check-overlaps` to verify geometry integrity
3. Generate both `--vis-macro-file` and `--det-macro-file` for simulation
4. Use custom `--config` files to document specific geometry variations

### Performance Considerations

- Overlap checking is computationally expensive; use sparingly
- Fine mesh visualization (`"fine_mesh": true` in scene files) increases memory
  usage
- Maximum verbosity (`--debug`) generates large log outputs; use only when
  troubleshooting
