import numpy as np
import os
from typing import Dict, List, Tuple, Optional, Any

def parse_liggghts_dump_file_numpy(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Parse LIGGGHTS dump file using NumPy for faster processing
    
    Args:
        filepath: Path to LIGGGHTS dump file
        
    Returns:
        Dictionary with particle data or None if parsing failed
    """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
        
    try:
        # First pass - identify the data section and header structure
        with open(filepath, 'r') as f:
            line_count = 0
            header_line = -1
            data_start_line = -1
            
            for i, line in enumerate(f):
                line = line.strip()
                line_count += 1
                
                if line.startswith("ITEM: ATOMS"):
                    header_line = i
                    data_start_line = i + 1
                    headers = line.split()[2:]
                    break
            
        if data_start_line == -1:
            print(f"No atom data found in file {filepath}")
            return None
            
        # Determine column indices for required data
        header_indices = {}
        for i, header in enumerate(headers):
            header_indices[header] = i
            
        id_idx = header_indices.get('id', 0)
        x_idx = header_indices.get('x', 1)
        y_idx = header_indices.get('y', 2)
        z_idx = header_indices.get('z', 3)
        radius_idx = header_indices.get('radius', 4)
        
        # Load only the data portion of the file using NumPy
        # skiprows=data_start_line skips the header lines
        try:
            # Use NumPy to load data much faster than line-by-line
            data_array = np.loadtxt(
                filepath, 
                skiprows=data_start_line,
                usecols=(id_idx, x_idx, y_idx, z_idx, radius_idx)
            )
            
            # Handle case of single line of data
            if data_array.ndim == 1:
                data_array = data_array.reshape(1, -1)
            
            # Extract columns into appropriate arrays
            ids = data_array[:, 0].astype(np.int32)
            positions = data_array[:, 1:4]  # x, y, z
            radii = data_array[:, 4]
            
            print(f"Parsed {len(ids)} particles from file using NumPy")
            
            return {
                'id': ids,
                'positions': positions,
                'radii': radii
            }
            
        except Exception as e:
            print(f"Error in NumPy loading: {str(e)}")
            print("Falling back to manual parsing method")
            
            # Fallback to manual parsing if NumPy fails
            data = {'id': [], 'positions': [], 'radii': []}
            
            with open(filepath, 'r') as f:
                lines = f.readlines()[data_start_line:]
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        if id_idx < len(parts) and x_idx < len(parts) and y_idx < len(parts) and z_idx < len(parts) and radius_idx < len(parts):
                            data['id'].append(int(parts[id_idx]))
                            data['positions'].append((float(parts[x_idx]), float(parts[y_idx]), float(parts[z_idx])))
                            data['radii'].append(float(parts[radius_idx]))
                
            print(f"Parsed {len(data['positions'])} particles using fallback method")
            return data
            
    except Exception as e:
        print(f"Error parsing frame: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_data(filepath, start_line, max_particles=None):
    data = []
    additional_data = {}
    column_names = []
    
    try:
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
            
            # Parse the rest of the data
            for i, line in enumerate(f):
                if max_particles is not None and i >= max_particles:
                    break
                
                values = line.strip().split()
                
                # Ensure the line has the correct number of columns
                if len(values) != num_columns:
                    print(f"Skipping line {i + start_line + 2} due to incorrect number of columns: {len(values)} instead of {num_columns}")
                    continue
                
                try:
                    x, y, z = map(float, values[:3])
                    data.append((x, y, z))
                    
                    # Store additional data
                    for j, name in enumerate(column_names[3:]):
                        additional_data[name].append(float(values[j + 3]))
                except ValueError:
                    print(f"Skipping line {i + start_line + 2} due to invalid data format.")
                    continue
    
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return [], {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return [], {}
    
    return np.array(data, dtype=np.float32), additional_data
