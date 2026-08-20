# Description of the geometry

This page is a visual tour of the parts that are currently implemented, from a
single detector unit out to the cavern.

:::{note}

All renderings on this page are produced by `docs/generate_docs_images.py`. Run
it after changing the geometry and inspect the resulting images. Comparing them
against the committed ones is a quick way to spot an unintended change.

:::

Which parts end up in a geometry is controlled by the _detail level_ and the
selected assemblies, both described in {doc}`runtime-cfg`.

## Detector unit

The smallest repeated building block is the detector unit consisting of one HPGe
detector sitting on a PEN plate, held by holders attached to three copper rods.

```{subfigure} AB
:subcaptions: above

:::{image} ./images/detector_unit.png
:height: 400px
:alt: Detector unit at the radiogenic detail level.
:::

:::{image} ./images/detector_unit_cosmogenic.png
:height: 400px
:alt: Detector unit at the cosmogenic detail level.
:::

```

&nbsp;

The left figure shows the `radiogenic` detail level, which includes high detail
on the front-end, including the signal and HV cables running along the unit,
their Ultem clamps, the ASIC, and the Ultem insulators and copper weldments that
fix the unit to the rods. The right figure is the same unit at the `cosmogenic`
level, where many of the front-end details are removed to reduce complexity in
tracking large number of particles in the high-energy interactions of
atmospheric muons.

## Detector string

Eight detector units are stacked into a string, suspended from a copper hanger.

```{subfigure} AB
:subcaptions: above

:::{image} ./images/string.png
:height: 500px
:alt: A single detector string.
:::

:::{image} ./images/string_fibers.png
:height: 500px
:alt: A detector string surrounded by its fiber curtain.
:::

```

&nbsp;

The right figure adds the TPB coated fiber curtain that surrounds each string.
Every string carries its own barrel of wavelength-shifting fibers, read out at
both ends by SiPM modules.

The detail level also selects between the two fiber models: `detailed` places
every individual fiber, `simple` places coarse segments instead. The figure uses
the detailed model.

## The reentrance tube

```{image} ./images/array_reentrance_tube.png
:height: 600px
:alt: The full array inside the reentrance tube.
```

All strings together hang in the lower part of the reentrance tube which extends
far above through the neck of the cryostat. The number of strings, their
positions and the number of units per string are all set in the pre-compiled
config files (see {doc}`runtime-cfg`).

## Cryostat

```{image} ./images/array_cryostat.png
:height: 600px
:alt: The array and reentrance tube inside the cryostat.
```

The reentrance tube sits inside a stainless steel cryostat filled with liquid
argon. The cryostat is a double-walled vessel, with the inner wall in contact
with the liquid argon and the outer wall exposed to the water tank. The vacuum
gap between the walls provides thermal insulation.

In addition, the coloured bands on the reentrance tube draw its structural
layers: EFCu copper (transparent), OFHC copper (brown) and 316L stainless steel
(blue-grey) above it.

## Water tank and muon veto

```{image} ./images/watertank.png
:height: 600px
:alt: The cryostat inside the instrumented water tank.
```

The cryostat stands in a water tank acting as a Cherenkov muon veto. The tank is
lined with a Tyvek reflector and instrumented with PMTs on the wall and on the
floor. Their number and arrangement are configurable.

## Cavern (LNGS Hall A)

```{image} ./images/cavern.png
:height: 600px
:alt: The water tank inside the cavern.
```

Finally the whole setup sits in a cavern approximating the geometry of LNGS Hall
A: a box with an elliptical ceiling, plus a cylindrical pit that the bottom of
the water tank sits in.
