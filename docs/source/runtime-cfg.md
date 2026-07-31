# Runtime configuration

A geometry is fully described by a single config file, passed to the generator
with `--config`:

```console
$ legend-pygeom-l1000 --config geom-config.yaml l1000.gdml
```

The file is YAML or JSON, and is validated against a JSON schema shipped with
the package (`src/pygeoml1000/configs/runtime_config_schema.yaml`), so a value
of the wrong type is reported instead of silently ignored. Unknown keys are
allowed through, so that a config carrying extra fields for the calling workflow
still validates. Its key names are deliberately kept in sync with
[legend-pygeom-l200](https://legend-pygeom-l200.readthedocs.io), so that the
same geometry config layout works for both generators. This is what lets
[legend-simflow](https://legend-simflow.readthedocs.io) drive either of them
through one workflow rule.

The geometry itself is built from two objects: `special_metadata`, a detailed
spatial configuration, and `channelmap`, the detector mapping and electronics
configuration (similar to the channelmap in the usual metadata). Those can be
supplied in two ways, and the choice is made by which keys the config file
contains, not by which command line flags are used:

- as a **raw** configuration: high-level geometry parameters (number of
  detectors per string, PMT positions, ...) that get _compiled_ into
  `special_metadata` and `channelmap`. This is the default. `raw_config`
  overrides individual raw values.
- as a **compiled** configuration: `special_metadata` and `channelmap` given
  directly, either inline or as paths to separate files. Then no compilation
  happens at all.

The typical workflow uses both: change the raw config for structural changes,
write the result out with `--write-config`, and edit that for fine-grained
adjustments.

## Config file reference

| key                  | type            | meaning                                                                              |
| -------------------- | --------------- | ------------------------------------------------------------------------------------ |
| `detail`             | string          | detail level preset, a key of `detail.yaml` (default: `radiogenic`)                  |
| `assemblies`         | list or string  | assemblies to build, see [Selecting assemblies](#selecting-assemblies)               |
| `raw_config`         | mapping or path | raw configuration overrides, see [Raw configuration files](#raw-configuration-files) |
| `special_metadata`   | mapping or path | compiled spatial configuration, skips compiling it from the raw config               |
| `channelmap`         | mapping or path | compiled channel map, skips compiling it from the raw config                         |
| `sipm_use_pde_curve` | bool            | if false, use a flat SiPM photon detection efficiency instead of the PDE curve       |
| `sipm_efficiencies`  | mapping         | per-channel scale factors for the SiPM detection efficiency                          |

Every option that defines the geometry lives in this file. The command line only
selects which artifacts to produce (`--write-manifest`, `--det-macro-file`, the
output GDML, ...), with the exception of `--detail` and `--assemblies`, which
override their config file counterparts.

(selecting-assemblies)=

### Selecting assemblies

`assemblies` selects which parts of the setup are built. Given as plain names it
is an absolute selection:

```yaml
assemblies: [cryostat, HPGe_dets, PEN_plates]
```

Alternatively, every entry can be prefixed by `+` or `-` to modify the set of
assemblies that the chosen detail level enables (either all entries carry an
operator, or none do):

```yaml
assemblies: [+watertank, -fiber_curtain]
```

Assemblies that are not selected are switched to `omit`. Selected assemblies
that the detail level omits are built at the `simple` detail level. The cryostat
must be included whenever `HPGe_dets` or `fiber_curtain` are.

(raw-configuration-files)=

## Raw configuration files

The raw configuration files are YAML files located in
`src/pygeoml1000/configs/`. Each file controls a specific aspect of the
geometry.

The `raw_config` key overrides them. It is deep-merged on top of the packaged
files, so only the values that actually change have to be given:

```yaml
raw_config:
  string:
    units:
      n: 10 # 10 detector units per string, everything else unchanged
```

It can also be the path to a folder of raw config files, which is again merged
over the packaged ones. A file that is not in the folder simply keeps its
packaged contents:

```yaml
raw_config: /path/to/my/configs
```

Use `--dump-raw-configs <dir>` to get a copy of the packaged files as a starting
point. `raw_config` is ignored (with a warning) if both `channelmap` and
`special_metadata` are given, since then nothing needs to be compiled.

The `configs` folder in the source directory contains the following raw config
files:

```bash
configs/
├── array.yaml
├── crystal.yaml
├── detail.yaml
├── hpge.yaml
├── pmts_pos.yaml
├── pmts.yaml
├── sipm.yaml
└── string.yaml
```

### `array.yaml` - String array layout

Defines the positions and orientations of the detector string array:

```yaml
center:
  x_in_mm: [0.0, 533.7, 106.7, -427.0, -533.7, -106.7, 427.0]
  y_in_mm: [0.0, 184.9, 554.7, 369.8, -184.9, -554.7, -369.8]
radius_in_mm: 213.5
angle_in_deg: [0, 60, 120, 180, 240, 300]
```

- `center`: lists of x/y coordinates (in mm) for each string cluster center. The
  number of clusters is given by the length of these lists.
- `radius_in_mm`: the radius at which individual strings are placed around their
  cluster center.
- `angle_in_deg`: the angular positions (in degrees) for the strings within a
  cluster. The total number of strings is
  `len(center.x_in_mm) × len(angle_in_deg)`.

### `string.yaml` - Detector string properties

Defines the physical parameters of a single detector string:

```yaml
units:
  n: 8
  l: 140.1
copper_rods:
  r: 1.5
  r_offset_from_center: 51
n_sipm_modules_per_string: 3
```

- `units.n`: number of HPGe detector slots per string.
- `units.l`: spacing between detector units along the string axis (in mm).
- `copper_rods.r`: copper rod radius (in mm).
- `copper_rods.r_offset_from_center`: radial offset of the copper rods from the
  string center (in mm).
- `n_sipm_modules_per_string`: number of SiPM fiber modules per string.

### `hpge.yaml` - HPGe detector template

Provides the template channelmap entry for all HPGe detectors. All detectors in
the generated channelmap start from this template and have their `name`,
`daq.rawid`, `location.string`, and `location.position` fields overwritten
during compilation. The template includes full geometry, production, and
characterization sub-fields following the standard LEGEND metadata format.

### `sipm.yaml` - SiPM module template

Provides the template channelmap entry for SiPM fiber modules. During
compilation, `name`, `location.barrel`, `location.fiber`, `location.position`,
and `daq.rawid` are filled in for each module. SiPM raw IDs start at 5000.

### `pmts.yaml` - PMT template

Provides the template channelmap entry for all PMTs. During compilation, `name`,
`daq.rawid`, and `location` (including x, y, z coordinates and the PMT
orientation direction) are filled in. PMT raw IDs start at 6000.

### `pmts_pos.yaml` - PMT placement

Defines the spatial layout of floor and wall PMTs:

```yaml
floor:
  row1: {id: 1, n: 50, r: 3800}
  ...
tyvek:
  faces: 15
  r: 4000
wall:
  row1: {id: 1, n: 35, z: 1811.1}
  ...
```

- `floor`: each entry defines a ring of PMTs at the tank floor with `n` PMTs at
  radius `r` (in mm). PMTs with `r` larger than `watertank.tank_pit_radius` are
  automatically raised to `watertank.tank_pit_height`.
- `tyvek.faces`: number of polygon faces of the Tyvek reflector wall. Determines
  the wall geometry for PMT placement.
- `tyvek.r`: inscribed radius of the Tyvek polygon (in mm). The circumradius
  used for PMT placement is computed as `r / cos(π / faces)`.
- `wall`: each entry defines a ring of PMTs at height `z` (in mm) with `n` PMTs
  distributed across the polygon faces.

### `detail.yaml` - Detail level presets

Defines which geometry assemblies are included for each named detail level:

```yaml
cosmogenic:
  cavern: simple
  watertank: simple
  ...
radiogenic:
  cavern: omit
  watertank: omit
  ...
```

Each key is a named preset (e.g. `cosmogenic`, `radiogenic`) selectable via the
`detail` config key or the `--detail` CLI option. Assembly values follow the
`pygeomtools` assembly detail convention (`omit`, `simple`, `stl`, `detailed`,
`metadata`, `place`).

### `crystal.yaml` - Crystal boule profile

Stores the impurity profile and slice offsets for the HPGe crystal boule used as
the default detector template, with the same format as in the metadata. It is
required to generate the drift-time map used in the post-processing of the
pulse-shape discrimination, but is not read by the geometry generation itself.

## Compilation

The compilation step converts the raw config files into the two runtime objects

- `special_metadata` and `channelmap` - via `config.py`.

**`special_metadata`** contains the detailed spatial layout used for geometry
placement:

- `hpge_string`: per-string center coordinates, angle, and rod geometry.
- `hpges`: per-detector rod length and baseplate type.
- `fibers`: per-SiPM-module position derived from the string array layout.
- `watertank_instrumentation`: Tyvek polygon parameters.
- `detail`: the full detail level presets copied from `detail.yaml`.

**`channelmap`** contains the detector mapping and electronics configuration:

- One entry per HPGe detector with location (string and position index) and raw
  ID.
- One entry per SiPM top/bottom channel with fiber name, barrel index, and raw
  ID.
- One entry per PMT with x/y/z position, orientation direction vector, and raw
  ID.

`--write-config` writes the result out resolved into an explicit `channelmap`
and `special_metadata`, together with the effective `detail` and `assemblies`.

```console
$ legend-pygeom-l1000 --config geom-config.yaml --write-config resolved.yaml
```

The output is itself a valid config file, so it can be edited by hand and fed
straight back in via `--config`, and it can be written in the same invocation
that builds the geometry:

```console
$ legend-pygeom-l1000 --config geom-config.yaml --write-config resolved.yaml l1000.gdml
```

## Best practices

1. **Start from `raw_config`** for high-level structural changes (e.g. number of
   strings, PMT ring positions). Because it is deep-merged over the packaged raw
   configs, a change is usually a handful of lines in the geometry config file
   and needs no copy of the defaults:

   ```yaml
   # geom-config.yaml
   detail: radiogenic
   raw_config:
     string:
       units:
         n: 10
   ```

2. **Move to a resolved config** for fine-grained adjustments (e.g. removing
   individual detectors, overriding a single position or raw ID) that the raw
   configuration cannot express. Write it out, edit it, and pass it back in:

   ```console
   $ legend-pygeom-l1000 --config geom-config.yaml --write-config resolved.yaml
   $ vim resolved.yaml
   $ legend-pygeom-l1000 -V --config resolved.yaml l1000.gdml
   ```

3. **Keep `special_metadata` and `channelmap` in separate files** if the inline
   versions make the config unwieldy. Both keys also accept a path:

   ```yaml
   special_metadata: ./special_metadata.yaml
   channelmap: ./channelmap.yaml
   ```

Since a resolved config carries both compiled objects, `raw_config` no longer
has any effect on it. It is ignored with a warning if it is left in place.

## Examples

### Minimal single-ring geometry (6 strings)

<!-- prettier-ignore -->
:::{image} images/geom_6_strings_top.png
:height: 300px
:::

<!-- prettier-ignore -->
:::{image} images/geom_6_strings_side.png
:height: 300px
:::

A compact geometry with one central cluster of 6 strings is useful for fast test
simulations or studies that do not require the full array. Override the cluster
list in `array.yaml` with a single entry at the origin:

```yaml
# geom-config.yaml
raw_config:
  array:
    center:
      x_in_mm: [0.0]
      y_in_mm: [0.0]
```

Then build:

```console
$ legend-pygeom-l1000 -V --config geom-config.yaml
```

This produces 6 strings (`V0101`-`V0608`, 48 HPGe detectors total), 36 SiPM
channels, and the full PMT complement (unchanged, since `pmts_pos.yaml` was not
modified).

### Two-ring geometry (12 strings)

<!-- prettier-ignore -->
:::{image} images/geom_12_strings_top.png
:height: 300px
:::

<!-- prettier-ignore -->
:::{image} images/geom_12_strings_side.png
:height: 300px
:::

To simulate two string clusters placed around their respective centers, set two
entries in `array.yaml`:

```yaml
# geom-config.yaml
raw_config:
  array:
    center:
      x_in_mm: [0.0, 533.7]
      y_in_mm: [0.0, 184.9]
```

Compiling this produces 12 strings (`V0101`-`V1208`, 96 HPGe detectors), 72 SiPM
channels, and the full PMT complement.

### Removing a specific detector or string from the resolved config

<!-- prettier-ignore -->
:::{image} images/geom_12_strings_wo_string_7_top.png
:height: 300px
:::

<!-- prettier-ignore -->
:::{image} images/geom_12_strings_wo_string_7_side.png
:height: 300px
:::

After writing out the resolved config with `--write-config`, individual
detectors can be removed by deleting their entries from its `channelmap` and
`special_metadata.hpges` sections. For example, to remove `V0701` (position 1 of
string 7) from the 12-string config:

1. Delete the `V0701` key from `channelmap`.
2. Delete the `V0701` key from `special_metadata.hpges`.

The remaining 95 HPGe detectors are placed normally. The missing slot is simply
left empty in the string.

To remove an entire string (e.g. string 7) from the geometry, delete:

- in the `channelmap`:
  - all `geds` entries with `location.string: 7`,
  - all `spms` entries with `location.barrel: 7`,
- in the `special_metadata`:
  - all entries with `V07xx` in `hpges`,
  - all entries with `S07xx` in `fibers`, and
  - the entry for string `'7'` in `hpge_string`

To remove all detectors of a string (e.g. string 7), but keep the SiPM modules
and fibers, only delete the `geds` entries in the `channelmap` and the `V07xx`
entries in `hpges` in the `special_metadata`.

### Replacing the default HPGe template with a custom one

To use a custom HPGe template, override `hpge` in `raw_config` with the desired
geometry and characterization fields. The geometry is defined using the standard
format of the legend metadata (e.g. the example geometries found in the remage
[tutorial](https://remage.readthedocs.io/en/stable/tutorial.html#experimental-geometry)).
At the moment, there is only support for using a single geometry template for
all detectors, though in the future this will be generalized to allow for
multiple geometries per setup. Per-detector geometries can already be set by
hand in a resolved config, since each `channelmap` entry carries its own
`geometry` block.
