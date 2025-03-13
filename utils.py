import re
import os
from typing import Dict, List, Tuple, Optional, Any

def extract_frame_number_pattern(filename: str) -> Optional[Dict[str, Any]]:
    """Extract frame number and create pattern parts from filename"""
    pattern = r'(.*?)(\d+)(.*)'
    match = re.match(pattern, filename)
    if not match:
        return None
    
    prefix, number, suffix = match.groups()
    return {
        'prefix': prefix,
        'number': int(number),
        'suffix': suffix,
        'pattern': f"{prefix}*{suffix}"
    }

def find_matching_files(directory: str, pattern: str) -> List[Tuple[int, str]]:
    """Find all files matching pattern and extract frame numbers"""
    if not os.path.exists(directory):
        return []
        
    prefix, suffix = pattern.split('*')
    number_pattern = re.compile(f"^{re.escape(prefix)}(\d+){re.escape(suffix)}$")
    
    matching_files = []
    try:
        for f in os.listdir(directory):
            match = number_pattern.match(f)
            if match:
                frame_num = int(match.group(1))
                matching_files.append((frame_num, f))
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error accessing directory: {str(e)}")
    
    return sorted(matching_files)
