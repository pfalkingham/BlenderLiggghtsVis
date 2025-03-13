# LIGGGHTS Particle Visualization

A Blender addon for importing and visualizing LIGGGHTS particle simulation data.

## Features

- Import LIGGGHTS dump files as particles in Blender
- Automatic frame sequence detection
- Reference frame support for displacement visualization
- Dynamic updates when changing frames
- Geometry Nodes visualization

## Installation

1. Download the addon ZIP file
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install..." and select the ZIP file
4. Enable the addon by checking the box

## Usage

1. In the 3D Viewport, open the sidebar (N key)
2. Select the "LIGGGHTS" tab
3. Click "Import Particle Data" and select any frame file from your simulation
4. Use Blender's timeline to navigate through frames
5. Optionally set a reference frame to visualize particle displacement

## File Format

The addon expects LIGGGHTS dump files with at least the following columns:
- id
- x, y, z (particle positions)
- radius

## Version History

- 0.7.0: Improved error handling and performance optimizations
- 0.6.8: Initial public release

## License

[Your license information here]

## Contact

[Your contact information here]
