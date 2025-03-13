import bpy
from . import bl_info

class LIGGGHTS_PT_main_panel(bpy.types.Panel):
    bl_label = "LIGGGHTS Particle Visualization"
    bl_idname = "LIGGGHTS_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LIGGGHTS"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        dataset = scene.liggghts_dataset
        
        # Version display
        version = ".".join(str(x) for x in bl_info["version"])
        layout.label(text=f"v{version}")
        layout.separator()
        
        # Import button
        layout.operator("liggghts.import_particles", text="Import Particle Data")
        
        # Dataset info
        if dataset.filepath_pattern:
            layout.label(text=f"Selected Dataset: {bpy.path.basename(dataset.filepath_pattern)}")
            
            # Reference frame section
            box = layout.box()
            box.operator("liggghts.set_reference", text="Set Reference Frame")
            
            if dataset.reference_frame != -1:
                box.label(text=f"Reference Frame: {dataset.reference_frame}")
            
            # Performance optimization settings
            box = layout.box()
            box.label(text="Performance Settings")
            box.prop(dataset, "use_optimized_parser", text="Use NumPy Parser")
            box.prop(dataset, "use_mesh_update", text="Update Vertices")
            box.prop(dataset, "use_parallel_processing", text="Parallel Processing")
