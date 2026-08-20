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
legend-pygeom-l1000 l1000.gdml --visualize
```

Creates the GDML file and immediately opens the VTK visualization viewer.

#### Custom Scene File

You can provide a custom visualization scene configuration:

```console
legend-pygeom-l1000 --visualize scene.json
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

More details can be found in
[legend-pygeom-tools](https://legend-pygeom-tools.readthedocs.io/en/stable/vis.html).

#### Generating Macros for Visualization and Detectors Registration (if necessary)

Generate a Geant4 macro file with visualization attributes:

```console
legend-pygeom-l1000 l1000.gdml --vis-macro-file vis.mac
```

Generate a Geant4 macro file for remage with active detector definitions:

```console
legend-pygeom-l1000 l1000.gdml --det-macro-file detectors.mac
```

### Geometry Options

#### Detail Levels

Control the level of detail in the generated geometry using the `--detail`
option:

```console
legend-pygeom-l1000 l1000.gdml --detail radiogenic
```

Available detail levels:

- `radiogenic`: (default) Includes relevant components for radiogenic background
  studies, i.e., a lot of details around the HPGe detector strings
- `cosmogenic`: Includes larger structures such as the water tank and hall, less
  detail around the HPGe detectors, used for cosmogenic simulations

Example:

```console
legend-pygeom-l1000 l1000_cosmogenic.gdml --detail cosmogenic
```

#### Assembly Selection

Select specific assemblies to include in the geometry:

```console
legend-pygeom-l1000 --assemblies "watertank,cryostat,HPGe_dets" l1000.gdml
```

When `--assemblies` is specified as a list of plain names, all unspecified
assemblies are omitted from the geometry. Entries can instead be prefixed by `+`
or `-` to modify the set of assemblies enabled by the detail level (either all
entries carry an operator, or none do):

```console
legend-pygeom-l1000 --assemblies "+watertank,-fiber_curtain" l1000.gdml
```

Available assemblies include:

- `cavern`: Cavern and surrounding rock
- `labs`: Experimental laboratory halls (not implemented yet)
- `watertank`: Water tank and surrounding infrastructure
- `watertank_instrumentation`: PMTs in the water tank
- `cryostat`: Cryostat components
- `nm_plastic`: Neutron moderator
- `nm_holding_structure`: Support structure for the neutron moderator (not
  implemented yet)
- `fiber_curtain`: WLS fibers around HPGe strings
- `front-end_and_insulators`: Front-end electronics and insulator holding
  structure
- `PEN_plates`: PEN baseplates
- `HPGe_dets`: HPGe detectors

The cryostat must be included whenever `HPGe_dets` or `fiber_curtain` are. For
more details see the `detail.yaml` section of {doc}`runtime-cfg`.

#### Custom Configuration

Use a configuration file to describe the geometry:

```console
legend-pygeom-l1000 l1000.gdml --config geom-config.yaml
```

Everything that defines the geometry can be set there, including the detail
level, the assembly selection, overrides of the pre-compiled configs, and a
fully compiled `channelmap`/`special_metadata`. `--detail` and `--assemblies`
override their config file counterparts. See {doc}`runtime-cfg` for the full
reference.

To write out the resolved configuration, i.e, the pre-compiled configs compiled
into an explicit `channelmap` and `special_metadata`, for archival or
hand-editing:

```console
legend-pygeom-l1000 --config geom-config.yaml --write-config resolved.yaml l1000.gdml
```

To get a copy of the pre-compiled config files shipped with the package as a
starting point for a custom configuration:

```console
legend-pygeom-l1000 --dump-pre-compiled-configs .
```

### Generated Metadata

LEGEND-1000 has no metadata database. The generator writes the detector part of
one:

```console
legend-pygeom-l1000 --config geom-config.yaml --write-metadata l1000dsg01-geom-metadata.tar.gz
```

The files use the layout and the format of
[legend-metadata](https://github.com/legend-exp/legend-metadata), so a workflow
reads them in the usual way. Give a plain folder name to write the tree directly
instead of an archive.

The generator covers the `datasets` and `hardware` parts only. It writes nothing
under `simprod`, `dataprod` or `jldataprod`. See {doc}`runtime-cfg` for the
exact scope.

[legend-simflow](https://legend-simflow.readthedocs.io) does not need the
archive. It imports this package and writes the same files straight into its
metadata folder, from the geometry config of the experiment.

The pre-compiled `runs.yaml` supplies what a geometry cannot know, such as the
runs and their duration. Change it like any other pre-compiled config, through
`pre_compiled_config` in the geometry config file:

```yaml
# geom-config.yaml
pre_compiled_config:
  runs:
    runinfo:
      p01:
        r000:
          phy:
            start_key: 20300101T000000Z
            livetime_in_s: 31557600.0
```

Use `--dump-pre-compiled-configs <dir>` to get a copy of the packaged file
first. See {doc}`runtime-cfg` for what it holds.

### Quality Control

#### Overlap Checking

Check for overlaps in the geometry using pyg4ometry:

```console
legend-pygeom-l1000 l1000.gdml --check-overlaps
```

```{note}
Overlap checking can be slow for complex geometries and may not catch all overlap issues. It's recommended to verify geometries with Geant4 as well. Refer to [l200:geom-dev](https://legend-pygeom-l200.readthedocs.io/en/stable/geom-dev.html) for details.
```

#### Parts Manifest

Write a YAML manifest of every part in the geometry, with its material, its
number of placements and its total mass:

```console
legend-pygeom-l1000 --write-manifest parts.yaml
```

No GDML file has to be produced. The manifest is meant to be cross-checked
against the experiment's bill of materials, and to provide the mass of each
material present in the simulation for background studies.

```yaml
metadata:
  package_version: 0.4
  detail_level: radiogenic
  assemblies: null
  mesh_slices: 100
  n_logical_volumes: 370
  n_physical_volumes: 17196
  units:
    volume: cm**3
    mass: g
    density: g/cm**3
totals:
  mass: 373458272.2
  by_material:
    LiquidArgon: 280951383.1
    metal_steel: 84623861.8
    # ...
parts:
  - name: hpge_cable_hv_140.10
    material: metal_copper
    density: 8.96
    solid: Union
    placements: 336
    unit_volume: 0.4193
    total_volume: 140.9
    total_mass: 1262.1
  # ...
```

There is one entry per logical volume, sorted by descending total mass.
`placements` is the number of times that volume occurs in the whole geometry,
counted through the volume tree.

The manifest only describes what is actually in the geometry, so it follows
`--detail` and `--assemblies`. Parts that are omitted are absent from it rather
than listed with zero mass.

```{note}
Volumes are derived from the meshes computed by pyg4ometry, so the masses are
approximations. `--write-manifest` therefore builds the geometry with a fine
mesh (100 slices).
```

### Optical Properties

The materials come from
[legend-pygeom-tools](https://legend-pygeom-tools.readthedocs.io/en/stable/)
(`LegendMaterialRegistry`). The other LEGEND geometry packages use the same
definitions.

Every material carries its optical properties by default. These are the
refractive indices, the attenuation and absorption lengths, and the WLS and
scintillation tables. Use the `enable_optical` config key to change this. See
{doc}`runtime-cfg` for the syntax.

#### Custom Optical Properties Plugin

Load custom material properties before geometry construction:

```console
legend-pygeom-l1000 l1000.gdml --pygeom-optics-plugin my_materials.py
```

This allows you to define or modify optical properties of materials used in the
geometry.

## Complete Examples

### Example 1: Full Geometry with Visualization

Generate a complete geometry with radiogenic detail and visualize it:

```console
legend-pygeom-l1000 l1000_radiogenic.gdml --detail radiogenic --visualize
```

### Example 2: Specific Assemblies with Macros

Generate geometry with only specific components and export macro files:

```console
legend-pygeom-l1000 \
  l1000_custom.gdml \
  --assemblies watertank,cryostat,HPGe_dets \
  --vis-macro-file vis.mac \
  --det-macro-file detectors.mac
```

### Example 3: Custom Configuration with Overlap Check

Use a custom configuration and check for overlaps:

```console
legend-pygeom-l1000 \
  --config geom-config.yaml \
  --check-overlaps \
  --verbose
```

### Example 4: Debugging with Maximum Verbosity

Generate geometry with full debug output:

```console
legend-pygeom-l1000 l1000_debug.gdml --debug
```

## Workflow Tips

### Rapid Prototyping

For quick testing and iteration:

1. Use `--visualize` without specifying an output file to preview changes
   quickly
2. Use `--assemblies` to focus on specific components

### Production Geometries

For final, production-ready geometries:

1. Use `--detail radiogenic` for radiogenic detail
2. Run with `--check-overlaps` to verify geometry integrity
3. Use custom `--config` files to document specific geometry variations, and
   `--write-config` to archive the exact geometry that was built

### Performance Considerations

- Overlap checking is computationally expensive. Use sparingly
- Fine mesh visualization (`"fine_mesh": true` in scene files) increases memory
  usage
- Maximum verbosity (`--debug`) generates large log outputs. Use only when
  troubleshooting
