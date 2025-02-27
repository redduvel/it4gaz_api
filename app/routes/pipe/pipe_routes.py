from flask import jsonify, request, send_from_directory
from app.routes.pipe import pipe_bp
import numpy as np
import json
import os

def get_test_sensor_data():
    """Get test sensor data for pipe deformation and temperature"""
    # Test data from CSV (space-separated)
    test_data_str = """Time	T3_L_3 (s/n=, CH6, value)	T3_L_2 (s/n=, CH6, value)	T3_L_1 (s/n=, CH6, value)	T3_R_1 (s/n=, CH6, value)	T3_R_2 (s/n=, CH6, value)	T3_R_3 (s/n=, CH6, value)	T3_Up_1 (s/n=, CH7, value)	T3_Up_2 (s/n=, CH7, value)	T3_Up_3 (s/n=, CH7, value)	T3_K_1 (s/n=, CH7, value)	T3_K_2 (s/n=, CH7, value)	T2_K_3 (s/n=, CH7, value)	T_3 (s/n=, CH7, value)
2024-01-01T00:06:09,555	720,4790652	336,9241863	279,4417719	274,4453808	291,1124319	740,2059905	-146,6366455	-249,9021305	-170,2594846	638,4761851	472,8626131	542,7257687	14,06850088"""
    
    # Parse the test data
    lines = test_data_str.strip().split('\n')
    headers = lines[0].split('\t')
    values = lines[1].split('\t')
    
    # Convert comma-separated decimal values to dots
    for i in range(1, len(values)):
        values[i] = float(values[i].replace(',', '.'))
    
    # Create sensor data structure
    sensor_data = []
    
    # Define positions for sensors along the 12-meter pipe
    # Sensors are placed at equal distances, with 1-meter offset from each end
    pipe_length = 12.0  # meters
    num_sensor_groups = 3
    
    # Calculate positions for sensor groups (1m from each end, equal spacing)
    positions = []
    for i in range(num_sensor_groups):
        # Position normalized to 0-1 range
        position = (1.0 + i * ((pipe_length - 2.0) / (num_sensor_groups - 1))) / pipe_length
        positions.append(position)
    
    # Temperature sensor (in the middle of the pipe)
    temp_value = values[13]  # T_3 value
    sensor_data.append({
        "sensor_id": "T_3",
        "type": "temperature",
        "position": 0.5,  # Middle of the pipe
        "value": temp_value,
        "location": "center"
    })
    
    # Add Left side sensors (L_1, L_2, L_3)
    for i in range(num_sensor_groups):
        sensor_data.append({
            "sensor_id": f"T3_L_{i+1}",
            "type": "deformation",
            "position": positions[i],
            "value": values[3-i],  # T3_L_3, T3_L_2, T3_L_1 (reversed in the data)
            "location": "left"
        })
    
    # Add Right side sensors (R_1, R_2, R_3)
    for i in range(num_sensor_groups):
        sensor_data.append({
            "sensor_id": f"T3_R_{i+1}",
            "type": "deformation",
            "position": positions[i],
            "value": values[4+i],  # T3_R_1, T3_R_2, T3_R_3
            "location": "right"
        })
    
    # Add Upper side sensors (Up_1, Up_2, Up_3)
    for i in range(num_sensor_groups):
        sensor_data.append({
            "sensor_id": f"T3_Up_{i+1}",
            "type": "deformation",
            "position": positions[i],
            "value": values[7+i],  # T3_Up_1, T3_Up_2, T3_Up_3
            "location": "upper"
        })
    
    # Add Circular deformation sensors (K_1, K_2, K_3)
    # These are at one end of the pipe
    for i in range(num_sensor_groups):
        sensor_data.append({
            "sensor_id": f"T3_K_{i+1}" if i < 2 else f"T2_K_3",
            "type": "deformation",
            "position": positions[0],  # All at the first position (1m from start)
            "value": values[10+i],  # T3_K_1, T3_K_2, T2_K_3
            "location": "circular"
        })
    
    # Normalize deformation values for better visualization
    # Find max absolute value for normalization
    max_deform = max([abs(s["value"]) for s in sensor_data if s["type"] == "deformation"])
    
    # Normalize deformation values to a reasonable range (-0.5 to 0.5)
    for sensor in sensor_data:
        if sensor["type"] == "deformation":
            sensor["value"] = (sensor["value"] / max_deform) * 0.5
    
    # Normalize temperature to the 20-80 range
    for sensor in sensor_data:
        if sensor["type"] == "temperature":
            # Assuming temperature is in Celsius and reasonable
            # If not, we can adjust the scaling
            sensor["value"] = max(20, min(80, sensor["value"]))
    
    return sensor_data

def generate_mock_sensor_data(num_sensors=10):
    """Generate mock sensor data for pipe deformation and temperature"""
    # For testing purposes, we'll use the test data instead of random values
    return get_test_sensor_data()

@pipe_bp.route('/', methods=['GET'])
def pipe_visualization():
    """Serve the pipe visualization HTML page"""
    return send_from_directory('static', 'index.html')

@pipe_bp.route('/sensor-data', methods=['GET'])
def get_sensor_data():
    """Get sensor data for pipe deformation"""
    sensor_data = get_test_sensor_data()
    return jsonify({"sensor_data": sensor_data})

@pipe_bp.route('/pipe-model', methods=['GET'])
def get_pipe_model():
    """Get 3D pipe model data based on sensor readings"""
    segments = request.args.get('segments', default=32, type=int)
    
    # Get sensor data
    sensor_data = get_test_sensor_data()
    
    # Generate pipe model
    pipe_model = generate_pipe_model(sensor_data, segments)
    
    return jsonify({"pipe_model": pipe_model})

def generate_pipe_model(sensor_data, segments=32):
    """
    Generate a 3D pipe model based on sensor data
    
    Args:
        sensor_data: List of sensor readings with position and deformation values
        segments: Number of segments around the pipe circumference
    
    Returns:
        Dictionary with vertices, faces, and colors for the 3D model
    """
    # Group sensors by position
    positions = set()
    for sensor in sensor_data:
        positions.add(sensor["position"])
    
    # Add more positions for smoother pipe
    num_extra_points = 20  # Number of extra points to add between sensor positions
    
    # Get min and max positions
    min_pos = min(positions)
    max_pos = max(positions)
    
    # Add extra positions for smoother pipe
    for i in range(num_extra_points):
        pos = min_pos + (max_pos - min_pos) * i / (num_extra_points - 1)
        positions.add(pos)
    
    # Sort positions
    positions = sorted(list(positions))
    num_points = len(positions)
    
    # Create a dictionary to store sensors by position
    sensors_by_position = {}
    for position in positions:
        sensors_by_position[position] = []
    
    for sensor in sensor_data:
        sensors_by_position[sensor["position"]].append(sensor)
    
    # Create vertices and colors for the pipe
    vertices = []
    colors = []  # RGB color values for each vertex
    
    # Create the pipe segments
    for i, position in enumerate(positions):
        position_sensors = sensors_by_position[position]
        
        # If no sensors at this position, interpolate from nearest positions
        if not position_sensors:
            # Find nearest positions with sensors
            positions_with_sensors = [p for p in positions if sensors_by_position[p]]
            
            # Find nearest positions before and after current position
            prev_pos = max([p for p in positions_with_sensors if p < position], default=None)
            next_pos = min([p for p in positions_with_sensors if p > position], default=None)
            
            # If we have both prev and next, interpolate
            if prev_pos is not None and next_pos is not None:
                prev_sensors = sensors_by_position[prev_pos]
                next_sensors = sensors_by_position[next_pos]
                
                # Interpolation factor
                factor = (position - prev_pos) / (next_pos - prev_pos)
                
                # Interpolate sensors
                for prev_sensor in prev_sensors:
                    # Find matching sensor in next position
                    next_sensor = next((s for s in next_sensors if s["sensor_id"] == prev_sensor["sensor_id"]), None)
                    
                    if next_sensor:
                        # Create interpolated sensor
                        interp_sensor = {
                            "sensor_id": prev_sensor["sensor_id"],
                            "type": prev_sensor["type"],
                            "position": position,
                            "value": prev_sensor["value"] + factor * (next_sensor["value"] - prev_sensor["value"]),
                            "location": prev_sensor["location"]
                        }
                        position_sensors.append(interp_sensor)
        
        # Get temperature value for this position (for coloring)
        temp_sensor = next((s for s in position_sensors if s["type"] == "temperature"), None)
        
        # If no temperature sensor at this position, use default or interpolate
        if not temp_sensor:
            # Find all temperature sensors
            temp_sensors = [s for s in sensor_data if s["type"] == "temperature"]
            if temp_sensors:
                # Use the temperature from the middle of the pipe
                temp_sensor = temp_sensors[0]
        
        temperature = temp_sensor["value"] if temp_sensor else 50  # Default temperature
        
        # Map temperature to color (blue to red gradient)
        # 20°C -> Blue (0, 0, 1)
        # 80°C -> Red (1, 0, 0)
        temp_normalized = (temperature - 20) / 60  # Normalize to 0-1 range
        r = temp_normalized
        g = 0
        b = 1 - temp_normalized
        
        # Get deformation sensors for this position
        deform_sensors = [s for s in position_sensors if s["type"] == "deformation"]
        
        # Create a dictionary to store deformation by location
        deform_by_location = {
            "circular": 0,
            "left": 0,
            "right": 0,
            "upper": 0
        }
        
        # Fill in deformation values
        for sensor in deform_sensors:
            if sensor["location"] in deform_by_location:
                deform_by_location[sensor["location"]] = sensor["value"]
        
        # Base radius of the pipe
        base_radius = 1.0
        
        # Create a ring of vertices around the pipe at this position
        for j in range(segments):
            angle = 2 * np.pi * j / segments
            
            # Determine which deformation to use based on angle
            deform_value = 0
            
            # Upper side (top of pipe)
            if angle < np.pi/4 or angle > 7*np.pi/4:
                deform_value = deform_by_location["upper"]
            # Right side
            elif angle < 3*np.pi/4:
                deform_value = deform_by_location["right"]
            # Bottom (use circular)
            elif angle < 5*np.pi/4:
                deform_value = deform_by_location["circular"]
            # Left side
            else:
                deform_value = deform_by_location["left"]
            
            # Calculate deformation effect
            deform_factor = np.cos(angle) * deform_value
            
            # Calculate the radius with deformation
            radius = base_radius + deform_factor
            
            # Calculate vertex position
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = position * 12  # Scale to 12 meters pipe length
            
            vertices.append([x, y, z])
            colors.append([r, g, b])  # Add color based on temperature
    
    # Create faces (triangles) for the pipe
    faces = []
    
    # Connect vertices to form triangles
    for i in range(num_points - 1):
        for j in range(segments):
            # Get indices of the four corners of a quad
            i0 = i * segments + j
            i1 = i * segments + (j + 1) % segments
            i2 = (i + 1) * segments + (j + 1) % segments
            i3 = (i + 1) * segments + j
            
            # Create two triangles for each quad
            faces.append([i0, i1, i2])
            faces.append([i0, i2, i3])
    
    return {
        "vertices": vertices,
        "faces": faces,
        "colors": colors
    } 