bl_info = {
    "name": "LIGGGHTS Particle Visualization",
    "author": "Your Name",
    "version": (0, 8, 3),  # Updated version with memory optimizations
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > LIGGGHTS",
    "description": "Import and visualize LIGGGHTS particle simulation data",
    "category": "Import-Export",
    "doc_url": "",  # Add documentation URL if available
    "tracker_url": "",  # Add bug tracker URL if available
}

import bpy
from . import particle_dataset, operators, ui, optimized_parser

classes = (
    particle_dataset.ReferencePosition,
    particle_dataset.ParticleDataset,
    ui.LIGGGHTS_PT_main_panel,
    ui.LIGGGHTS_OT_clear_cache,  # Register the new cache clearing operator
    operators.LIGGGHTS_OT_import_particles,
    operators.LIGGGHTS_OT_set_reference,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.liggghts_dataset = bpy.props.PointerProperty(type=particle_dataset.ParticleDataset)
    bpy.types.WindowManager.particle_object = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.is_setting_reference = bpy.props.BoolProperty(default=False)

def unregister():
    # Clean up frame change handlers
    operators.LIGGGHTS_OT_import_particles.cleanup_handler()
    
    # Clean up any caches
    try:
        from . import numpy_loader
        numpy_loader.LIGGGHTSDataLoader.clear_cache()
    except:
        pass
    
    # Remove properties
    if hasattr(bpy.types.Scene, "is_setting_reference"):
        del bpy.types.Scene.is_setting_reference
    if hasattr(bpy.types.WindowManager, "particle_object"):
        del bpy.types.WindowManager.particle_object
    if hasattr(bpy.types.Scene, "liggghts_dataset"):
        del bpy.types.Scene.liggghts_dataset
        
    # Unregister classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

if __name__ == "__main__":
    register()
