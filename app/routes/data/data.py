from flask import Blueprint, jsonify, request
from app.db_client import DBClient
import pandas as pd
import io
import re

data_bp = Blueprint('data', __name__, url_prefix='/api/v1/data')

@data_bp.route('/analyze', methods=['POST'])
def analyze_csv():
    if 'file' not in request.files:
        return jsonify({"message": "No file part", "status": "error"}), 415
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"message": "No selected file", "status": "error"}), 404
    
    if not file.filename.endswith('.csv'):
        return jsonify({"message": "File must be CSV format", "status": "error"}), 422
    
    try:
        separator = request.form.get('separator', ';')
        
        file_content = file.stream.read().decode("UTF-8-SIG")
        stream = io.StringIO(file_content, newline=None)
        
        first_line = stream.readline()
        headers = first_line.split(separator)
        
        clean_headers = []
        for header in headers:
            clean_header = header.split(' ')[0].strip()
            clean_header = ''.join(c for c in clean_header if c.isprintable())
            clean_headers.append(clean_header)
        
        sensor_types = {}
        pipe_numbers = set()
        time_column = None
        
        for header in clean_headers:
            if header.lower() == 'time' or header.lower() == 'timestamp':
                time_column = header
                continue
                
            if header.startswith('T') and '_' in header:
                match = re.match(r'T(\d+)_([A-Za-z]+)_(\d+)', header)
                if match:
                    pipe_num, sensor_type, sensor_num = match.groups()
                    pipe_numbers.add(pipe_num)
                    
                    if sensor_type not in sensor_types:
                        sensor_types[sensor_type] = set()
                    
                    sensor_types[sensor_type].add(sensor_num)
                    
                elif re.match(r'T_\d+', header):
                    if 'Temperature' not in sensor_types:
                        sensor_types['Temperature'] = set()
                    
                    sensor_num = header.split('_')[1]
                    sensor_types['Temperature'].add(sensor_num)
        
        columns = {}
        for header in clean_headers:
            if header == time_column:
                columns[header] = "TIMESTAMP WITH TIME ZONE"
            else:
                columns[header] = "DOUBLE PRECISION"
        
        suggested_table_name = "sensor_data"
        if pipe_numbers:
            pipe_list = sorted([int(p) for p in pipe_numbers])
            if len(pipe_list) == 1:
                suggested_table_name = f"T{pipe_list[0]}_data"
            else:
                suggested_table_name = f"T{pipe_list[0]}_T{pipe_list[-1]}_data"
        
        return jsonify({
            "status": "success",
            "file_name": file.filename,
            "columns": clean_headers,
            "column_count": len(clean_headers),
            "time_column": time_column,
            "sensor_types": {k: list(v) for k, v in sensor_types.items()},
            "pipe_numbers": list(pipe_numbers),
            "suggested_table_name": suggested_table_name,
            "columns_structure": columns
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e), "status": "error"}), 500


@data_bp.route('/create_and_load', methods=['POST'])
def create_and_load():
    if 'file' not in request.files:
        return jsonify({"message": "No file part", "status": "error"}), 415
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"message": "No selected file", "status": "error"}), 404
    
    if not file.filename.endswith('.csv'):
        return jsonify({"message": "File must be CSV format", "status": "error"}), 422
    
    try:
        separator = request.form.get('separator', ';')
        table_name = request.form.get('table_name', 'sensor_data')
        create_table = request.form.get('create_table', 'true').lower() == 'true'
        
        file_content = file.stream.read().decode("UTF-8-SIG")
        stream = io.StringIO(file_content, newline=None)
        
        first_line = stream.readline()
        headers = first_line.split(separator)
        
        clean_headers = []
        for header in headers:
            clean_header = header.split(' ')[0].strip()
            clean_header = ''.join(c for c in clean_header if c.isprintable())
            clean_headers.append(clean_header)
        
        stream.seek(0)
        
        df = pd.read_csv(stream, sep=separator, names=clean_headers, skiprows=1, dtype=str)
        
        time_column = None
        for col in df.columns:
            if col.lower() == 'time' or col.lower() == 'timestamp':
                time_column = col
                break
        
        if not time_column:
            return jsonify({"message": "Time column not found in CSV", "status": "error"}), 400
        
        for column in df.columns:
            if column == time_column:
                df[column] = df[column].str.replace(',', '.')
                try:
                    df[column] = pd.to_datetime(df[column])
                except Exception as e:
                    print(f"Error converting time: {str(e)}")
                continue
                
            try:
                df[column] = df[column].str.replace(',', '.').astype(float)
            except Exception as e:
                print(f"Error converting column {column}: {str(e)}")
        
        db_client = DBClient()
        supabase = db_client.get_supabase()
        
        if create_table:
            columns = {}
            for header in clean_headers:
                if header == time_column:
                    columns[header] = "TIMESTAMP WITH TIME ZONE"
                else:
                    columns[header] = "DOUBLE PRECISION"
            
            try:
                print(f"Creating table {table_name} with structure: {columns}")
                
                result = supabase.rpc(
                    'create_sensor_table',
                    {
                        'table_name': table_name,
                        'columns_json': columns 
                    }
                ).execute()
                
                print(f"Table creation result: {result.data}")
                
                if result.data and isinstance(result.data, str) and result.data.startswith('Error:'):
                    return jsonify({
                        "status": "error",
                        "message": f"Error creating table: {result.data}"
                    }), 500
                
            except Exception as e:
                print(f"Error creating table: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    "status": "error",
                    "message": f"Error creating table: {str(e)}"
                }), 500
        
        records = df.to_dict('records')
        
        for record in records:
            for key, value in record.items():
                if isinstance(value, pd.Timestamp):
                    record[key] = value.isoformat()
        
        try:
            response = supabase.table(table_name).insert(records).execute()
            print(f"Data successfully loaded into table {table_name}")
        except Exception as e:
            print(f"Error inserting data: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Error inserting data: {str(e)}"
            }), 500
        
        sensor_metadata = []
        for column in df.columns:
            if column == time_column:
                continue
                
            sensor_type = "Unknown"
            pipe_number = None
            sensor_number = None
            
            if column.startswith('T_'):
                sensor_type = "Temperature"
                try:
                    sensor_number = int(column.split('_')[1])
                except:
                    sensor_number = None
            
            elif '_' in column:
                match = re.match(r'T(\d+)_([A-Za-z]+)_(\d+)', column)
                if match:
                    try:
                        pipe_number = int(match.group(1))
                        sensor_code = match.group(2)
                        sensor_number = int(match.group(3))
                        
                        if sensor_code == 'K':
                            sensor_type = "Ring deformation"
                        elif sensor_code == 'L':
                            sensor_type = "Left side"
                        elif sensor_code == 'R':
                            sensor_type = "Right side"
                        elif sensor_code == 'Up':
                            sensor_type = "Upper side"
                    except:
                        pass
            
            sensor_metadata.append({
                "sensor_code": column,
                "pipe_number": pipe_number,
                "sensor_type": sensor_type,
                "sensor_number": sensor_number,
                "description": f"{sensor_type} sensor #{sensor_number} on pipe #{pipe_number}" if pipe_number else f"{sensor_type} sensor #{sensor_number}",
                "units": "°C" if sensor_type == "Temperature" else "mm"
            })
        
        try:
            supabase.table("sensor_metadata").upsert(sensor_metadata).execute()
            print(f"Successfully updated sensor metadata")
        except Exception as e:
            print(f"Error updating sensor metadata: {str(e)}")
        
        return jsonify({
            "status": "success",
            "message": f"Data loaded successfully into {table_name}",
            "rows_inserted": len(records),
            "sensors_metadata": len(sensor_metadata)
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e), "status": "error"}), 500


@data_bp.route('/load', methods=['POST'])
def load_data():
    return create_and_load()


