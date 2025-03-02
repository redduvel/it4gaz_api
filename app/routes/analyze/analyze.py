from flask import Blueprint, jsonify, request
from app.db_client import DBClient
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from statsmodels.tsa.statespace.sarimax import SARIMAX

analyze_bp = Blueprint('analyze', __name__, url_prefix='/api/v1/analyze')

def process_models(data: pd.DataFrame, orders_filename: str, length: int):
    pred = {}
    with open(orders_filename) as f:
        orders = json.load(f)
        print(f"Available orders: {list(orders.keys())}")
        print(f"Data columns: {list(data.columns)}")
        
        # Create a mapping from column name to order parameter name
        column_to_order = {}
        for column in data.columns:
            # Try exact match first
            if column in orders:
                column_to_order[column] = column
            else:
                # Try without table prefix if exact match fails
                column_parts = column.split('_')
                if len(column_parts) >= 3:  # Format like "table_sensorType_index"
                    potential_key = f"{column_parts[-2]}_{column_parts[-1]}"
                    if potential_key in orders:
                        column_to_order[column] = potential_key
        
        print(f"Column to order mapping: {column_to_order}")
        
        for column in data.columns:
            order_key = column_to_order.get(column)
            if order_key:
                print(f"Processing predictions for {column} using order parameters from {order_key}")
                try:
                    model = SARIMAX(endog=data[column], order=orders[order_key]).fit(disp=False)
                    fc_pred = model.get_forecast(length)
                    pred_df = fc_pred.conf_int(alpha = 0.05)
                    pred_df['Prediction'] = model.predict(start = pred_df.index[0], end = pred_df.index[-1])
                    pred_df.index = pd.date_range(data.index[-1] + timedelta(seconds=10), data.index[-1] + timedelta(seconds=length * 10), freq='10s')
                    pred[column] = pred_df["Prediction"]
                    print(f"Successfully generated prediction for {column}")
                except Exception as e:
                    print(f"Error generating prediction for {column}: {str(e)}")
            else:
                print(f"No matching order parameters found for column {column}")
    
    result_df = pd.DataFrame({i: pred[i] for i in data.columns if i in pred})
    print(f"Final prediction columns: {list(result_df.columns)}")
    return result_df

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
    
    # Prediction parameters
    include_predictions = request_data.get('include_predictions', False)
    prediction_length = request_data.get('prediction_length', 10)
    
    # Replace single sensor_type and sensor_index with sensors array
    sensors = filters.get('sensors', [])
    
    time_start = filters.get('time_start')
    time_end = filters.get('time_end')
    
    value_min = filters.get('value_min')
    value_max = filters.get('value_max')
    
    db_client = DBClient()
    supabase = db_client.get_supabase()
    
    if not sensors:
        # 422 Unprocessable Entity - Missing required filter parameters
        return jsonify({
            "message": "At least one sensor must be specified in the sensors array", 
            "status": "error",
            "code": "MISSING_REQUIRED_FILTERS"
        }), 422
    
    # Construct column names based on the sensors array
    column_names = []
    sensor_info = []  # Store original sensor type and index for response
    for sensor_item in sensors:
        # Handle format like {"T": 1} or {"Up": 2}
        for sensor_type, sensor_index in sensor_item.items():
            if sensor_type == 'T':
                column_name = f"T_{sensor_index}"
            else:
                column_name = f"{table_name}_{sensor_type}_{sensor_index}"
            column_names.append(column_name)
            sensor_info.append({
                "column_name": column_name,
                "sensor_type": sensor_type,
                "sensor_index": sensor_index
            })
    
    # Construct the select query with multiple columns
    select_columns = "Time," + ",".join(column_names)
    query = supabase.table(table_name).select(select_columns)
    
    # Apply time filters
    if time_start:
        query = query.gte('Time', time_start)
    
    if time_end:
        query = query.lte('Time', time_end)
    
    # Apply value filters if specified (note: these will apply to all columns)
    if value_min is not None:
        for column_name in column_names:
            query = query.or_(f"{column_name}.gte.{value_min}")
    
    if value_max is not None:
        for column_name in column_names:
            query = query.or_(f"{column_name}.lte.{value_max}")
    
    # We need to get more data for predictions
    # If predictions are requested, we don't use pagination for the raw query
    # but still apply pagination to the returned data
    if include_predictions:
        # Get all matching data for predictions
        response = query.order('Time').execute()
    else:
        # Apply pagination if no predictions are requested
        range_start = (page - 1) * page_size
        range_end = range_start + page_size - 1
        response = query.order('Time', desc=True).range(range_start, range_end).execute()
    
    try:
        # Count query for pagination
        count_query = supabase.table(table_name).select("Time", count='exact')
        
        if time_start:
            count_query = count_query.gte('Time', time_start)
        
        if time_end:
            count_query = count_query.lte('Time', time_end)
        
        count_result = count_query.execute()
        total_count = count_result.count
        
        total_pages = (total_count + page_size - 1) // page_size
        
        # If predictions are requested, generate them
        predictions_by_time = {}
        if include_predictions and response.data:
            print(f"Attempting to generate predictions")
            # Convert to DataFrame for predictions
            df_data = {}
            time_column = []
            
            for row in response.data:
                time_column.append(row["Time"])
                for column_name in column_names:
                    if column_name not in df_data:
                        df_data[column_name] = []
                    if column_name in row:
                        df_data[column_name].append(row[column_name])
                    else:
                        df_data[column_name].append(None)
            
            # Create DataFrame with time as index
            df = pd.DataFrame(df_data)
            print(f"Created DataFrame with columns: {list(df.columns)} and {len(df)} rows")
            df.index = pd.to_datetime(time_column)
            df = df.sort_index()  # Ensure data is sorted by time
            
            # Drop rows with NaN values
            df_before = len(df)
            df = df.dropna()
            df_after = len(df)
            print(f"After dropping NaN values: {df_after} rows (dropped {df_before - df_after} rows)")
            
            if not df.empty:
                # Get predictions using the model
                orders_filename = os.path.join('data', 'orders.json')
                if os.path.exists(orders_filename):
                    print(f"Found orders.json file at {orders_filename}")
                    predictions_df = process_models(df, orders_filename, prediction_length)
                    print(f"Generated predictions with shape: {predictions_df.shape}")
                    
                    # Organize predictions by timestamp
                    for idx, timestamp in enumerate(predictions_df.index):
                        time_str = timestamp.isoformat()
                        if time_str not in predictions_by_time:
                            predictions_by_time[time_str] = []
                        
                        for column in predictions_df.columns:
                            if not pd.isna(predictions_df.iloc[idx][column]):
                                # Find original sensor type and index
                                sensor_info_item = next((item for item in sensor_info if item["column_name"] == column), None)
                                sensor_type = sensor_info_item["sensor_type"] if sensor_info_item else "unknown"
                                sensor_index = sensor_info_item["sensor_index"] if sensor_info_item else 0
                                
                                predictions_by_time[time_str].append({
                                    "sensor": column,
                                    "sensor_type": sensor_type,
                                    "sensor_index": sensor_index,
                                    "value": float(predictions_df.iloc[idx][column])
                                })
                else:
                    print(f"orders.json file not found at {orders_filename}")
            else:
                print("DataFrame is empty after dropping NaN values")
        
        # Apply pagination to the response data for actual values
        paginated_data = response.data
        if include_predictions:
            # If we fetched all data for predictions, we need to apply pagination now
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_data = paginated_data[-end_idx:-start_idx] if start_idx > 0 else paginated_data[-end_idx:]
            paginated_data.reverse()  # Reverse to get descending order by time
        
        # Transform actual data - group by time
        data_by_time = {}
        for row in paginated_data:
            time_value = row["Time"]
            if time_value not in data_by_time:
                data_by_time[time_value] = []
            
            for column_name in column_names:
                if column_name in row:
                    # Find original sensor type and index
                    sensor_info_item = next((item for item in sensor_info if item["column_name"] == column_name), None)
                    sensor_type = sensor_info_item["sensor_type"] if sensor_info_item else "unknown"
                    sensor_index = sensor_info_item["sensor_index"] if sensor_info_item else 0
                    
                    data_by_time[time_value].append({
                        "sensor": column_name,
                        "sensor_type": sensor_type,
                        "sensor_index": sensor_index,
                        "value": row[column_name]
                    })
        
        # Convert to list format, sorted by time in descending order
        transformed_data = [
            {"time": time_value, "readings": readings}
            for time_value, readings in sorted(data_by_time.items(), reverse=True)
        ]
        
        # Convert predictions to list format
        predicted_data = [
            {"time": time_value, "readings": readings}
            for time_value, readings in sorted(predictions_by_time.items(), reverse=True)
        ]
        
        # Prepare response
        response_data = {
            "data": transformed_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages
            },
            "filters": {
                "sensors": sensors,
                "time_start": time_start,
                "time_end": time_end,
                "value_min": value_min,
                "value_max": value_max
            },
            "table": table_name,
            "status": "success"
        }
        
        # Add predictions if available
        if include_predictions:
            print(f"Include predictions is set to: {include_predictions}")
            print(f"Generated {len(predicted_data)} prediction data points")
            
            # Always include predictions array even if empty
            response_data["predictions"] = predicted_data
            response_data["prediction_params"] = {
                "length": prediction_length
            }
            
            if predicted_data:
                print(f"Added {len(predicted_data)} prediction points to response")
            else:
                print("No predictions were generated, but predictions section was added to response")
                
                # Try to provide a hint about what went wrong
                if not os.path.exists(os.path.join('data', 'orders.json')):
                    print("WARNING: orders.json file was not found")
                    response_data["prediction_error"] = "Configuration file not found"
                elif not response.data:
                    print("WARNING: No data returned from database")
                    response_data["prediction_error"] = "No data available for prediction"
                else:
                    # Get column statistics to help debug
                    order_file = os.path.join('data', 'orders.json')
                    if os.path.exists(order_file):
                        with open(order_file, 'r') as f:
                            orders = json.load(f)
                            print(f"Orders file contains keys: {list(orders.keys())}")
                            print(f"Looking for columns: {column_names}")
                            
                            # Check for potential column name issues
                            matched_columns = []
                            for col in column_names:
                                if col in orders:
                                    matched_columns.append(col)
                                else:
                                    # Check for partial matches
                                    parts = col.split('_')
                                    if len(parts) >= 2:
                                        partial = f"{parts[-2]}_{parts[-1]}"
                                        if partial in orders:
                                            matched_columns.append(col)
                            
                            if not matched_columns:
                                response_data["prediction_error"] = "No matching configuration for selected sensors"
                                print(f"WARNING: None of the requested columns match entries in orders.json")
                            else:
                                response_data["prediction_error"] = "Error generating predictions"
                                print(f"WARNING: Found matches but predictions still failed: {matched_columns}")
        else:
            print(f"No predictions added to response. include_predictions={include_predictions}")
        
        return jsonify(response_data)
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
    