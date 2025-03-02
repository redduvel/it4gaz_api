from flask import Blueprint, jsonify, request, render_template, send_from_directory
import pandas as pd
import numpy as np
import os
import json
from app.db_client import DBClient
import logging
import locale

# Создаем blueprint для визуализации
visualization_bp = Blueprint('visualization', __name__, url_prefix='/api/v1/visualization',
                            template_folder='templates', static_folder='static')

# Функция для чтения данных из CSV
def read_sensor_data_from_csv(csv_path, time_start=None, time_end=None):
    try:
        # Загрузка CSV с данными датчиков
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        # Очистка имен столбцов от лишней информации
        df.columns = [col.split(' ')[0] for col in df.columns]
        
        # Преобразуем столбец времени в datetime с явным указанием формата
        # Здесь предполагаем, что формат даты - ISO (2024-01-01T00:06:09,555)
        # Заменяем запятую на точку в значениях времени для правильного парсинга
        df['Time'] = df['Time'].str.replace(',', '.')
        df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%dT%H:%M:%S.%f')
        
        # Применяем фильтры по времени, если указаны
        if time_start:
            time_start = pd.to_datetime(time_start)
            df = df[df['Time'] >= time_start]
        
        if time_end:
            time_end = pd.to_datetime(time_end)
            df = df[df['Time'] <= time_end]
        
        # Преобразуем числовые столбцы, заменяя запятые на точки
        for column in df.columns:
            if column != 'Time':
                # Заменяем запятые на точки и преобразуем в числовой формат
                df[column] = df[column].astype(str).str.replace(',', '.').astype(float)
        
        return df
    
    except Exception as e:
        logging.error(f"Error reading sensor data: {str(e)}")
        raise

# Функция для создания 3D модели трубы
def generate_pipe_model(sensor_data, length=10.0, radius=1.0, wall_thickness=0.1, segments=32, sections=64, critical_threshold=500):
    # Создаем JSON модель трубы, которую будем передавать на фронтенд
    pipe_model = {
        "metadata": {
            "version": 1.0,
            "type": "pipe",
            "parameters": {
                "length": length,
                "radius": radius,
                "wall_thickness": wall_thickness,
                "segments": segments,
                "sections": sections,
                "critical_threshold": critical_threshold
            }
        },
        "sensors": [],
        "vertices": [],
        "normals": [],
        "colors": [],
        "indices": []
    }
    
    # Создаем вершины цилиндра (трубы)
    for i in range(sections + 1):
        z = (i / sections) * length
        for j in range(segments):
            theta = (j / segments) * 2 * np.pi
            
            # Внешняя поверхность трубы
            x_outer = radius * np.cos(theta)
            y_outer = radius * np.sin(theta)
            
            # Внутренняя поверхность трубы
            x_inner = (radius - wall_thickness) * np.cos(theta)
            y_inner = (radius - wall_thickness) * np.sin(theta)
            
            # Добавляем вершины внешней и внутренней поверхности
            pipe_model["vertices"].extend([x_outer, y_outer, z])
            pipe_model["vertices"].extend([x_inner, y_inner, z])
            
            # Нормали (упрощенно)
            normal_outer = [np.cos(theta), np.sin(theta), 0]
            normal_inner = [-np.cos(theta), -np.sin(theta), 0]
            
            pipe_model["normals"].extend(normal_outer)
            pipe_model["normals"].extend(normal_inner)
    
    # Создаем индексы для треугольников (faces)
    for i in range(sections):
        for j in range(segments):
            # Индексы для внешней поверхности
            idx00 = 2 * (i * segments + j)
            idx01 = 2 * (i * segments + (j + 1) % segments)
            idx10 = 2 * ((i + 1) * segments + j)
            idx11 = 2 * ((i + 1) * segments + (j + 1) % segments)
            
            # Два треугольника для внешней поверхности
            pipe_model["indices"].extend([idx00, idx10, idx01])
            pipe_model["indices"].extend([idx01, idx10, idx11])
            
            # Индексы для внутренней поверхности
            idx00_in = idx00 + 1
            idx01_in = idx01 + 1
            idx10_in = idx10 + 1
            idx11_in = idx11 + 1
            
            # Два треугольника для внутренней поверхности (обратный порядок)
            pipe_model["indices"].extend([idx00_in, idx01_in, idx10_in])
            pipe_model["indices"].extend([idx01_in, idx11_in, idx10_in])

    # Добавляем информацию о датчиках и цветах деформации
    if sensor_data is not None:
        # Получаем последнюю строку данных (или среднее нескольких строк)
        latest_data = sensor_data.iloc[-1:].mean().to_dict()
        
        # Определяем типы датчиков
        sensor_types = {}
        for column in sensor_data.columns:
            if column == "Time":
                continue
                
            # T2_K_1 - кольцевая деформация
            # T2_Up_1 - верхняя часть
            # T2_R_1 - правая сторона
            # T2_L_1 - левая сторона
            # T_2 - температура
            if "_K_" in column:  # Кольцевая деформация
                sensor_type = "ring"
                sensor_num = int(column.split("_")[-1])
                position = float(sensor_num) / 3.0 * length  # Примерное позиционирование
                pipe_model["sensors"].append({
                    "id": column,
                    "type": sensor_type,
                    "position": [0, 0, position],
                    "value": latest_data.get(column, 0)
                })
            elif "_Up_" in column:  # Верхняя часть
                sensor_type = "up"
                sensor_num = int(column.split("_")[-1])
                position = float(sensor_num) / 3.0 * length
                pipe_model["sensors"].append({
                    "id": column,
                    "type": sensor_type,
                    "position": [0, radius, position],
                    "value": latest_data.get(column, 0)
                })
            elif "_R_" in column:  # Правая сторона
                sensor_type = "right"
                sensor_num = int(column.split("_")[-1])
                position = float(sensor_num) / 3.0 * length
                pipe_model["sensors"].append({
                    "id": column,
                    "type": sensor_type,
                    "position": [radius, 0, position],
                    "value": latest_data.get(column, 0)
                })
            elif "_L_" in column:  # Левая сторона
                sensor_type = "left"
                sensor_num = int(column.split("_")[-1])
                position = float(sensor_num) / 3.0 * length
                pipe_model["sensors"].append({
                    "id": column,
                    "type": sensor_type,
                    "position": [-radius, 0, position],
                    "value": latest_data.get(column, 0)
                })
        
        # Функция для определения цвета на основе значения и критического порога
        def get_color_for_value(value, critical_threshold):
            ratio = value / critical_threshold
            
            if ratio >= 1.0:
                # Красный для критических значений
                return [1.0, 0.0, 0.0]
            elif ratio >= 0.8:
                # Плавный переход от жёлтого к красному
                factor = (ratio - 0.8) / 0.2
                return [1.0, 1.0 * (1 - factor), 0.0]
            else:
                # Плавный переход от зелёного к жёлтому
                factor = ratio / 0.8
                return [factor, 1.0, 0.0]
        
        # Рассчитываем цвета для вершин на основе близости к датчикам и их показаниям
        all_sensor_values = [sensor["value"] for sensor in pipe_model["sensors"] if sensor["type"] != "temperature"]
        
        # Рассчитываем цвета для всех вершин
        num_vertices = len(pipe_model["vertices"]) // 3
        
        for i in range(num_vertices):
            vertex_x = pipe_model["vertices"][i * 3]
            vertex_y = pipe_model["vertices"][i * 3 + 1]
            vertex_z = pipe_model["vertices"][i * 3 + 2]
            
            # Находим ближайший датчик и рассчитываем влияние
            weights = []
            for sensor in pipe_model["sensors"]:
                if sensor["type"] == "temperature":
                    continue
                
                sensor_x, sensor_y, sensor_z = sensor["position"]
                # Рассчитываем расстояние
                distance = np.sqrt((vertex_x - sensor_x)**2 + (vertex_y - sensor_y)**2 + (vertex_z - sensor_z)**2)
                # Влияние обратно пропорционально квадрату расстояния
                weight = 1.0 / (1.0 + distance**2)
                weights.append((sensor["id"], weight, sensor["value"]))
            
            # Нормализуем веса
            total_weight = sum(w[1] for w in weights)
            if total_weight > 0:
                weights = [(sid, w/total_weight, val) for sid, w, val in weights]
            
            # Рассчитываем взвешенное значение деформации для вершины
            weighted_value = sum(val * w for _, w, val in weights) if weights else 0
            
            # Конвертируем в цвет на основе нового алгоритма
            color = get_color_for_value(weighted_value, critical_threshold)
            
            pipe_model["colors"].extend(color)
    
    return pipe_model

# Эндпоинт для получения страницы визуализации
@visualization_bp.route('/', methods=['GET'])
def visualization_page():
    return render_template('visualization.html')

# Эндпоинт для получения данных модели трубы
@visualization_bp.route('/pipe-model', methods=['GET'])
def get_pipe_model():
    try:
        # Получаем параметры из запроса
        length = float(request.args.get('length', 10.0))
        radius = float(request.args.get('radius', 1.0))
        wall_thickness = float(request.args.get('wall_thickness', 0.1))
        segments = int(request.args.get('segments', 32))
        sections = int(request.args.get('sections', 64))
        critical_threshold = float(request.args.get('critical_threshold', 500))
        
        time_start = request.args.get('time_start', None)
        time_end = request.args.get('time_end', None)
        
        # Путь к CSV файлу
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'case_2.csv')
        
        # Загружаем данные датчиков
        sensor_data = read_sensor_data_from_csv(csv_path, time_start, time_end)
        
        if sensor_data is None:
            return jsonify({
                "status": "error",
                "message": "Error reading sensor data from CSV"
            }), 500
        
        # Генерируем модель трубы
        pipe_model = generate_pipe_model(
            sensor_data, 
            length=length, 
            radius=radius, 
            wall_thickness=wall_thickness,
            segments=segments,
            sections=sections,
            critical_threshold=critical_threshold
        )
        
        # Возвращаем JSON модель
        return jsonify({
            "status": "success",
            "model": pipe_model,
            "sensor_data": {col: float(sensor_data[col].iloc[-1]) for col in sensor_data.columns if col != "Time"}
        })
        
    except Exception as e:
        logging.error(f"Error generating pipe model: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error generating pipe model: {str(e)}"
        }), 500

# Эндпоинт для получения всех данных датчиков
@visualization_bp.route('/sensor-data', methods=['GET'])
def get_sensor_data():
    try:
        # Получаем критический порог, если указан
        critical_threshold = float(request.args.get('critical_threshold', 500))
        
        # Путь к CSV файлу
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'case_2.csv')
        
        # Загружаем данные датчиков
        sensor_data = read_sensor_data_from_csv(csv_path)
        
        if sensor_data is None:
            return jsonify({
                "status": "error",
                "message": "Error reading sensor data from CSV"
            }), 500
        
        # Получаем информацию о доступных датчиках
        sensor_info = []
        latest_values = sensor_data.iloc[-1].to_dict()
        
        for column in sensor_data.columns:
            if column == "Time":
                continue
                
            sensor_type = "unknown"
            if "_K_" in column:
                sensor_type = "Кольцевая деформация"
            elif "_Up_" in column:
                sensor_type = "Верхняя часть"
            elif "_R_" in column:
                sensor_type = "Правая сторона"
            elif "_L_" in column:
                sensor_type = "Левая сторона"
            elif column.startswith("T_"):
                sensor_type = "Температура"
            
            value = float(latest_values.get(column, 0))
            
            # Определяем статус на основе значения и критического порога
            status = "normal"
            if value >= critical_threshold:
                status = "critical"
            elif value >= 0.8 * critical_threshold:
                status = "warning"
                
            sensor_info.append({
                "id": column,
                "type": sensor_type,
                "latest_value": value,
                "status": status
            })
        
        # Возвращаем информацию о датчиках
        return jsonify({
            "status": "success",
            "sensors": sensor_info,
            "time_range": {
                "start": sensor_data["Time"].min().isoformat(),
                "end": sensor_data["Time"].max().isoformat()
            },
            "critical_threshold": critical_threshold
        })
        
    except Exception as e:
        logging.error(f"Error getting sensor data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting sensor data: {str(e)}"
        }), 500 