# Dummy-metadata and legend-metadata

This repository comes with some dummy-detector-metadata, which will be used by
default to create the geometry. This means that a working setup of
[`legend-metadata`](https://github.com/legend-exp/legend-metadata) should not be
required for the usage of this package.

```{warning}

This functionality was implemented as a quick fix after copying over the source
code from the L200 geometry package. There it is useful to consider different
assembly options for the detector strings in different geometry configurations.
In L1000 however, due to it still being in development, this functionality is
not directly needed.

What it does offer is potential for systematic studies, i.e., scanning through
different options and testing the impact on the background model. However,
rather than having a base config file, the base parameters should be hardcoded,
but with the option to override them via an additional config file or CLI
options. __Therefore, this functionality should be refactored in the future.__

```

## Dummy-metadata

This package adds the option `legend-pygeom-l1000 --generate-metadata`. This
option will use the `config.json` file found in `src/pygeoml1000/configs/` to
create the essential `channelmap.json` and `special_metadata.yaml` file in the
formerly named folder. The context of these files massively governs the geometry
creation. Especially the `special_metadata.yaml` file contains plenty of
specific setup options, that can easily be changed.

In case that the user directly creates a geometry without previously generating
these files, the `config.json` file will be used to create the essential
`channelmap` and `special_metadata` information on the fly, without creating any
files.

The `--generate-metadata` option has four additional arguments. The first three
arguments should only ever be used by very experienced users (as i can not
really think of a usecase for them...). They take the path to the input and
output files, defaulting to the path in the config folder where they are
expected to be... The fourth argument lets the user choose a HPGe detector from
the [`legend-metadata`](https://github.com/legend-exp/legend-metadata) package,
which will be used to replace all HPGe detectors in the geometry.

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
should be explained in the geometry section (WIP ADD LINK TO THAT PART HERE).

Additionally there is more information about detailed structures in there.

### Global HPGe string configuration

- `hpge_string` → HPGe string number
  - `radius_in_mm` → radial distance from the center of the cryostat to the
    string
  - `angle_in_deg` → azimutal position of the string with respect to the
    positive x-direction
  - `minishroud_radius_in_mm` → radius of the minishroud of this string
  - `minishroud_delta_length_in_mm` → modification of the default length of a
    NMS. If unspecified, 0 will be used.
  - `rod_radius_in_mm` → placement radius of the support rod of this string

### HPGe detector unit configuration

- `hpges` → HPGe detector name
  - `rodlength_in_mm` → length of the copper rods next to this detector. This is
    a "warm" length, i.e. it is multiplied by a factor < 1 to get the shorter
    rod length in the cryostat.
  - `baseplate` → size of the PEN plate below this detector (one value out of
    `small`, `medium`, `large`, `xlarge`)

    Depending on the other detector properties, the value might be transformed,
    i.e. for Ortec ICPCs to `medium_ortec`.

### Calibration tube configuration

- `calibration` → Calibration tube number
  - `radius_in_mm` → radial distance from the center of the cryostat to the
    calibration tube
  - `angle_in_deg` → azimutal position of the calibration tube with respect to
    the positive x-direction
  - `tube_radius_in_mm` → radius of the tube itself
  - `length_in_mm` → length of the calibration tube below the top copper plate

### Watertank instrumentation

- `tyvek` → The reflective tyvek foil planned to split the water tank in two
  sections
  - `faces` → Number of faces, as it is a polycone and not a cylinder
  - `r` → radius of the tyvek polycone in mm
