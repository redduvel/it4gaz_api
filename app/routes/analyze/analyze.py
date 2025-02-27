from flask import Blueprint, jsonify, request
from app.db_client import DBClient

analyze_bp = Blueprint('analyze', __name__, url_prefix='/api/v1/analyze')

@analyze_bp.route('/sensor/<table_name>', methods=['POST'])
def get_sensor_data(table_name):
    request_data = request.get_json()
    
    if not request_data:
        # 400 Bad Request - Missing request body
        return jsonify({"message": "Request body is required", "status": "error", "code": "MISSING_REQUEST_BODY"}), 400
    
    if not table_name:
        # 404 Not Found - Missing resource identifier
        return jsonify({"message": "Table name is required", "status": "error", "code": "MISSING_TABLE_NAME"}), 404
    
    filters = request_data.get('filters', {})
    
    page = request_data.get('page', 1)
    page_size = request_data.get('page_size', 20)
    
    sensor_type = filters.get('sensor_type')
    
    sensor_index = filters.get('sensor_index')
    
    time_start = filters.get('time_start')
    time_end = filters.get('time_end')
    
    value_min = filters.get('value_min')
    value_max = filters.get('value_max')
    
    db_client = DBClient()
    supabase = db_client.get_supabase()
    
    if not sensor_type or not sensor_index:
        # 422 Unprocessable Entity - Missing required filter parameters
        return jsonify({
            "message": "Both sensor_type and sensor_index are required", 
            "status": "error",
            "code": "MISSING_REQUIRED_FILTERS"
        }), 422
    
    if sensor_type == 'T':
        column_name = f"T_{sensor_index}"
    else:
        column_name = f"{table_name}_{sensor_type}_{sensor_index}"
    
    query = supabase.table(table_name).select(f"Time,{column_name}")

    if value_min is not None:
        query = query.gte(column_name, value_min)
    
    if value_max is not None:
        query = query.lte(column_name, value_max)
    
    if time_start:
        query = query.gte('Time', time_start)
    
    if time_end:
        query = query.lte('Time', time_end)
    
    range_start = (page - 1) * page_size
    range_end = range_start + page_size - 1
    
    try:
        response = query.order('Time', desc=True).range(range_start, range_end).execute()
        
        count_query = supabase.table(table_name).select(column_name, count='exact')
        
        if value_min is not None:
            count_query = count_query.gte(column_name, value_min)
        
        if value_max is not None:
            count_query = count_query.lte(column_name, value_max)
        
        if time_start:
            count_query = count_query.gte('Time', time_start)
        
        if time_end:
            count_query = count_query.lte('Time', time_end)
        
        count_result = count_query.execute()
        total_count = count_result.count
        
        total_pages = (total_count + page_size - 1) // page_size
        
        transformed_data = []
        for row in response.data:
            transformed_data.append({
                "time": row["Time"],
                "value": row[column_name],
                "sensor": column_name
            })
        
        # Prepare response
        return jsonify({
            "data": transformed_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages
            },
            "filters": {
                "sensor_type": sensor_type,
                "sensor_index": sensor_index,
                "time_start": time_start,
                "time_end": time_end,
                "value_min": value_min,
                "value_max": value_max
            },
            "table": table_name,
            "status": "success"
        })
    except Exception as e:
        error_message = str(e)
        error_code = "INTERNAL_SERVER_ERROR"
        status_code = 500
        
        if "does not exist" in error_message:
            error_code = "RESOURCE_NOT_FOUND"
            status_code = 404
        elif "permission denied" in error_message.lower():
            error_code = "PERMISSION_DENIED"
            status_code = 403
        elif "syntax error" in error_message.lower() or "invalid input syntax" in error_message.lower():
            error_code = "INVALID_QUERY_SYNTAX"
            status_code = 400
        elif "value out of range" in error_message.lower():
            error_code = "VALUE_OUT_OF_RANGE"
            status_code = 422
        
        return jsonify({
            "message": f"Error retrieving sensor data from table '{table_name}': {error_message}",
            "status": "error",
            "code": error_code
        }), status_code
    