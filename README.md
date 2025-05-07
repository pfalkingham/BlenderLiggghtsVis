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

1. In the 3D Viewport, open the sidebar
2. Select the "LIGGGHTS" tab
3. Click "Import Particle Data" and select any frame file from your simulation
4. Use Blender's timeline to navigate through frames
5. Optionally set a reference frame to visualize particle displacement (visualization needs a mix of custom geometry nodes and shader nodes)

## File Format

The addon expects LIGGGHTS dump files with at least the following columns:
- id
- x, y, z (particle positions)
- radius

## Version History

- 0.9.0: Removed a bug duplicating reference data, made sure reference is applied when clicked, and added a much better geometry nodes setup.
- 0.8.3b: Has a cachine system, and is overall just much faster.
- 0.8.2: Can read fx/fy/fz and other attributes (untested)
- 0.7.0: Improved error handling and performance optimizations
- 0.6.8: Initial public release

## To do

- read more flexibly:
	-- file name parsing more robust
	-- unknown attributes
- read binary files
- add a clear referrence button?  Not super necessary (no realy penalty to keeping reference, and can overwrite at any time), but a bit cleaner.
~~- make sure reference is applied to current frame when you click set reference~~
~~- cache files.  maybe dynamically keep track of RAM?  maybe enter size of cache first? dunno.  It's _very_ slow at the moment.~~
  ~~-- a button to flush cache would be useful to do before rendering maybe.~~

## Contact

via github.
