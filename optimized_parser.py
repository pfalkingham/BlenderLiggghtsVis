import numpy as np
import os
from typing import Dict, List, Tuple, Optional, Any
from . import numpy_loader

def parse_liggghts_dump_file_numpy(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Parse LIGGGHTS dump file using NumPy for faster processing
    
    Args:
        filepath: Path to LIGGGHTS dump file
        
    Returns:
        Dictionary with particle data or None if parsing failed
    """
    return numpy_loader.parse_liggghts_file(filepath)

def parse_data(filepath, start_line, max_particles=None):
    """
    Parse custom data file with positions and additional columns
    
    Args:
        filepath: Path to data file
        start_line: Line to start reading data from
        max_particles: Maximum number of particles to read (None for all)
        
    Returns:
        Tuple of (positions array, additional data dictionary)
    """
    return numpy_loader.parse_custom_data_file(filepath, start_line, max_particles)

def get_cache_stats():
    """Return information about the data loader cache performance"""
    return numpy_loader.LIGGGHTSDataLoader.get_cache_stats()

def clear_cache():
    """Clear the data loader cache to free memory"""
    numpy_loader.LIGGGHTSDataLoader.clear_cache()
