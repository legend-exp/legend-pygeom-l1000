# Visualization

The `legend-pygeom-l1000` package provides powerful visualization capabilities
through VTK (Visualization Toolkit), allowing you to inspect and explore the
geometry interactively.

## Basic Visualization

### Opening the Viewer

The simplest way to visualize a geometry is:

```console
legend-pygeom-l1000 --visualize
```

This generates the geometry using default settings and immediately opens an
interactive 3D viewer window.

### Visualizing with GDML Output

To save the geometry and visualize it simultaneously:

```console
legend-pygeom-l1000 --visualize l1000.gdml
```

This creates both the GDML file and opens the visualization.

## Viewer Controls

Once the VTK viewer window is open, you can interact with the geometry using
your mouse and keyboard:

### Mouse Controls

- **Left Click + Drag**: Rotate the view around the geometry
- **Middle Click + Drag**: Pan the view (move the camera position)
- **Right Click + Drag**: Zoom in and out
- **Scroll Wheel**: Zoom in and out (alternative method)

### Keyboard Shortcuts

Common VTK viewer shortcuts include:

- **r**: Reset the camera to show the entire geometry
- **w**: Toggle wireframe mode
- **s**: Toggle surface rendering
- **3**: Toggle 3D stereo mode (if supported)
- **q** or **e**: Quit the viewer

## Scene Configuration Files

Scene files allow you to customize the visualization settings, including camera
position, rendering quality, and display options.

### Creating a Scene File

Create a JSON file (e.g., `scene.json`) with your desired settings:

```json
{
  "fine_mesh": true,
  "camera_position": [0, 0, 5000],
  "camera_focal_point": [0, 0, 0],
  "camera_view_up": [0, 1, 0],
  "background_color": [0.1, 0.1, 0.15],
  "window_size": [1920, 1080]
}
```

### Using a Scene File

Pass the scene file to the `--visualize` option:

```console
legend-pygeom-l1000 --visualize scene.json l1000.gdml
```

### Scene File Options

#### Mesh Quality

- `fine_mesh` (boolean): When `true`, uses high-quality mesh rendering with 100
  slices/stacks. This produces smoother surfaces but increases memory usage and
  rendering time.
  - Default: `false`
  - Example: `"fine_mesh": true`

#### Camera Configuration

Control the initial camera position and orientation:

- `camera_position` (array): [x, y, z] coordinates of the camera position in mm
  - Example: `"camera_position": [0, 0, 5000]`

- `camera_focal_point` (array): [x, y, z] coordinates where the camera looks
  - Example: `"camera_focal_point": [0, 0, 0]`

- `camera_view_up` (array): [x, y, z] vector defining the "up" direction
  - Example: `"camera_view_up": [0, 1, 0]`

#### Display Settings

- `background_color` (array): [r, g, b] values from 0 to 1 for background color
  - Example: `"background_color": [1, 1, 1]` (white background)
  - Example: `"background_color": [0, 0, 0]` (black background)

- `window_size` (array): [width, height] in pixels for the viewer window
  - Example: `"window_size": [1920, 1080]`

### Example Scene Configurations

#### Close-up View of Cryostat

```json
{
  "camera_position": [2000, 2000, 1000],
  "camera_focal_point": [0, 0, -500],
  "background_color": [0.9, 0.9, 0.95],
  "fine_mesh": true
}
```

#### Top-Down View

```json
{
  "camera_position": [0, 5000, 0],
  "camera_focal_point": [0, 0, 0],
  "camera_view_up": [0, 0, 1],
  "background_color": [0.2, 0.2, 0.25]
}
```

#### Presentation View (High Quality)

```json
{
  "fine_mesh": true,
  "camera_position": [3000, 3000, 3000],
  "camera_focal_point": [0, 0, 0],
  "background_color": [1, 1, 1],
  "window_size": [2560, 1440]
}
```

## Geant4 Visualization Macros

For use with Geant4 simulations, you can generate macro files that define
visualization attributes and detector configurations.

### Visualization Attributes Macro

Generate a macro file with color and visibility settings:

```console
legend-pygeom-l1000 --vis-macro-file vis.mac l1000.gdml
```

This creates a `vis.mac` file containing Geant4 commands to set colors,
transparency, and visibility for different geometry components. This macro can
be used with Geant4's visualization commands to customize how the geometry
appears in Geant4 viewers (OpenGL, Qt, DAWN, etc.).

Example usage in Geant4:

```
/control/execute vis.mac
/vis/open OGL
/vis/drawVolume
```

### Detector Configuration Macro

Generate a macro file listing all active detectors for remage:

```console
legend-pygeom-l1000 --det-macro-file detectors.mac l1000.gdml
```

This creates a `detectors.mac` file that remage can use to identify which
volumes should be treated as sensitive detectors in the simulation.

### Combined Example

Generate both macro files along with the GDML:

```console
legend-pygeom-l1000 \
  --vis-macro-file vis.mac \
  --det-macro-file detectors.mac \
  l1000.gdml
```

## Visualization Workflow

### 1. Initial Exploration

Start with basic visualization to get familiar with the geometry:

```console
legend-pygeom-l1000 --visualize
```

Use mouse controls to explore different views and identify regions of interest.

### 2. Focused Visualization

Create scene files for specific views you want to examine in detail:

```console
legend-pygeom-l1000 --visualize detector_view.json l1000.gdml
```

### 3. Quality Check

Use fine mesh rendering to check surface quality:

```json
{
  "fine_mesh": true
}
```

```console
legend-pygeom-l1000 --visualize fine_scene.json l1000.gdml
```

### 4. Documentation and Presentations

Create high-quality renderings with custom lighting and camera angles:

```console
legend-pygeom-l1000 --visualize presentation.json l1000.gdml
```

## Tips and Best Practices

### Performance

- **Start simple**: Begin with default visualization before enabling `fine_mesh`
- **Selective assembly**: Use `--assemblies` to visualize only the components
  you're interested in
- **Memory considerations**: Fine mesh rendering requires significantly more
  memory for large geometries

### Debugging Geometry

- **Wireframe mode**: Press `w` in the viewer to see through volumes and
  identify overlaps
- **Rotation**: Rotate the view completely around to check all angles
- **Reset view**: Press `r` to reset the camera if you lose orientation

### Creating Scene Files

- **Iterate**: Start with default view, adjust camera position interactively,
  then note the angles you prefer
- **Multiple scenes**: Create different scene files for different perspectives
  (overview, detail views, etc.)
- **Version control**: Keep scene files in version control alongside geometry
  configurations

### Capturing Images

Most VTK viewers allow you to save screenshots:

- Look for a screenshot button in the viewer toolbar
- Or use your operating system's screenshot functionality
- For publication-quality images, use `fine_mesh` and high window resolution

## Troubleshooting

### Viewer Doesn't Open

- Ensure you have a working display (X11 on Linux, or appropriate display
  server)
- Check that VTK is properly installed with rendering support
- Try the `--debug` flag to see detailed error messages

### Geometry Appears Incomplete

- Check that all required assemblies are included (don't use `--assemblies`
  unless intentional)
- Verify the detail level is appropriate: `--detail full` for complete geometry
- Review the console output for warnings or errors during geometry construction

### Slow Performance

- Disable `fine_mesh` if enabled
- Reduce the number of assemblies with `--assemblies`
- Close other applications to free up system memory and GPU resources
- Use `--detail simple` for faster geometry generation
