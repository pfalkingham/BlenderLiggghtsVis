# BlenderLiggghtsVis v0.8.2
Repository for Blender addon to visualize liggghts output


This is fantastically bare-bones at the minute, but has enough functionality that I want to get a snapshot of this up on github.

## Blender LIGGGHTS Reader

This addon can import particle data as output from LIGGGHTS (and maybe LAMMPS but I haven't tried yet).  Currently, it will only accept ascii data, not binary, though I am working on that.

 - zip it and add as an addon in blender manually (v1 might go to the extensions market place but probably not, as it's pretty niche)
 - this provides a new tab on the right of the 3D viewport called 'LIGGGHTS'
 - click the button and select a file.  It _should_ figure out the sequence of files in the directory, but parsing filenames is not bullet proof.
 - You can then scrub the timeline (slow*) and it will change files.
 - You can set a reference frame, which will take XYZ positions from that frame and add them as attributes to other frames for visuzalization of displacement etc.
 - Shading of variables is handled via geometry nodes and shader nodes.

# Very much a work in progress.
