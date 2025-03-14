import bpy
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, CollectionProperty, BoolProperty, IntVectorProperty, FloatProperty
import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from . import optimized_parser

class ReferencePosition(bpy.types.PropertyGroup):
    """Store reference position and ID for displacement calculation"""
    vector: FloatVectorProperty(size=3)
    particle_id: IntProperty(name="Particle ID")  # Store particle ID for each reference position

class ParticleDataset(bpy.types.PropertyGroup):
    """Manages LIGGGHTS particle data and reference frames"""
    filepath_pattern: StringProperty(name="File Pattern")
    start_frame: IntProperty(name="Start Frame", default=1)
    end_frame: IntProperty(name="End Frame", default=1)
    frame_increment: IntProperty(name="Frame Increment", default=1)
    file_start: IntProperty(name="File Start", default=0)
    file_end: IntProperty(name="File End", default=0)
    file_increment: IntProperty(name="File Increment", default=1)
    reference_frame: IntProperty(name="Reference Frame", default=-1)
    reference_positions: CollectionProperty(type=ReferencePosition)
    
    # Option for optimizations
    use_optimized_parser: BoolProperty(
        name="Use Optimized Parser", 
        default=True,
        description="Use NumPy-based parser for faster file loading"
    )
    use_mesh_update: BoolProperty(
        name="Update Mesh", 
        default=True,
        description="Update existing vertices when possible instead of recreating the mesh"
    )
    use_parallel_processing: BoolProperty(
        name="Parallel Processing", 
        default=False,
        description="Use parallel processing to load files in background (experimental)"
    )
    use_data_caching: BoolProperty(
        name="Cache Data", 
        default=True,
        description="Cache recently loaded frames to improve timeline scrubbing performance"
    )
    max_cache_size: IntProperty(
        name="Cache Size", 
        default=5,
        min=1,
        max=20,
        description="Maximum number of frames to keep in memory cache"
    )
    last_vertex_count: IntProperty(default=0)
    
    # Make reference dictionary a class variable to avoid issues with reinitialization
    _ref_positions_dict = {}
    
    is_sorted: BoolProperty(
        name="Data Sorted", 
        default=False, 
        description="Indicates if the particle data is pre-sorted by ID"
    )
    
    def blender_to_file_number(self, frame):
        """Convert Blender frame number to file number"""
        rel_frame = frame - self.start_frame
        return self.file_start + (rel_frame * self.file_increment)

    def file_to_blender_frame(self, file_num):
        """Convert file number to Blender frame number"""
        rel_num = (file_num - self.file_start) // self.file_increment
        return self.start_frame + rel_num
    
    def get_file_path(self, frame):
        """Get file path for a specific Blender frame"""
        file_num = self.blender_to_file_number(frame)
        if not self.filepath_pattern:
            return None
        return self.filepath_pattern.replace('*', str(file_num))

    def parse_frame_data(self, filepath):
        """Parse a single frame file and return particle data"""
        # Set cache size from property
        from . import numpy_loader
        numpy_loader.LIGGGHTSDataLoader._cache_size = self.max_cache_size
        
        # Use optimized parser if enabled
        if self.use_optimized_parser:
            try:
                data = optimized_parser.parse_liggghts_dump_file_numpy(filepath)
                if data is not None:
                    return data
                # If optimized parser fails, fall back to standard parser
                print("Optimized parser failed, falling back to standard parser")
            except ImportError:
                print("Could not import optimized parser, using standard parser")
        
        # Standard parser implementation
        data = {'positions': [], 'radii': [], 'id': []}
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return None
            
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                parsing_atoms = False
                header_indices = {}
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("ITEM: ATOMS"):
                        parsing_atoms = True
                        # Parse header to identify column indices
                        headers = line.split()[2:]
                        for i, header in enumerate(headers):
                            header_indices[header] = i
                        continue
                    
                    if parsing_atoms and line:
                        parts = line.split()
                        if len(parts) >= 5:
                            # Use header indices if available, otherwise fall back to fixed positions
                            id_idx = header_indices.get('id', 0)
                            x_idx = header_indices.get('x', 1) 
                            y_idx = header_indices.get('y', 2)
                            z_idx = header_indices.get('z', 3)
                            radius_idx = header_indices.get('radius', 4)
                            
                            if id_idx < len(parts) and x_idx < len(parts) and y_idx < len(parts) and z_idx < len(parts) and radius_idx < len(parts):
                                data['id'].append(int(parts[id_idx]))
                                data['positions'].append((float(parts[x_idx]), float(parts[y_idx]), float(parts[z_idx])))
                                data['radii'].append(float(parts[radius_idx]))
                            
                print(f"Parsed {len(data['positions'])} particles from file")
        except Exception as e:
            print(f"Error parsing frame: {str(e)}")
            return None
            
        return data
    
    def check_if_sorted(self, ids):
        """Check if a list of IDs is sorted in ascending order."""
        if isinstance(ids, np.ndarray) and len(ids) > 1:
            # NumPy version is much faster for large arrays
            return np.all(ids[:-1] <= ids[1:])
        return all(ids[i] <= ids[i+1] for i in range(len(ids)-1))

    def store_reference_data(self, positions, ids):
        """Store current positions as reference with corresponding particle IDs"""
        self.reference_positions.clear()
        
        # Clear and rebuild our lookup dictionary
        ParticleDataset._ref_positions_dict = {}
        print(f"Storing {len(positions)} reference positions")
        
        # Optimize for large datasets by using NumPy operations
        if isinstance(ids, np.ndarray) and len(ids) > 1000:
            # For large datasets, use a faster approach with NumPy
            positions_array = np.array(positions, dtype=np.float32) if not isinstance(positions, np.ndarray) else positions
            
            # Add to Blender property collection
            for i, (pos, pid) in enumerate(zip(positions_array, ids)):
                item = self.reference_positions.add()
                item.vector = pos if isinstance(pos, tuple) else tuple(pos)
                item.particle_id = int(pid)
                ParticleDataset._ref_positions_dict[int(pid)] = tuple(pos) if not isinstance(pos, tuple) else pos
                
                # Show progress every 10,000 particles
                if i % 10000 == 0 and i > 0:
                    print(f"Stored {i} reference positions...")
        else:
            # Standard method for smaller datasets
            for pos, pid in zip(positions, ids):
                item = self.reference_positions.add()
                item.vector = pos
                item.particle_id = pid
                # Store in dictionary for fast lookups
                ParticleDataset._ref_positions_dict[pid] = pos
        
        print(f"Reference dictionary contains {len(ParticleDataset._ref_positions_dict)} entries")
    
    def get_cache_stats(self):
        """Get statistics on parser cache usage"""
        try:
            stats = optimized_parser.get_cache_stats()
            return stats
        except:
            return {"hits": 0, "misses": 0, "hit_rate": 0.0, "cache_size": 0}
            
    def clear_cache(self):
        """Clear the file parsing cache"""
        try:
            optimized_parser.clear_cache()
            return True
        except:
            return False
