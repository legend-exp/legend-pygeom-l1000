# Features for geometry development

## Registering detectors for use with [`remage`](https://github.com/legend-exp/remage)

The `legend-pygeom-l1000` package can export detector registration information
for use with remage simulations. This information can be exported by using
`--det-macro-file=l1000-dets.mac` as an additional CLI option.

### Usage

```console
legend-pygeom-l1000 --det-macro-file=l1000-dets.mac l1000.gdml
```

This generates a Geant4 macro file (`l1000-dets.mac`) that contains commands to
register all sensitive detectors in the geometry. The macro should be executed
in your main remage macro file:

```
/control/execute l1000-dets.mac
```

### What gets registered

The detector macro includes:

- **HPGe detectors**: All germanium detectors with their unique names (e.g.,
  `V01234A`)
- **Optical detectors**: SiPMs, PMTs, and other optical sensors
- **LAr instrumentation**: Active LAr veto volumes if configured

Each detector is registered with:

- Physical volume name
- Detector type
- Unique identifier for data output

### Integration with remage

The generated macro works with remage's detector construction system. See the
[remage documentation](https://remage.readthedocs.io/) and
[legend-pygeom-tools detector registration docs](https://legend-pygeom-tools.readthedocs.io/en/stable/detector-registration.html)
for more details.

## Checking for overlaps

Geometry overlaps (where two volumes occupy the same space) can cause simulation
errors and produce incorrect results. It's critical to check for overlaps before
using a geometry for production simulations.

### Why not use `--check-overlaps`?

The `--check-overlaps` CLI option exists but has limitations:

```console
legend-pygeom-l1000 --check-overlaps l1000.gdml
```

**Issues with this approach:**

- Uses coarsely tessellated volumes (same as visualization)
- May miss overlaps or report false positives
- Very slow for complex geometries
- Not as accurate as Geant4's native overlap checker

**Recommendation**: Use Geant4/remage for overlap checking instead.

### Checking overlaps with Geant4/remage (recommended)

The most reliable way to check for overlaps is to use Geant4's built-in overlap
checker through remage.

#### Step 1: Create a macro file

Create a file called `check-overlaps.mac` with the following contents:

```
/RMG/Manager/Logging/LogLevel error
/run/initialize
```

#### Step 2: Run the overlap check

Use remage to load your GDML file and check for overlaps:

```console
remage check-overlaps.mac -g l1000.gdml
```

This will:

1. Load the GDML file into Geant4
2. Validate that the geometry is correctly formatted
3. Perform a comprehensive overlap check on all volumes
4. Report any overlaps found with detailed information

### Interpreting overlap results

If overlaps are found, Geant4 will report:

- The names of the overlapping volumes
- The overlap region location
- The overlap size

Example output:

```
-------- WWWW ------- G4Exception-START -------- WWWW -------
*** G4Exception : GeomVol1002
      issued by : G4PVPlacement::CheckOverlaps()
Overlap of 0.123 mm between volume 'detector_1' and 'nms_1_lower'
  at position: (245.3, 0.0, -350.2) mm
*** This is just a warning message. ***
-------- WWWW -------- G4Exception-END --------- WWWW -------
```

### Fixing overlaps

Common causes and solutions:

1. **Dimension errors**: Check component sizes in special_metadata.yaml
2. **Positioning errors**: Verify string and detector positions
3. **Thermal contraction**: Ensure proper scaling factors
4. **Custom configurations**: Review any modified geometry parameters

After fixing, always re-run the overlap check.

## Visualization macros

Generate visualization attribute macros for Geant4 visualization:

```console
legend-pygeom-l1000 --vis-macro-file=l1000-vis.mac l1000.gdml
```

The generated macro file (`l1000-vis.mac`) sets colors, transparency, and
visibility for different geometry components.

### Using the visualization macro

Create a file `vis.mac` in the same directory:

```
/run/initialize

/vis/open OGL
/vis/drawVolume lar

/vis/viewer/set/defaultColour black
/vis/viewer/set/background white
/vis/viewer/set/viewpointVector -3 -2 1
/vis/viewer/set/upVector 0 0 1
/vis/viewer/set/rotationStyle freeRotation
/vis/viewer/set/lineSegmentsPerCircle 100

/vis/scene/add/trajectories smooth
/vis/scene/endOfEventAction accumulate

# Import the auto-generated visualization attributes
/control/execute l1000-vis.mac

/vis/scene/add/axes 0 0 0 500 mm
/vis/viewer/flush
```

Run with remage:

```console
remage vis.mac -i -g l1000.gdml
```

This opens an interactive Geant4 visualization window with proper colors and
attributes applied.

## Development workflow

### Recommended workflow for geometry changes

1. **Make changes** to geometry code or configuration

2. **Generate geometry**:

   ```console
   legend-pygeom-l1000 l1000_test.gdml
   ```

3. **Quick visual check**:

   ```console
   legend-pygeom-l1000 --visualize l1000_test.gdml
   ```

4. **Check for overlaps**:

   ```console
   remage check-overlaps.mac -g l1000_test.gdml
   ```

5. **Generate production files** (only after passing checks):
   ```console
   legend-pygeom-l1000 \
     --det-macro-file=l1000-dets.mac \
     --vis-macro-file=l1000-vis.mac \
     l1000.gdml
   ```

### Testing with specific assemblies

For faster iteration when working on specific components:

```console
# Test only the component you're working on
legend-pygeom-l1000 --assemblies=hpge_strings --visualize test.gdml

# Check overlaps for specific assembly
remage check-overlaps.mac -g test.gdml
```

**Warning**: Don't use stripped-down geometries (from `--assemblies`) for
production simulations. They're missing components and will give incorrect
results.

## Testing different detail levels

Test all detail levels to ensure consistency:

```console
# Simple
legend-pygeom-l1000 --detail simple simple.gdml
remage check-overlaps.mac -g simple.gdml

# Radiogenic (default)
legend-pygeom-l1000 --detail radiogenic radiogenic.gdml
remage check-overlaps.mac -g radiogenic.gdml

# Full
legend-pygeom-l1000 --detail full full.gdml
remage check-overlaps.mac -g full.gdml
```

## Debugging geometry issues

### Enable verbose output

```console
legend-pygeom-l1000 --debug l1000.gdml
```

This provides detailed logging of:

- Geometry construction steps
- Material creation
- Volume placement
- Surface definitions

### Check specific volumes

Use Geant4 visualization to inspect specific volumes:

```
# In Geant4 macro
/vis/viewer/set/culling global false
/vis/viewer/set/culling invisible false
/vis/specify volume_name
/vis/viewer/flush
```

### Python debugging

For development, you can use the package programmatically:

```python
from pygeoml1000 import core

# Build geometry with custom parameters
registry = core.construct(
    assemblies=["strings", "calibration"], detail_level="full", config=my_config_dict
)

# Access volumes directly
world_lv = registry.worldVolume
# Inspect, modify, or debug as needed
```

## Performance tips

### For faster iteration

1. **Use `--detail simple`** during development
2. **Limit assemblies** with `--assemblies` to only what you need
3. **Disable overlap checking** (`--check-overlaps`) during rapid prototyping
4. **Use visualization** instead of full simulation for quick checks

### For production

1. **Always use `--detail full`** or `radiogenic` as appropriate
2. **Include all relevant assemblies**
3. **Run complete overlap check with Geant4/remage**
4. **Validate with test simulations** before production use

## Common pitfalls

### Geometry validation

- ❌ Don't trust `--check-overlaps` alone
- ✅ Always validate with Geant4/remage
- ❌ Don't skip overlap checks for "small" changes
- ✅ Check overlaps for every geometry variant

### Configuration management

- ❌ Don't manually edit GDML files
- ✅ Make changes in code or configuration files
- ❌ Don't reuse geometries with different detector configurations
- ✅ Generate new GDML for each configuration

### Assembly selection

- ❌ Don't use `--assemblies` for production simulations
- ✅ Use it only for development and visualization
- ❌ Don't assume stripped geometry is "close enough"
- ✅ Run full geometry for any physics results

## Resources

- [remage documentation](https://remage.readthedocs.io/)
- [legend-pygeom-tools](https://legend-pygeom-tools.readthedocs.io/)
- [pyg4ometry documentation](https://pyg4ometry.readthedocs.io/)
- [Geant4 visualization guide](https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Visualization/visualization.html)
