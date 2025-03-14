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
            box.label(text="Reference Frame")
            box.operator("liggghts.set_reference", text="Set Reference Frame")
            
            if dataset.reference_frame != -1:
                box.label(text=f"Reference Frame: {dataset.reference_frame}")
            
            # Performance optimization settings
            perf_box = layout.box()
            perf_box.label(text="Performance Settings")
            
            # Parser settings
            parser_row = perf_box.row()
            parser_row.prop(dataset, "use_optimized_parser", text="Use NumPy Parser")
            
            # Mesh update settings
            mesh_row = perf_box.row()
            mesh_row.prop(dataset, "use_mesh_update", text="Update Vertices")
            
            # Cache settings
            cache_row = perf_box.row()
            cache_row.prop(dataset, "use_data_caching", text="Cache Frames")
            
            # Only show cache size if caching is enabled
            if dataset.use_data_caching:
                cache_size_row = perf_box.row()
                cache_size_row.prop(dataset, "max_cache_size")
                
                # Add cache stats and clear button
                cache_stats = dataset.get_cache_stats()
                if cache_stats["cache_size"] > 0:
                    stats_row = perf_box.row()
                    stats_row.label(text=f"Cache: {cache_stats['cache_size']} frames, {cache_stats['hit_rate']:.1%} hit rate")
                    clear_cache = perf_box.row()
                    clear_cache.operator("liggghts.clear_cache", text="Clear Cache")
            
            # Advanced options box
            adv_box = layout.box()
            adv_box.label(text="Advanced Options")
            thread_row = adv_box.row()
            thread_row.prop(dataset, "use_parallel_processing", text="Parallel Processing")
            # Add note about parallel processing (it's not very useful but provides info to user)
            if dataset.use_parallel_processing:
                note_row = adv_box.row()
                note_row.label(text="Note: May not improve performance")
                note_row.label(text="on I/O-bound loads")

# Operator to clear the cache
class LIGGGHTS_OT_clear_cache(bpy.types.Operator):
    bl_idname = "liggghts.clear_cache"
    bl_label = "Clear Cache"
    bl_description = "Clear the frame cache to free memory"
    
    def execute(self, context):
        dataset = context.scene.liggghts_dataset
        if dataset.clear_cache():
            self.report({'INFO'}, "Cache cleared successfully")
        else:
            self.report({'WARNING'}, "Failed to clear cache")
        return {'FINISHED'}
