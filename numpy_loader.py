import numpy as np
import os
from typing import Dict, List, Tuple, Optional, Any
import time

class LIGGGHTSDataLoader:
    """
    A high-performance loader for LIGGGHTS particle data using NumPy
    with additional features for caching and memory optimization.
    """
    
    # Cache for recently loaded files to avoid re-parsing
    _file_cache = {}
    _cache_size = 5  # Maximum number of frames to keep in cache
    _cache_hits = 0
    _cache_misses = 0
    
    @classmethod
    def clear_cache(cls):
        """Clear the file cache to free memory"""
        cls._file_cache = {}
        cls._cache_hits = 0
        cls._cache_misses = 0
        
    @classmethod
    def get_cache_stats(cls):
        """Return cache performance statistics"""
        total = cls._cache_hits + cls._cache_misses
        hit_rate = cls._cache_hits / total if total > 0 else 0
        return {
            'hits': cls._cache_hits,
            'misses': cls._cache_misses,
            'hit_rate': hit_rate,
            'cache_size': len(cls._file_cache)
        }
    
    @staticmethod
    def parse_dump_file(filepath: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Parse LIGGGHTS dump file using optimized NumPy methods
        
        Args:
            filepath: Path to LIGGGHTS dump file
            use_cache: Whether to use file caching (default: True)
            
        Returns:
            Dictionary with particle data or None if parsing failed
        """
        # Check cache first
        if use_cache and filepath in LIGGGHTSDataLoader._file_cache:
            LIGGGHTSDataLoader._cache_hits += 1
            return LIGGGHTSDataLoader._file_cache[filepath]
            
        if use_cache:
            LIGGGHTSDataLoader._cache_misses += 1
            
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return None
        
        start_time = time.time()
        
        try:
            # First pass - identify the data section and header structure
            with open(filepath, 'r') as f:
                # Read file in chunks for better performance with large files
                line_count = 0
                header_line = -1
                data_start_line = -1
                headers = []
                
                for i, line in enumerate(f):
                    line = line.strip()
                    
                    if line.startswith("ITEM: ATOMS"):
                        header_line = i
                        data_start_line = i + 1
                        headers = line.split()[2:]
                        break
                
            if data_start_line == -1:
                print(f"No atom data found in file {filepath}")
                return None
                
            # Determine column indices for required data
            header_indices = {header: i for i, header in enumerate(headers)}
            
            id_idx = header_indices.get('id', 0)
            x_idx = header_indices.get('x', 1)
            y_idx = header_indices.get('y', 2)
            z_idx = header_indices.get('z', 3)
            radius_idx = header_indices.get('radius', 4)
            
            # Additional data columns that might be present
            fx_idx = header_indices.get('fx', -1)
            fy_idx = header_indices.get('fy', -1)
            fz_idx = header_indices.get('fz', -1)
            
            # Determine which columns to load
            usecols = [id_idx, x_idx, y_idx, z_idx, radius_idx]
            # Add force columns if they exist
            force_cols = []
            if fx_idx >= 0: 
                usecols.append(fx_idx)
                force_cols.append(fx_idx)
            if fy_idx >= 0:
                usecols.append(fy_idx)
                force_cols.append(fy_idx)
            if fz_idx >= 0:
                usecols.append(fz_idx)
                force_cols.append(fz_idx)
                
            try:
                # Use NumPy's efficient data loading
                data_array = np.loadtxt(
                    filepath, 
                    skiprows=data_start_line,
                    usecols=tuple(usecols)
                )
                
                # Handle case of single line of data
                if data_array.ndim == 1:
                    data_array = data_array.reshape(1, -1)
                
                # Extract columns into appropriate arrays
                ids = data_array[:, 0].astype(np.int32)
                positions = data_array[:, 1:4]  # x, y, z
                radii = data_array[:, 4]
                
                # Build result dictionary
                result = {
                    'id': ids,
                    'positions': positions,
                    'radii': radii
                }
                
                # Add forces if available
                if force_cols:
                    forces = []
                    force_col_count = len(force_cols)
                    if force_col_count == 3:
                        # All three force components available
                        force_indices = [5, 6, 7] if len(usecols) >= 8 else []
                        if force_indices:
                            forces = data_array[:, force_indices]
                            result['forces'] = forces
                
                # Store in cache if caching is enabled
                if use_cache:
                    # Maintain cache size limit using simple FIFO eviction
                    if len(LIGGGHTSDataLoader._file_cache) >= LIGGGHTSDataLoader._cache_size:
                        # Remove oldest item
                        oldest_key = next(iter(LIGGGHTSDataLoader._file_cache))
                        LIGGGHTSDataLoader._file_cache.pop(oldest_key)
                    
                    LIGGGHTSDataLoader._file_cache[filepath] = result
                
                end_time = time.time()
                print(f"Parsed {len(ids)} particles in {end_time - start_time:.3f}s using NumPy")
                
                return result
                
            except Exception as e:
                print(f"Error in NumPy loading: {str(e)}")
                print("Falling back to standard parser")
                
                # Fallback to manual parsing if NumPy fails
                return LIGGGHTSDataLoader._fallback_parse(filepath, data_start_line, header_indices)
                
        except Exception as e:
            print(f"Error parsing frame: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _fallback_parse(filepath: str, data_start_line: int, header_indices: Dict[str, int]) -> Optional[Dict[str, Any]]:
        """Fallback parser using standard Python for cases where NumPy fails"""
        data = {'positions': [], 'radii': [], 'id': [], 'forces': []}
        has_forces = all(k in header_indices for k in ['fx', 'fy', 'fz'])
        
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()[data_start_line:]
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        id_idx = header_indices.get('id', 0)
                        x_idx = header_indices.get('x', 1) 
                        y_idx = header_indices.get('y', 2)
                        z_idx = header_indices.get('z', 3)
                        radius_idx = header_indices.get('radius', 4)
                        
                        if id_idx < len(parts) and x_idx < len(parts) and y_idx < len(parts) and z_idx < len(parts) and radius_idx < len(parts):
                            data['id'].append(int(parts[id_idx]))
                            data['positions'].append((float(parts[x_idx]), float(parts[y_idx]), float(parts[z_idx])))
                            data['radii'].append(float(parts[radius_idx]))
                            
                            if has_forces:
                                fx_idx = header_indices.get('fx')
                                fy_idx = header_indices.get('fy')
                                fz_idx = header_indices.get('fz')
                                if all(idx < len(parts) for idx in [fx_idx, fy_idx, fz_idx]):
                                    data['forces'].append((float(parts[fx_idx]), float(parts[fy_idx]), float(parts[fz_idx])))
                
            # If no forces were found, remove the empty forces list
            if not data['forces']:
                del data['forces']
                
            # Convert to numpy arrays
            data['id'] = np.array(data['id'], dtype=np.int32)
            data['positions'] = np.array(data['positions'], dtype=np.float32)
            data['radii'] = np.array(data['radii'], dtype=np.float32)
            if 'forces' in data:
                data['forces'] = np.array(data['forces'], dtype=np.float32)
                
            print(f"Parsed {len(data['positions'])} particles using fallback method")
            return data
            
        except Exception as e:
            print(f"Fallback parser failed: {str(e)}")
            return None
            
    @staticmethod
    def parse_custom_format(filepath: str, start_line: int = 0, max_particles: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """
        Parse custom format data files with improved performance
        
        Args:
            filepath: Path to data file
            start_line: Line number to start reading at
            max_particles: Maximum number of particles to load (None for all)
            
        Returns:
            Tuple of (positions_array, additional_data_dict)
        """
        try:
            # Determine file size for progress reporting
            file_size = os.path.getsize(filepath)
            if file_size > 10*1024*1024:  # 10MB
                print(f"Loading large file ({file_size/1024/1024:.1f}MB), this may take a moment...")
            
            # For very large files, use a more efficient approach
            if file_size > 100*1024*1024 and max_particles is None:  # 100MB
                return LIGGGHTSDataLoader._parse_large_file(filepath, start_line)
                
            # Regular parsing for normal-sized files
            positions = []
            additional_data = {}
            column_names = []
            
            with open(filepath, 'r') as f:
                # Skip header lines
                for _ in range(start_line):
                    next(f)
                
                # Read the first line to determine the number of columns
                first_line = f.readline().strip().split()
                num_columns = len(first_line)
                
                # Determine column names based on the number of columns
                if num_columns >= 3:
                    column_names = ['x', 'y', 'z'] + [f'col_{i}' for i in range(3, num_columns)]
                else:
                    raise ValueError("At least x, y, z columns are required.")
                
                # Initialize lists for additional data
                for name in column_names[3:]:
                    additional_data[name] = []
                
                # Pre-allocate lists if we know the particle count
                if max_particles is not None:
                    positions = [(0.0, 0.0, 0.0)] * min(max_particles, 10000)
                    for name in column_names[3:]:
                        additional_data[name] = [0.0] * min(max_particles, 10000)
                
                # Parse first line
                try:
                    x, y, z = map(float, first_line[:3])
                    if len(positions) <= 0:
                        positions.append((x, y, z))
                    else:
                        positions[0] = (x, y, z)
                    
                    # Store additional data
                    for j, name in enumerate(column_names[3:]):
                        if j + 3 < len(first_line):
                            if len(additional_data[name]) <= 0:
                                additional_data[name].append(float(first_line[j + 3]))
                            else:
                                additional_data[name][0] = float(first_line[j + 3])
                except ValueError:
                    print("Skipping first line due to invalid data format.")
                
                # Parse the rest of the data
                for i, line in enumerate(f, start=1):
                    if max_particles is not None and i >= max_particles:
                        break
                    
                    values = line.strip().split()
                    
                    # Ensure the line has the correct number of columns
                    if len(values) != num_columns:
                        print(f"Skipping line {i + start_line + 1} due to incorrect number of columns: {len(values)} instead of {num_columns}")
                        continue
                    
                    try:
                        x, y, z = map(float, values[:3])
                        if i < len(positions):
                            positions[i] = (x, y, z)
                        else:
                            positions.append((x, y, z))
                        
                        # Store additional data
                        for j, name in enumerate(column_names[3:]):
                            if j + 3 < len(values):
                                if i < len(additional_data[name]):
                                    additional_data[name][i] = float(values[j + 3])
                                else:
                                    additional_data[name].append(float(values[j + 3]))
                    except ValueError:
                        print(f"Skipping line {i + start_line + 1} due to invalid data format.")
                        continue
            
            # Trim pre-allocated arrays if needed
            if max_particles is not None:
                actual_count = len(positions)
                positions = positions[:actual_count]
                for name in additional_data:
                    additional_data[name] = additional_data[name][:actual_count]
            
            # Convert to NumPy arrays for better performance
            return np.array(positions, dtype=np.float32), additional_data
        
        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
            return np.array([], dtype=np.float32), {}
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
            return np.array([], dtype=np.float32), {}
    
    @staticmethod
    def _parse_large_file(filepath: str, start_line: int) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """Specialized parser for very large files using memory mapping"""
        import mmap
        import contextlib
        
        positions = []
        additional_data = {}
        column_count = 0
        
        try:
            with open(filepath, 'r') as f:
                # Skip header
                for _ in range(start_line):
                    f.readline()
                
                # Sample first line to determine structure
                first_line = f.readline().strip().split()
                column_count = len(first_line)
                
                if column_count < 3:
                    raise ValueError("File must have at least 3 columns (x,y,z)")
                    
                column_names = ['x', 'y', 'z'] + [f'col_{i}' for i in range(3, column_count)]
                for name in column_names[3:]:
                    additional_data[name] = []
            
            # Now process using memory mapping for better performance
            with open(filepath, 'r') as f:
                with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
                    # Skip header lines
                    current_pos = 0
                    for _ in range(start_line + 1):  # +1 since we've read one line already
                        next_pos = m.find(b'\n', current_pos) + 1
                        if next_pos == 0:  # Not found
                            return np.array([], dtype=np.float32), {}
                        current_pos = next_pos
                    
                    # Read chunks to avoid loading entire file into memory at once
                    while current_pos < m.size():
                        # Read a chunk (~10MB at a time)
                        chunk_end = min(current_pos + 10*1024*1024, m.size())
                        next_newline = m.find(b'\n', chunk_end)
                        if next_newline == -1:
                            chunk_end = m.size()
                        else:
                            chunk_end = next_newline + 1
                            
                        # Process chunk line by line
                        chunk = m[current_pos:chunk_end].decode('utf-8')
                        lines = chunk.splitlines()
                        
                        for line in lines:
                            if not line.strip():
                                continue
                                
                            values = line.split()
                            if len(values) >= 3:
                                try:
                                    x, y, z = map(float, values[:3])
                                    positions.append((x, y, z))
                                    
                                    # Additional data
                                    for j, name in enumerate(column_names[3:]):
                                        if j + 3 < len(values):
                                            additional_data[name].append(float(values[j + 3]))
                                        else:
                                            additional_data[name].append(0.0)
                                except ValueError:
                                    continue
                        
                        # Move to next chunk
                        current_pos = chunk_end
                        if len(positions) % 100000 == 0:
                            print(f"Loaded {len(positions)} particles...")
            
            # Convert to numpy array
            return np.array(positions, dtype=np.float32), additional_data
            
        except Exception as e:
            print(f"Error in large file parser: {str(e)}")
            import traceback
            traceback.print_exc()
            return np.array(positions, dtype=np.float32), additional_data

# Simplified export function for direct use
def parse_liggghts_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Simplified function for parsing LIGGGHTS files"""
    return LIGGGHTSDataLoader.parse_dump_file(filepath)

def parse_custom_data_file(filepath: str, start_line: int = 0, max_particles: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, List[float]]]:
    """Simplified function for parsing custom data files"""
    return LIGGGHTSDataLoader.parse_custom_format(filepath, start_line, max_particles)