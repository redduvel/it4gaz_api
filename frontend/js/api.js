// API URL configurations
const API_BASE_URL = '/api/v1'; // Base URL for all API calls

// Режим разработки - использовать заглушки вместо реального API
const USE_MOCK_API = false; // Отключаем режим заглушек для работы с реальным API

// Данные заглушек
const MOCK_DATA = {
    tables: {
        status: 'success',
        data: [
            { created_at: "2025-03-04T20:48:42.506465+00:00", id: 1, name: "main" },
            { created_at: "2025-03-04T20:49:32.106465+00:00", id: 2, name: "test" }
        ]
    },
    // Заглушка для метаданных датчиков с русскими названиями типов
    sensorMetadata: {
        status: 'success',
        table_name: 'main',
        sensors: [
            // Кольцевая деформация - код K
            { type: 'Кольцевая деформация', number: 1, code: 'K_1', description: 'Кольцевая деформация датчик #1', units: 'мм' },
            { type: 'Кольцевая деформация', number: 2, code: 'K_2', description: 'Кольцевая деформация датчик #2', units: 'мм' },
            { type: 'Кольцевая деформация', number: 3, code: 'K_3', description: 'Кольцевая деформация датчик #3', units: 'мм' },
            // Левая образующая - код L
            { type: 'Левая образующая', number: 1, code: 'L_1', description: 'Левая образующая датчик #1', units: 'мм' },
            { type: 'Левая образующая', number: 2, code: 'L_2', description: 'Левая образующая датчик #2', units: 'мм' },
            { type: 'Левая образующая', number: 3, code: 'L_3', description: 'Левая образующая датчик #3', units: 'мм' },
            // Верхняя образующая - код Up
            { type: 'Верхняя образующая', number: 1, code: 'Up_1', description: 'Верхняя образующая датчик #1', units: 'мм' },
            { type: 'Верхняя образующая', number: 2, code: 'Up_2', description: 'Верхняя образующая датчик #2', units: 'мм' },
            { type: 'Верхняя образующая', number: 3, code: 'Up_3', description: 'Верхняя образующая датчик #3', units: 'мм' },
            // Правая образующая - код R
            { type: 'Правая образующая', number: 1, code: 'R_1', description: 'Правая образующая датчик #1', units: 'мм' },
            { type: 'Правая образующая', number: 2, code: 'R_2', description: 'Правая образующая датчик #2', units: 'мм' },
            { type: 'Правая образующая', number: 3, code: 'R_3', description: 'Правая образующая датчик #3', units: 'мм' },
            // Температура - код T
            { type: 'Температура', number: null, code: 'T', description: 'Температура', units: '°C' }
        ]
    },
    // Заглушка для данных датчиков
    sensorData: {
        status: 'success',
        data: [
            { Time: '2025-03-04T10:00:00Z', T: 22.5, K_1: 1.2, L_1: 2.0, Up_1: 0.8, R_2: 1.1 },
            { Time: '2025-03-04T11:00:00Z', T: 23.1, K_1: 1.3, L_1: 2.1, Up_1: 0.9, R_2: 1.2 },
            { Time: '2025-03-04T12:00:00Z', T: 23.8, K_1: 1.2, L_1: 2.2, Up_1: 1.0, R_2: 1.3 },
            { Time: '2025-03-04T13:00:00Z', T: 24.2, K_1: 1.4, L_1: 2.3, Up_1: 1.1, R_2: 1.2 },
            { Time: '2025-03-04T14:00:00Z', T: 24.0, K_1: 1.3, L_1: 2.2, Up_1: 1.0, R_2: 1.1 },
            { Time: '2025-03-04T15:00:00Z', T: 23.5, K_1: 1.2, L_1: 2.1, Up_1: 0.9, R_2: 1.0 }
        ]
    }
};

// API endpoints
const API_ENDPOINTS = {
    TABLES: '/analyze/tables',
    SENSOR_METADATA: '/analyze/sensor_metadata',
    SENSOR_DATA: '/analyze/sensor'
};

/**
 * General function to handle API calls
 * @param {string} url - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise} - Promise with response data
 */
async function apiCall(url, options = {}) {
    try {
        console.log(`Вызов API: ${url}`, options);
        
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        console.log(`Ответ API статус: ${response.status} ${response.statusText}`);
        
        // Проверяем, содержит ли ответ JSON
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            console.log('Ответ не в формате JSON:', text);
            data = { 
                status: 'error', 
                message: 'Ответ сервера не в формате JSON' 
            };
        }
        
        console.log(`Ответ API данные:`, data);

        if (!response.ok) {
            throw new Error(data.message || `Ошибка сервера: ${response.status} ${response.statusText}`);
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Get all available tables (pipes)
 * @returns {Promise} - Promise with tables data
 */
async function getTables() {
    // Если включен режим заглушек, возвращаем тестовые данные
    if (USE_MOCK_API) {
        console.log('Using mock data for tables');
        return MOCK_DATA.tables;
    }
    
    const url = `${API_BASE_URL}${API_ENDPOINTS.TABLES}`;
    return apiCall(url);
}

/**
 * Get sensor metadata for a specific table
 * @param {string} tableName - Name of the table
 * @returns {Promise} - Promise with sensor metadata
 */
async function getSensorMetadata(tableName) {
    // Если включен режим заглушек, возвращаем тестовые данные
    if (USE_MOCK_API) {
        console.log('Using mock data for sensor metadata');
        // Клонируем данные чтобы не изменить оригинал
        const mockResponse = JSON.parse(JSON.stringify(MOCK_DATA.sensorMetadata));
        mockResponse.table_name = tableName; // Устанавливаем запрошенное имя таблицы
        return mockResponse;
    }
    
    const url = `${API_BASE_URL}${API_ENDPOINTS.SENSOR_METADATA}/${tableName}`;
    return apiCall(url);
}

/**
 * Get sensor data for a specific table
 * @param {string} tableName - Name of the table
 * @param {Object} filters - Filters to apply to the data
 * @returns {Promise} - Promise with sensor data
 */
async function getSensorData(tableName, filters = {}) {
    // Если включен режим заглушек, возвращаем тестовые данные
    if (USE_MOCK_API) {
        console.log('Using mock data for sensor data with filters:', filters);
        // В реальном приложении здесь можно реализовать фильтрацию моковых данных
        return MOCK_DATA.sensorData;
    }
    
    const url = `${API_BASE_URL}${API_ENDPOINTS.SENSOR_DATA}/${tableName}`;
    
    // Логирование запроса для отладки
    console.log('Sending API request to:', url);
    console.log('Sensors format:', filters.sensors);
    
    // Форматируем каждый объект в массиве sensors для удобства чтения в логах
    const formattedSensors = filters.sensors.map(sensor => {
        const key = Object.keys(sensor)[0];
        return `{"${key}": ${sensor[key]}}`;
    }).join(", ");
    console.log('Formatted sensors for API:', `[${formattedSensors}]`);
    
    return apiCall(url, {
        method: 'POST',
        body: JSON.stringify({
            filters: filters,
            page: 1,
            page_size: 1000 // Request a larger page size for chart data
        })
    });
}

// Handle API error display
function showApiError(error) {
    // Выводим подробную информацию об ошибке в консоль для отладки
    console.error('API Error:', error);
    
    // Формируем сообщение об ошибке в зависимости от типа ошибки
    let errorMessage = 'Произошла ошибка при обращении к API';
    
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        errorMessage = 'Не удалось подключиться к серверу API. Проверьте соединение или запустите сервер.';
    } else if (error instanceof DOMException && error.name === 'NetworkError') {
        errorMessage = 'Ошибка CORS: Запрос к API заблокирован из-за политики безопасности браузера. Проверьте настройки сервера.';
    } else if (error.message) {
        errorMessage = `Ошибка API: ${error.message}`;
    }
    
    // Показываем блок с сообщением об ошибке
    const errorBlock = document.getElementById('apiErrorMessage');
    if (errorBlock) {
        // Добавляем детали ошибки в блок
        const detailsParagraph = document.createElement('p');
        detailsParagraph.className = 'mt-2 text-danger';
        detailsParagraph.textContent = errorMessage;
        
        // Удаляем предыдущие детали ошибки, если они есть
        const existingDetails = errorBlock.querySelector('.text-danger');
        if (existingDetails) {
            existingDetails.remove();
        }
        
        errorBlock.appendChild(detailsParagraph);
        errorBlock.style.display = 'block';
    } else {
        // Запасной вариант, если блок не найден
        alert(errorMessage);
    }
} 