# Additional geometry metadata

The files in this directory contain metadata describing the geometry, that might
change over time (i.e. between deployments). In principle, all metadata should
be upstreamed to `legend-metadata` at some point; but it currently is not.

This metadata is passed to all instrumentation modules, stored as
`special_metadata` on each `InstrumentationData` instance.

## Global HPGe string configuration

- `hpge_string` → HPGe string number
  - `radius_in_mm` → radial distance from the center of the cryostat to the
    string
  - `angle_in_deg` → azimutal position of the string with respect to the
    positive x-direction
  - `minishroud_radius_in_mm` → radius of the minishroud of this string
  - `minishroud_delta_length_in_mm` → modification of the default length of a
    NMS. If unspecified, 0 will be used.
  - `rod_radius_in_mm` → placement radius of the support rod of this string

## HPGe detector unit configuration

- `hpges` → HPGe detector name
  - `rodlength_in_mm` → length of the copper rods next to this detector. This is
    a "warm" length, i.e. it is multiplied by a factor < 1 to get the shorter
    rod length in the cryostat.
  - `baseplate` → size of the PEN plate below this detector (one value out of
    `small`, `medium`, `large`, `xlarge`)

    Depending on the other detector properties, the value might be transformed,
    i.e. for Ortec ICPCs to `medium_ortec`.

## Calibration tube configuration

- `calibration` → Calibration tube number
  - `radius_in_mm` → radial distance from the center of the cryostat to the
    calibration tube
  - `angle_in_deg` → azimutal position of the calibration tube with respect to
    the positive x-direction
  - `tube_radius_in_mm` → radius of the tube itself
  - `length_in_mm` → length of the calibration tube below the top copper plate
