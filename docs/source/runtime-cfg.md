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
configuration (similar to the channelmap in the usual metadata).

(input-schemes)=

## The three input schemes

Three schemes supply those two objects. The keys in the config file select the
scheme.

| scheme                                    | key                                 | what it sets                                             | edit it by hand?             |
| ----------------------------------------- | ----------------------------------- | -------------------------------------------------------- | ---------------------------- |
| [raw](#raw-configuration-files)           | `raw_config`                        | the shape of the setup, such as the detectors per string | yes, for a high-level change |
| [compiled](#compilation)                  | `channelmap` and `special_metadata` | every detector, one by one                               | yes, for a low-level change  |
| [generated metadata](#generated-metadata) | `metadata`                          | a whole metadata tree, which holds both objects          | no, this one is for simflow  |

A config file that gives more than one scheme keeps the most explicit one.
`metadata` wins over the other two. `channelmap` together with
`special_metadata` wins over `raw_config`. The generator writes a warning for
each key that it drops.

### Raw

The raw configuration holds the parameters that describe the shape of the setup:
the number of strings, the number of detectors on a string, the position of the
PMTs. The generator compiles them into the two objects. This is the default.

Use it for a change that modifies many parts at the same time. Such a change is
usually a few lines. See [Raw configuration files](#raw-configuration-files).

### Compiled

A compiled configuration gives the two objects directly, either in the config
file or as a path to a separate file. The generator then compiles nothing.

Use it for a change that the raw parameters cannot express: to remove a single
detector, to move a single string, or to give one detector its own geometry. The
key names match [legend-pygeom-l200](https://legend-pygeom-l200.readthedocs.io),
so a config of this shape drives both generators.

Write one with `--write-config` and then edit it. See
[Compilation](#compilation).

### Generated metadata

The `metadata` key points to the tarball that `--write-metadata` wrote. That
tarball holds the same information as the compiled configuration, but in the
form of the legend-metadata tree.

This scheme exists for [legend-simflow](https://legend-simflow.readthedocs.io),
where the geometry defined here defines the structure of the metadata content.
Do not edit the tarball to change the geometry. Change a raw or a compiled
config instead, and write a new tarball. See
[Generated metadata](#generated-metadata).

## Config file reference

| key                  | type            | meaning                                                                                                 |
| -------------------- | --------------- | ------------------------------------------------------------------------------------------------------- |
| `detail`             | string          | detail level preset, a key of `detail.yaml` (default: `radiogenic`)                                     |
| `assemblies`         | list or string  | assemblies to build, see [Selecting assemblies](#selecting-assemblies)                                  |
| `raw_config`         | mapping or path | raw configuration overrides, see [Raw configuration files](#raw-configuration-files)                    |
| `special_metadata`   | mapping or path | compiled spatial configuration, skips compiling it from the raw config                                  |
| `channelmap`         | mapping or path | compiled channel map, skips compiling it from the raw config                                            |
| `metadata`           | path            | generated metadata tree that holds both compiled objects, see [Generated metadata](#generated-metadata) |
| `enable_optical`     | bool or list    | materials that get optical properties, see [Optical properties](#optical-properties)                    |
| `sipm_use_pde_curve` | bool            | if false, use a flat SiPM photon detection efficiency instead of the PDE curve                          |
| `sipm_efficiencies`  | mapping         | per-channel scale factors for the SiPM detection efficiency                                             |

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

(optical-properties)=

### Optical properties

`enable_optical` selects the materials that get optical properties, such as
refractive indices, absorption lengths and scintillation tables. The default is
`true`.

```yaml
enable_optical: true # every material gets optical properties (default)
```

```yaml
enable_optical: false # no material gets optical properties
```

```yaml
enable_optical: [liquidargon, pen] # only these materials
```

Turn the optical properties off for a geometry that only needs the mass model,
for example a radiogenic background study. The GDML file is then much smaller.

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

### `crystal.yaml` - Crystal boule catalog

A list of crystal boules. Each boule has an impurity profile and slice offsets,
in the same format as in the metadata.

The compilation assigns the detectors to the boules of the catalog in order.
Each detector takes the `name` and the `order` of its boule. A workflow uses
these two fields to find the boule again. A detector therefore always points to
a crystal that exists.

The boule data does not change the geometry. It generates the drift-time map for
the post-processing of the pulse-shape discrimination, and it goes into the
[generated metadata](#generated-metadata).

(compilation)=

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

(generated-metadata)=

## Generated metadata

To use the LEGEND-1000 geometry in simflow, one has to generate a metadata
database:

```console
$ legend-pygeom-l1000 --config geom-config.yaml --write-metadata l1000dsg01-geom-metadata.tar.gz
```

The tree uses the same layout as the real
[legend-metadata](https://github.com/legend-exp/legend-metadata). A workflow
therefore reads it in the usual way.

The archive holds everything that describes the detectors. Four files come from
a template. The generator derives all other files from the compiled channel map.

| file                                                | content                                                       |
| --------------------------------------------------- | ------------------------------------------------------------- |
| `datasets/runinfo.yaml`                             | template: the runs, their start keys and live times           |
| `datasets/runlists.yaml`                            | template: the named run lists                                 |
| `datasets/statuses/validity.yaml`                   | template: from when the statuses apply                        |
| `datasets/statuses/<name>.yaml`                     | one analysis status per channel                               |
| `hardware/configuration/channelmaps/validity.yaml`  | template: from when the channel map applies                   |
| `hardware/configuration/channelmaps/<name>.yaml`    | `name`, `system`, `location` and `daq` of every channel       |
| `hardware/detectors/germanium/diodes/<DET>.yaml`    | one per HPGe: type, production, geometry and characterization |
| `hardware/detectors/germanium/crystals/<XTAL>.yaml` | one per crystal boule the detectors were cut from             |
| `special_metadata.yaml`                             | the compiled special metadata                                 |

The `apply:` entries of the adjacent `validity.yaml` set `<name>`. Nothing reads
these names. A workflow selects a file by comparing its `valid_from` with the
start key of a run. The template thus controls how the files are called.

The real legend-metadata has no `special_metadata.yaml`. This file carries the
compiled geometry, and it makes the tree sufficient to rebuild that geometry.

(why-each-part)=

### Why each part is necessary

Each part answers a question that
[legend-simflow](https://legend-simflow.readthedocs.io) asks while it builds the
DAG, or while it runs a job. This section names the reader of each part and the
effect of its absence.

#### `datasets/runinfo.yaml`

Gives the start key of each run. The workflow resolves every validity file
against a start key. It also gives `livetime_in_s` for a physics run. The
workflow splits the simulated events over the runs in proportion to that number.

Without it no run identifier resolves, and the workflow cannot select a channel
map or a status.

#### `datasets/runlists.yaml`

Names a group of runs, so that a production can ask for
`~runlists:valid.phy.p01` instead of a list of run identifiers.

The workflow reads this file only for a request of that form. A production that
lists its run identifiers one by one never touches it.

#### `datasets/statuses/`

Holds the analysis status of each channel. `LegendMetadata.channelmap` attaches
the status to the channel as `analysis`. The workflow then reads
`analysis.usability` to decide whether it simulates a detector, and
`analysis.psd.status.low_aoe` for the pulse-shape discrimination.

This part is the one that fails hardest. The workflow reads `analysis.usability`
without a guard while it builds the DAG. A germanium channel without a status
stops the production before the first job starts.

#### `hardware/configuration/channelmaps/`

Lists the channels. The workflow reads `system` to separate the germanium
detectors from the SiPMs and the PMTs, and `daq.rawid` to match a channel to the
raw identifier that the simulation writes.

Without it the workflow sees no channels, and there is nothing to simulate.

#### `hardware/detectors/germanium/diodes/`

One file per germanium detector, with four separate jobs:

- `geometry` builds the detector solid for the drift-time map.
- `characterization.combined_0vbb_analysis.fccd_in_mm.value` gives the dead
  layer. Without it the workflow falls back to 1 mm and writes a warning for
  each detector in each job.
- `characterization.l200_site.depletion_voltage_in_V` decides whether a detector
  runs far enough above depletion to be modeled. A detector without it gets no
  pulse-shape model.
- `type`, `production.order` and `production.crystal` build the name of the
  crystal. That name is the file the workflow looks for in the next folder.

The workflow also hands the whole file to the Julia code that builds the
drift-time map.

#### `hardware/detectors/germanium/crystals/`

One file per crystal boule. `impurity_curve.parameters` gives the impurity
profile along the boule, which the drift-time map needs. A detector whose
crystal has no impurity curve is not modelable.

`slices[<slice>].status` decides whether the simulated hits of a detector count.
The workflow copies it into the hit tier as `is_valid_sim`. A missing status
makes every hit of that detector invalid, and it does so quietly.

#### `special_metadata.yaml`

The workflow never reads this file. It holds the compiled geometry, so that this
generator can rebuild the same setup from the tarball alone.

```{note}
The tree describes the detectors. It does not describe the production. The
settings under `simprod/config/` stay with the user, and the operational
voltages in `pars/<experiment>/geds/opv/` are mandatory there. A workflow that
cannot read them fails while it builds the DAG.
```

### Rebuild the geometry from the tarball

A geometry config that points to a generated tree needs nothing else:

```yaml
# l1000dsg01-geom-config.yaml
executable: legend-pygeom-l1000
metadata: ./l1000dsg01-geom-metadata.tar.gz
```

```console
$ legend-pygeom-l1000 --config l1000dsg01-geom-config.yaml l1000.gdml
```

The generator reads both compiled objects from the tree. The keys `channelmap`,
`special_metadata` and `raw_config` thus have no effect next to `metadata`, and
the generator ignores them with a warning. Commit the two files together to make
a production reproducible from them alone.

### One channel in three files

The generator splits a channel map entry into three disjoint parts, because the
database merges them again when it reads them. The reader loads the channel map
first. It then merges the matching diode file over the channel. Last, it
attaches the status as `analysis`.

The diode file wins this merge. It therefore carries none of `system`, `daq` or
`location`. Any of these keys would replace the raw ID and the position of the
channel.

(metadata-template)=

### The template

The template holds what a geometry cannot know: the runs, their duration, and
the start of validity of the metadata. It ships as
`src/pygeoml1000/configs/template_metadata.tar.gz` and holds four files. The
four blocks below are those files, unpacked while this page is built.

`datasets/runinfo.yaml` gives the start key of each run. Every validity file
resolves against a start key, so this file is the clock of the whole tree.

```{literalinclude} _generated/template_metadata/datasets/runinfo.yaml
:language: yaml
```

`datasets/runlists.yaml` names a group of runs. Keep the entries as `rNNN..rMMM`
range expressions.

```{literalinclude} _generated/template_metadata/datasets/runlists.yaml
:language: yaml
```

`datasets/statuses/validity.yaml` says from when the per-channel statuses apply,
and under which name the generator writes them.

```{literalinclude} _generated/template_metadata/datasets/statuses/validity.yaml
:language: yaml
```

`hardware/configuration/channelmaps/validity.yaml` does the same for the channel
map.

```{literalinclude} _generated/template_metadata/hardware/configuration/channelmaps/validity.yaml
:language: yaml
```

#### Change the template

1. Unpack a copy of the template.
2. Edit the files.
3. Give the copy to the generator.

```console
$ tar xzf $(python -c "import pygeoml1000, pathlib; \
    print(pathlib.Path(pygeoml1000.__file__).parent / 'configs/template_metadata.tar.gz')") -C my_template
$ $EDITOR my_template/datasets/runinfo.yaml
$ legend-pygeom-l1000 --write-metadata out.tar.gz --metadata-template my_template
```

The packaged template carries a comment on each setting. Read those before you
change a value.

Keep the run list entries as `rNNN..rMMM` range expressions. A workflow adds the
experiment name only to an entry with the shape of a range. It reads a plain
`r000` as a complete run identifier, which never resolves.

The template does not hold the per-channel statuses either. A geometry cannot
know how a channel behaved in a run, so the generator gives every channel the
same status: `usability: "on"`, `processable: true`, and for a germanium channel
`psd.status.low_aoe: valid`.

There is no config key for this. To turn a channel off, edit its entry in the
generated `datasets/statuses/` file:

```yaml
V00101A:
  reason: "noisy"
  usability: "off"
  processable: true
  psd:
    status:
      low_aoe: valid
```

Commit the tarball with that edit. A later `--write-metadata` writes the
defaults again, so re-apply the change after a regeneration.

```{note}
A generated tree is not a Git repository. `legendmeta.LegendMetadata` reads such
a tree, but its version check does not. Call `channelmap` with
`skip_version_check=True`.

Unpack the archive before you give the folder to `LegendMetadata`. For a path
that is empty or absent, it clones the real legend-metadata over SSH.
```

## Best practices

[The three input schemes](#input-schemes) compares the schemes. This section
shows how to move from one to the next.

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
