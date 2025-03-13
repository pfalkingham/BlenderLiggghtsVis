import bpy
import os
import numpy as np
from bpy_extras.io_utils import ImportHelper
from . import utils
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy_extras.object_utils import object_data_add
from bpy.types import Operator
from mathutils import Vector, Matrix
from . import optimized_parser

class LIGGGHTS_OT_import_particles(bpy.types.Operator, ImportHelper):
    bl_idname = "liggghts.import_particles"
    bl_label = "Import Particle Data"
    
    filename_ext = ""
    filter_glob: bpy.props.StringProperty(default="*.*", options={'HIDDEN'})
    
    _is_updating = False  # Class variable to track updates
    _current_frame = None  # Track current frame to avoid duplicate updates

    filepath: StringProperty(subtype='FILE_PATH')
    start_line: IntProperty(name="Start Line", default=0, description="Line number to start reading particle data from")
    max_particles: IntProperty(name="Max Particles", default=0, description="Maximum number of particles to import (0 for all)")
    use_reference_object: BoolProperty(name="Use Reference Object", default=False, description="Use a reference object for particle positions")
    reference_object: StringProperty(name="Reference Object", default="", description="Name of the reference object")

    def execute(self, context):
        dirname = os.path.dirname(self.filepath)
        basename = os.path.basename(self.filepath)
        
        # Validate input file exists
        if not os.path.exists(self.filepath):
            self.report({'ERROR'}, f"File not found: {self.filepath}")
            return {'CANCELLED'}
        
        # Extract frame pattern
        frame_info = utils.extract_frame_number_pattern(basename)
        if not frame_info:
            self.report({'ERROR'}, "Could not find frame number in filename")
            return {'CANCELLED'}
        
        # Setup dataset
        dataset = context.scene.liggghts_dataset
        dataset.filepath_pattern = os.path.join(dirname, frame_info['pattern'])
        
        # Find matching files
        matching_files = utils.find_matching_files(dirname, frame_info['pattern'])
        if not matching_files:
            self.report({'ERROR'}, f"No matching files found for pattern: {frame_info['pattern']}")
            return {'CANCELLED'}
        
        # Configure dataset
        numbers = [n for n, _ in matching_files]
        dataset.file_start = numbers[0]
        dataset.file_end = numbers[-1]
        dataset.file_increment = numbers[1] - numbers[0] if len(numbers) > 1 else 1
        
        # Set frame range
        context.scene.frame_start = 1
        context.scene.frame_end = len(numbers)
        dataset.start_frame = 1
        dataset.end_frame = len(numbers)
        
        # Clean up existing object if present
        if hasattr(context.window_manager, "particle_object") and context.window_manager.particle_object:
            try:
                old_obj = context.window_manager.particle_object
                bpy.data.objects.remove(old_obj, do_unlink=True)
            except:
                pass
        
        # Create mesh object
        mesh = bpy.data.meshes.new("ParticleSystem")
        obj = bpy.data.objects.new("Particles", mesh)
        context.scene.collection.objects.link(obj)
        context.window_manager.particle_object = obj
        
        # Setup geometry nodes
        self._setup_geometry_nodes(obj)
        
        # Setup animation handling
        self._setup_animation_handler(context)
        
        self.report({'INFO'}, f"Imported {len(matching_files)} frames from {basename}")
        
        # Use max_particles=None to read all particles if the user sets it to 0
        max_particles = self.max_particles if self.max_particles > 0 else None
        
        data, additional_data = optimized_parser.parse_data(self.filepath, self.start_line, max_particles)
        
        if len(data) == 0:
            self.report({'ERROR'}, "No particle data found or error during parsing.")
            return {'CANCELLED'}
        
        # Create mesh and object
        mesh = bpy.data.meshes.new("LIGGGHTS_Particles")
        obj = bpy.data.objects.new("LIGGGHTS_Particles", mesh)
        
        # Add object to scene
        context.collection.objects.link(obj)
        
        # Create vertices from data
        verts = [Vector(row) for row in data]
        mesh.from_pydata(verts, [], [])
        
        # Update mesh geometry
        mesh.update()
        
        # Add additional data as vertex attributes
        for name, values in additional_data.items():
            if len(values) == len(verts):
                # Create a new attribute
                attribute = mesh.attributes.new(name=name, type='FLOAT_VECTOR', domain='POINT')
                
                # Assign the values to the attribute
                for i, value in enumerate(values):
                    attribute.data[i].vector = (value, 0.0, 0.0)  # Assuming scalar values
            else:
                self.report({'WARNING'}, f"Length of data for column '{name}' does not match the number of vertices. Skipping this column.")
        
        # Optionally use a reference object for positioning
        if self.use_reference_object and self.reference_object:
            try:
                reference_obj = bpy.data.objects[self.reference_object]
                
                # Apply the inverse transformation of the reference object to the particles
                matrix_world_inv = reference_obj.matrix_world.inverted()
                for vert in mesh.vertices:
                    vert.co = matrix_world_inv @ vert.co
            
            except KeyError:
                self.report({'ERROR'}, f"Reference object '{self.reference_object}' not found.")
                return {'CANCELLED'}
        
        # Link the object to the scene and select it
        context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Store the object in the scene's particle_object property
        context.window_manager.particle_object = obj
        
        return {'FINISHED'}
        
    def _setup_geometry_nodes(self, obj):
        # Create new geometry nodes modifier if it doesn't exist
        gn_mod = obj.modifiers.get("ParticleViz")
        if not gn_mod:
            gn_mod = obj.modifiers.new(name="ParticleViz", type='NODES')
            
        # Get or create node group
        node_group = bpy.data.node_groups.get("ParticleVisualization")
        if not node_group:
            node_group = bpy.data.node_groups.new("ParticleVisualization", "GeometryNodeTree")
            
        gn_mod.node_group = node_group
        
        # Clear existing nodes
        node_group.nodes.clear()
        
        # Create nodes
        group_in = node_group.nodes.new('NodeGroupInput')
        group_out = node_group.nodes.new('NodeGroupOutput')
        points = node_group.nodes.new('GeometryNodeMeshToPoints')
        radius_attr = node_group.nodes.new('GeometryNodeInputNamedAttribute')
        
        # Setup interface
        node_group.interface.clear()
        # Add input socket first
        node_group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        # Then add output socket
        node_group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        # Setup nodes
        radius_attr.data_type = 'FLOAT'
        radius_attr.inputs["Name"].default_value = "radius"
        
        # Link nodes (now with proper input socket)
        links = node_group.links
        links.new(group_in.outputs["Geometry"], points.inputs["Mesh"])
        links.new(radius_attr.outputs[0], points.inputs["Radius"])
        links.new(points.outputs[0], group_out.inputs["Geometry"])
        
        # Position nodes
        group_in.location = (-400, 0)
        radius_attr.location = (-400, -100)
        points.location = (0, 0)
        group_out.location = (200, 0)

    def _setup_animation_handler(self, context):
        # Remove any existing handlers first
        handlers = [h for h in bpy.app.handlers.frame_change_post 
                   if h.__name__ == 'update_particle_data']
        for h in handlers:
            bpy.app.handlers.frame_change_post.remove(h)
            
        # Load initial frame without triggering update
        self._current_frame = context.scene.frame_current
        self.update_particle_data(context.scene)
        
        # Now add the handler for future updates
        bpy.app.handlers.frame_change_post.append(self.update_particle_data)

    @staticmethod
    def update_particle_data(scene):
        # Skip if same frame or already updating
        if (LIGGGHTS_OT_import_particles._is_updating or 
            LIGGGHTS_OT_import_particles._current_frame == scene.frame_current):
            return
            
        LIGGGHTS_OT_import_particles._is_updating = True
        LIGGGHTS_OT_import_particles._current_frame = scene.frame_current
        
        try:
            obj = bpy.context.window_manager.particle_object
            dataset = scene.liggghts_dataset
            if not obj or not dataset.filepath_pattern:
                return
                
            # Load frame data
            file_num = dataset.blender_to_file_number(scene.frame_current)
            filepath = dataset.filepath_pattern.replace('*', str(file_num))
            if not os.path.exists(filepath):
                return
                
            data = dataset.parse_frame_data(filepath)
            if not data:
                return
            
            # Check if data is sorted
            if not dataset.is_sorted:
                dataset.is_sorted = dataset.check_if_sorted(data['id'])
                print(f"Data is sorted: {dataset.is_sorted}")
            
            try:
                # Convert to NumPy arrays if not already
                if isinstance(data['id'], list):
                    data['id'] = np.array(data['id'], dtype=np.int32)
                if isinstance(data['positions'], list):
                    data['positions'] = np.array(data['positions'], dtype=np.float32)
                if isinstance(data['radii'], list):
                    data['radii'] = np.array(data['radii'], dtype=np.float32)
                    
                # Sort data by particle ID
                if not dataset.is_sorted:
                    sorted_data = LIGGGHTS_OT_import_particles._sort_particle_data_by_id_numpy(data)
                else:
                    sorted_data = data
                
                # Convert NumPy arrays back to lists for Blender if needed
                if not isinstance(sorted_data['positions'][0], tuple):
                    # Convert from Nx3 array to list of tuples for Blender
                    positions = [tuple(pos) for pos in sorted_data['positions']]
                else:
                    positions = sorted_data['positions']
                    
            except Exception as e:
                print(f"Error processing data with NumPy: {str(e)}")
                # Fall back to original method
                sorted_data = LIGGGHTS_OT_import_particles._sort_particle_data_by_id(data)
                positions = sorted_data['positions']
                
            # Update mesh
            mesh = obj.data
            particle_count = len(sorted_data['id'])
            current_vertex_count = len(mesh.vertices)
            
            # Check if we can update existing vertices or need to recreate
            recreate_mesh = True
            if dataset.use_mesh_update and dataset.last_vertex_count == particle_count:
                recreate_mesh = False
            
            if recreate_mesh:
                # Need to recreate mesh (different particle count)
                mesh.clear_geometry()
                mesh.from_pydata(positions, [], [])
                dataset.last_vertex_count = particle_count
                print(f"Recreated mesh with {particle_count} vertices")
            else:
                # Can update existing vertices (same number of particles)
                # This is much faster than recreating the mesh
                try:
                    mesh.vertices.foreach_set("co", np.array(positions).flatten())
                    print(f"Updated {particle_count} existing vertices")
                except Exception as e:
                    print(f"Error updating vertices: {str(e)}")
                    # Fall back to recreating mesh
                    mesh.clear_geometry()
                    mesh.from_pydata(positions, [], [])
                    print(f"Fell back to recreating mesh with {particle_count} vertices")
            
            # Create or update attributes using NumPy for speed
            LIGGGHTS_OT_import_particles._update_attributes_numpy(mesh, sorted_data)
            
            # Add reference position attributes if needed
            if scene.liggghts_dataset.reference_frame > 0:
                LIGGGHTS_OT_import_particles._add_reference_attributes(mesh, sorted_data['id'], scene.liggghts_dataset)
                
        except Exception as e:
            print(f"Error updating particle data: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            LIGGGHTS_OT_import_particles._is_updating = False
    
    @staticmethod
    def _update_attributes_numpy(mesh, data):
        """Update mesh attributes using NumPy for performance"""
        try:
            # Update particle IDs
            id_attr = mesh.attributes.get("particle_id")
            if not id_attr:
                id_attr = mesh.attributes.new("particle_id", 'INT', 'POINT')
                
            # Convert to NumPy if not already
            if not isinstance(data['id'], np.ndarray):
                ids = np.array(data['id'], dtype=np.int32)
            else:
                ids = data['id']
                
            # Update IDs (use temporary array to match Blender's expected format)
            temp_ids = np.zeros(len(ids), dtype=np.int32)
            for i, id_val in enumerate(ids):
                temp_ids[i] = id_val
                
            id_attr.data.foreach_set("value", temp_ids)
            
            # Update radii
            radius_attr = mesh.attributes.get("radius")
            if not radius_attr:
                radius_attr = mesh.attributes.new("radius", 'FLOAT', 'POINT')
                
            # Convert to NumPy if not already
            if not isinstance(data['radii'], np.ndarray):
                radii = np.array(data['radii'], dtype=np.float32)
            else:
                radii = data['radii']
                
            # Update radii
            radius_attr.data.foreach_set("value", radii)
            
        except Exception as e:
            print(f"Error updating attributes with NumPy: {str(e)}")
            # Fall back to standard method
            for i, id_val in enumerate(data['id']):
                if i < len(mesh.attributes["particle_id"].data):
                    mesh.attributes["particle_id"].data[i].value = id_val
            
            for i, radius in enumerate(data['radii']):
                if i < len(mesh.attributes["radius"].data):
                    mesh.attributes["radius"].data[i].value = radius
    
    @staticmethod
    def _sort_particle_data_by_id_numpy(data):
        """Sort particle data by ID using NumPy for better performance"""
        try:
            # Verify data is valid
            if not isinstance(data['id'], np.ndarray) or len(data['id']) == 0:
                return data
                
            # Get sorted indices
            sorted_indices = np.argsort(data['id'])
            
            # Create sorted data dictionary
            sorted_data = {
                'id': data['id'][sorted_indices],
                'positions': data['positions'][sorted_indices],
                'radii': data['radii'][sorted_indices]
            }
            
            return sorted_data
            
        except Exception as e:
            print(f"NumPy sorting failed: {str(e)}")
            # Fall back to original sort method
            return LIGGGHTS_OT_import_particles._sort_particle_data_by_id(data)

    @staticmethod
    def _add_reference_attributes(mesh, particle_ids, dataset):
        """Add reference position attributes to the mesh vertices"""
        try:
            import bmesh
            
            # Need to ensure we have vertices in the mesh
            if len(mesh.vertices) == 0:
                print("No vertices in mesh - cannot add attributes")
                return
            
            # Get reference dict from dataset
            ref_positions = dataset._ref_positions_dict
            print(f"Number of reference positions available: {len(ref_positions)}")
            
            # Create a bmesh to work with
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            
            # Create new layers in the bmesh
            ref_pos_layer = bm.verts.layers.float_vector.new("reference_position")
            has_ref_layer = bm.verts.layers.float.new("has_reference")
            
            # Count how many matches we find
            match_count = 0
            
            # Fill the bmesh layers with data
            for i, v in enumerate(bm.verts):
                if i >= len(particle_ids):
                    continue
                
                pid = particle_ids[i]
                
                if pid in ref_positions:
                    # Particle has reference data
                    match_count += 1
                    ref_pos = ref_positions[pid]
                    v[ref_pos_layer] = ref_pos
                    v[has_ref_layer] = 1.0
                else:
                    # No reference data - use current position
                    v[ref_pos_layer] = v.co
                    v[has_ref_layer] = 0.0
            
            # Update the mesh with our changes
            bm.to_mesh(mesh)
            bm.free()
            
            # Ensure the mesh updates properly
            mesh.update()
            
            print(f"Added reference positions: {match_count} matches out of {len(mesh.vertices)} particles")
            
        except Exception as e:
            print(f"Error adding reference attributes: {str(e)}")
            import traceback
            traceback.print_exc()
            
    @staticmethod
    def _sort_particle_data_by_id(data):
        """Sort particle data by particle ID"""
        if not data or 'id' not in data or not data['id']:
            return data
        
        try:
            # Verify we have data to sort
            if (len(data['id']) == 0 or 
                len(data['positions']) != len(data['id']) or 
                len(data['radii']) != len(data['id'])):
                print("Warning: Inconsistent data lengths, skipping sort")
                return data
            
            # Create a list of (id, index) pairs and sort by id
            id_index_pairs = [(id_val, i) for i, id_val in enumerate(data['id'])]
            id_index_pairs.sort(key=lambda x: x[0])  # Sort by particle ID
            
            # Create sorted data using the sorted order
            sorted_data = {key: [] for key in data.keys()}
            
            # Rearrange data based on the sorted pairs
            for _, orig_idx in id_index_pairs:
                for key in data.keys():
                    sorted_data[key].append(data[key][orig_idx])
            
            # Log the first few IDs to verify sorting
            print(f"First few sorted IDs: {sorted_data['id'][:10]}")
            
            return sorted_data
        
        except Exception as e:
            print(f"Error during sorting: {str(e)}")
            return data  # Return original data if sorting fails

    @staticmethod
    def cleanup_handler():
        """Remove frame change handlers when addon is disabled"""
        handlers = [h for h in bpy.app.handlers.frame_change_post 
                   if h.__name__ == 'update_particle_data']
        for h in handlers:
            bpy.app.handlers.frame_change_post.remove(h)

class LIGGGHTS_OT_set_reference(bpy.types.Operator):
    bl_idname = "liggghts.set_reference"
    bl_label = "Set Reference Frame"
    
    def execute(self, context):
        scene = context.scene
        dataset = scene.liggghts_dataset
        obj = context.window_manager.particle_object
        
        if not obj or not obj.data.vertices:
            self.report({'ERROR'}, "No particle data available")
            return {'CANCELLED'}
            
        # Get current particle positions and IDs
        positions = [v.co[:] for v in obj.data.vertices]
        
        # Get particle IDs from attribute
        id_attr = obj.data.attributes.get("particle_id")
        if not id_attr:
            self.report({'ERROR'}, "No particle ID data available")
            return {'CANCELLED'}
            
        particle_ids = [id_attr.data[i].value for i in range(len(positions))]
        
        # Store reference data with IDs
        dataset.store_reference_data(positions, particle_ids)
        
        # Store frame number
        dataset.reference_frame = scene.frame_current
        
        self.report({'INFO'}, f"Reference frame set to {scene.frame_current} with {len(positions)} particles")
        return {'FINISHED'}
