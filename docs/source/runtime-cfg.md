# Runtime configuration

For frequently-changing details of the geometry, configuration is managed using
runtime configuration files. This allows flexibility without modifying code.

```{warning}

This might be subject to change as discussed in metadata documentation.

```

## Configuration file format

Runtime configuration files use **JSON** or **YAML** format and are specified
using the `--config` parameter:

```console
legend-pygeom-l1000 l1000.gdml --config my_config.json
```

## Configuration structure

A typical configuration file contains settings for:

### 1. Detector array layout

Configuration for detector strings, positions, and spacing:

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

### 2. Detail levels

Control which components are included and at what detail level:

```json
{
  "detail": {
    "radiogenic": {
      "cavern": "omit",
      "labs": "omit",
      "watertank": "omit",
      "watertank_instrumentation": "omit",
      "cryostat": "simple",
      "HPGe_dets": "metadata"
    }
  }
}
```

### 3. Water tank instrumentation

PMT positions and optical detector configuration:

```json
{
  "pmts_pos": {
    "floor": {
      "row1": {
        "n": 50,
        "r": 3800
      }
    },
    "wall": {
      "row1": {
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

### 4. Dummy detector specifications

Properties of dummy detectors when not using real detector data:

```json
{
  "dummy_dets": {
    "hpge": {
      "type": "icpc",
      "geometry": {
        "height_in_mm": 100,
        "radius_in_mm": 42.0
      }
    }
  }
}
```

## Relationship to metadata files

The runtime configuration system works in conjunction with metadata files:

- **config.json**: High-level geometry parameters and detector types
- **special_metadata.yaml**: Detailed spatial configuration (generated from
  config or created manually)
- **channelmap.json**: Detector mapping and electronics configuration (generated
  from config or from legend-metadata)

### Generation workflow

```console
# Generate metadata from configuration
legend-pygeom-l1000 --generate-metadata --metadata-config my_config.json

# Use generated metadata to create geometry
legend-pygeom-l1000 --config my_config.json l1000.gdml
```

## CLI vs config file options

Some options can be specified either via CLI or in the config file. **CLI
options override config file values**.

### Example: Detail level

Via CLI:

```console
legend-pygeom-l1000  l1000.gdml --detail radiogenic
```

Via config file:

```json
{
  "detail_level": "radiogenic"
}
```

```console
legend-pygeom-l1000 --config my_config.json l1000.gdml
```

### Example: Assemblies

Via CLI:

```console
legend-pygeom-l1000 --assemblies watertank,cryo,hpge_strings l1000.gdml
```

Via config file:

```json
{
  "assemblies": ["watertank", "cryostat", "HPGe_dets"]
}
```

## Best practices

### Configuration file organization

1. **Use descriptive names**: `l1000_full_with_tank.json` instead of
   `config1.json`
2. **Version control**: Keep configuration files in version control
3. **Document changes**: Add comments (in YAML) or separate documentation for
   major changes
4. **Separate concerns**: Use different files for different geometry variants

### When to use CLI vs config file

**Use CLI options when**:

- Quick one-time changes
- Testing different settings rapidly
- Overriding a single parameter

**Use config file when**:

- Complex multi-parameter configurations
- Repeatable geometry variants
- Production geometries that need documentation
- Sharing configurations with collaborators

### Configuration management workflow

1. **Start with default**: Use `src/pygeoml1000/configs/config.json` as a
   template
2. **Copy and modify**: Create your own configuration file
3. **Test thoroughly**: Generate geometry and check overlaps
4. **Document**: Note what changes were made and why
5. **Archive**: Keep configurations with their corresponding GDML files

## Example configurations

### Compact detector array

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

This creates a more compact array with closer detector spacing.

### High-PMT-density water tank

```json
{
  "pmts_pos": {
    "floor": {
      "row1": { "n": 60, "r": 3800 },
      "row2": { "n": 40, "r": 3000 },
      "row3": { "n": 20, "r": 1800 }
    }
  }
}
```

Increases PMT density for better muon veto efficiency.

### Minimal geometry for testing

```json
{
  "detail": {
    "simple": {
      "cavern": "omit",
      "labs": "omit",
      "watertank": "omit",
      "watertank_instrumentation": "omit",
      "cryostat": "simple",
      "HPGe_dets": "simple"
    }
  }
}
```

Minimal geometry for fast generation and testing.

## References

- Metadata configuration details: {doc}`metadata`
- CLI options: {doc}`cli_usage`
