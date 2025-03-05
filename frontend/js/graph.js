// DOM Elements
const pipeSelectElement = document.getElementById('pipeSelect');
const sensorSelectionContainer = document.getElementById('sensorSelectionContainer');
const sensorListElement = document.getElementById('sensorList');
const timePeriodButtons = document.querySelectorAll('[data-time-period]');
const customTimeRangeContainer = document.getElementById('customTimeRange');
const startDateInput = document.getElementById('startDate');
const startTimeInput = document.getElementById('startTime');
const endDateInput = document.getElementById('endDate');
const endTimeInput = document.getElementById('endTime');
const applyTimeRangeButton = document.getElementById('applyTimeRange');

// State variables
let selectedTable = null;
let selectedSensors = [];
let timePeriod = 'day'; // default time period
let sensorMetadata = [];
let customTimeRange = {
    start: null,
    end: null
};

// Colors for chart lines
const chartColors = [
    'rgb(75, 192, 192)',   // teal
    'rgb(255, 99, 132)',   // red
    'rgb(54, 162, 235)',   // blue
    'rgb(255, 159, 64)',   // orange
    'rgb(153, 102, 255)',  // purple
    'rgb(255, 205, 86)',   // yellow
    'rgb(201, 203, 207)'   // grey
];

// Global variables
let chart;
let errorContainer = document.getElementById('chartErrorMessage');

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM content loaded');
    
    // Log all buttons to verify IDs
    console.log('Time period buttons:', timePeriodButtons);
    console.log('Custom range button:', document.getElementById('customTimeRange'));
    console.log('Apply button:', applyTimeRangeButton);
    
    // Load available tables (pipes)
    loadTables();
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize chart
    initChart();
});

// Load available tables from API
async function loadTables() {
    try {
        // Show loading state
        pipeSelectElement.innerHTML = '<option value="" selected disabled>Загрузка...</option>';
        
        // Fetch tables from API
        const response = await getTables();
        
        if (response.status === 'success' && Array.isArray(response.data)) {
            // Clear loading state
            pipeSelectElement.innerHTML = '<option value="" selected disabled>Выберите трубу...</option>';
            
            // Add options for each table
            response.data.forEach(table => {
                const option = document.createElement('option');
                option.value = table.name; // Используем name как значение
                option.textContent = table.name; // Отображаем точно такое же имя как в API
                pipeSelectElement.appendChild(option);
            });
            
            // Если трубы не найдены
            if (response.data.length === 0) {
                pipeSelectElement.innerHTML = '<option value="" selected disabled>Трубы не найдены</option>';
            }
        } else {
            throw new Error('Некорректный формат данных от API');
        }
    } catch (error) {
        pipeSelectElement.innerHTML = '<option value="" selected disabled>Ошибка загрузки</option>';
        showApiError(error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Pipe selection change
    if (pipeSelectElement) {
        pipeSelectElement.addEventListener('change', handlePipeSelection);
    }
    
    // Time period buttons
    if (timePeriodButtons) {
        timePeriodButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Update active state
                timePeriodButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Update time period
                timePeriod = this.getAttribute('data-time-period');
                
                // Показываем или скрываем контейнер с пользовательским диапазоном
                if (timePeriod === 'custom' && customTimeRangeContainer) {
                    customTimeRangeContainer.style.display = 'block';
                    
                    // Инициализируем поля дат текущей датой, если не заданы
                    if (!startDateInput.value) {
                        const today = new Date();
                        const startDate = new Date(today);
                        startDate.setDate(today.getDate() - 7); // По умолчанию неделя назад
                        
                        startDateInput.value = formatDateForInput(startDate);
                        startTimeInput.value = '00:00';
                        endDateInput.value = formatDateForInput(today);
                        endTimeInput.value = '23:59';
                    }
                } else if (customTimeRangeContainer) {
                    customTimeRangeContainer.style.display = 'none';
                }
                
                // Reload data if a table is selected and sensors are chosen
                if (selectedTable && selectedSensors.length > 0) {
                    loadSensorData();
                }
            });
        });
    }
    
    // Custom time range "Apply" button
    if (applyTimeRangeButton) {
        console.log('Apply button found, adding event listener');
        applyTimeRangeButton.addEventListener('click', function() {
            console.log('Apply button clicked');
            try {
                // Проверка заполнения полей
                if (!startDateInput.value || !endDateInput.value) {
                    alert('Пожалуйста, заполните обязательные поля даты.');
                    return;
                }
                
                // Парсинг дат
                const startDateTime = new Date(`${startDateInput.value}T${startTimeInput.value || '00:00'}`);
                const endDateTime = new Date(`${endDateInput.value}T${endTimeInput.value || '23:59'}`);
                console.log('Start date:', startDateTime);
                console.log('End date:', endDateTime);
                
                // Проверка валидности дат
                if (isNaN(startDateTime.getTime()) || isNaN(endDateTime.getTime())) {
                    alert('Пожалуйста, введите корректные даты и время.');
                    return;
                }
                
                // Проверка, что начальная дата меньше конечной
                if (startDateTime >= endDateTime) {
                    alert('Начальная дата должна быть раньше конечной.');
                    return;
                }
                
                // Установка диапазона времени
                customTimeRange.start = startDateTime.toISOString();
                customTimeRange.end = endDateTime.toISOString();
                
                console.log(`Custom time range set: ${customTimeRange.start} - ${customTimeRange.end}`);
                
                // Загрузка данных с новым временным диапазоном
                if (selectedTable && selectedSensors.length > 0) {
                    loadSensorData();
                }
            } catch (error) {
                console.error('Error setting custom time range:', error);
                alert(`Ошибка при установке диапазона: ${error.message}`);
            }
        });
    }
}

// Handle pipe selection change
async function handlePipeSelection() {
    const selectedValue = pipeSelectElement.value;
    
    if (!selectedValue) return;
    
    selectedTable = selectedValue;
    selectedSensors = []; // Reset selected sensors
    
    // Load sensor metadata for the selected table
    await loadSensorMetadata(selectedValue);
}

// Load sensor metadata for a table
async function loadSensorMetadata(tableName) {
    try {
        // Show loading state
        sensorListElement.innerHTML = '<p>Загрузка датчиков...</p>';
        sensorSelectionContainer.style.display = 'block';
        
        // Fetch sensor metadata from API
        const response = await getSensorMetadata(tableName);
        
        if (response.status === 'success' && Array.isArray(response.sensors)) {
            sensorMetadata = response.sensors;
            
            // Group sensors by type
            const sensorsByType = {};
            
            sensorMetadata.forEach(sensor => {
                const sensorType = sensor.type; // Используем полное название типа датчика
                
                if (!sensorsByType[sensorType]) {
                    sensorsByType[sensorType] = [];
                }
                sensorsByType[sensorType].push(sensor);
            });
            
            // Generate sensor selection UI
            let html = '';
            
            for (const [type, sensors] of Object.entries(sensorsByType)) {
                html += `<div class="sensor-type-group mb-3">
                            <h6>${type}</h6>
                            <div class="row">`;
                
                sensors.forEach(sensor => {
                    html += `<div class="col-md-6 mb-2">
                                <div class="form-check">
                                    <input class="form-check-input sensor-checkbox" 
                                           type="checkbox" 
                                           value='${JSON.stringify({type: sensor.type, number: sensor.number})}'
                                           id="sensor-${sensor.code}">
                                    <label class="form-check-label" for="sensor-${sensor.code}">
                                        ${sensor.description || `${sensor.type} #${sensor.number || ''}`}
                                        ${sensor.units ? `(${sensor.units})` : ''}
                                    </label>
                                </div>
                            </div>`;
                });
                
                html += `</div></div>`;
            }
            
            // Add a button to apply selection
            html += `<button id="applySensorSelection" class="btn btn-primary">Применить выбор</button>`;
            
            sensorListElement.innerHTML = html;
            
            // Add event listener for the apply button
            document.getElementById('applySensorSelection').addEventListener('click', function() {
                const checkboxes = document.querySelectorAll('.sensor-checkbox:checked');
                selectedSensors = Array.from(checkboxes).map(checkbox => JSON.parse(checkbox.value));
                
                if (selectedSensors.length > 0) {
                    loadSensorData();
                } else {
                    alert('Пожалуйста, выберите хотя бы один датчик');
                }
            });
            
        } else {
            throw new Error('Не удалось загрузить метаданные датчиков');
        }
    } catch (error) {
        sensorListElement.innerHTML = '<p class="text-danger">Ошибка загрузки датчиков</p>';
        showApiError(error);
    }
}

// Load sensor data from API
function loadSensorData() {
    console.log('loadSensorData called');
    
    // Очистить предыдущие сообщения об ошибках
    errorContainer.textContent = '';
    errorContainer.classList.remove('alert-danger', 'alert-warning', 'alert-info');
    
    // Получить выбранные сенсоры и временной период
    const selectedSensors = getSelectedSensors();
    const timePeriod = getSelectedTimePeriod();
    
    console.log('Selected sensors:', selectedSensors);
    console.log('Selected time period:', timePeriod);
    
    if (selectedSensors.length === 0) {
        displayErrorMessage('Выберите хотя бы один датчик', 'warning');
        return;
    }

    // Получить временной диапазон для выбранного периода
    const { start, end } = getTimeRangeForPeriod(timePeriod);
    console.log(`Loading data for period: ${timePeriod}, range: ${start} to ${end}`);

    // Показать сообщение о загрузке
    errorContainer.textContent = 'Загрузка данных...';
    errorContainer.classList.add('alert-info');
    errorContainer.style.display = 'block';

    // Prepare filters
    const selectedPipeId = pipeSelectElement.value;
    console.log('Selected pipe ID:', selectedPipeId);
    
    const filters = {
        pipe_id: selectedPipeId,
        start_time: start,
        end_time: end,
        sensors: selectedSensors
    };
    
    console.log('API request filters:', filters);

    // Fetch data from API
    const apiUrl = `/api/v1/analyze/sensor/${selectedPipeId}`;
    console.log('API endpoint:', apiUrl);
    
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(filters)
    })
    .then(response => {
        console.log('API response status:', response.status);
        if (!response.ok) {
            throw new Error('Ошибка загрузки данных');
        }
        return response.json();
    })
    .then(data => {
        console.log('API response data:', data);
        
        // Убрать сообщение о загрузке и показать сообщение об успехе
        errorContainer.textContent = 'Данные успешно загружены';
        errorContainer.classList.remove('alert-info');
        errorContainer.classList.add('alert-success');
        
        // Скрыть сообщение об успехе через 3 секунды
        setTimeout(() => {
            if (errorContainer.textContent === 'Данные успешно загружены') {
                errorContainer.style.display = 'none';
            }
        }, 3000);
        
        updateChart(data);
    })
    .catch(error => {
        console.error('Error loading data:', error);
        displayErrorMessage(`Ошибка при загрузке данных: ${error.message}`, 'danger');
    });
}

// Calculate time range based on selected period
function getTimeRangeForPeriod(period) {
    console.log('getTimeRangeForPeriod called with period:', period);
    console.log('Current customTimeRange:', customTimeRange);
    
    // Если выбран пользовательский диапазон и он настроен
    if (period === 'custom' && customTimeRange.start && customTimeRange.end) {
        console.log(`Using custom time range: ${customTimeRange.start} - ${customTimeRange.end}`);
        return {
            start: customTimeRange.start,
            end: customTimeRange.end
        };
    }
    
    // Стандартные периоды
    const now = new Date();
    const end = now.toISOString();
    let start;
    
    switch (period) {
        case 'day':
            start = new Date(new Date().setDate(now.getDate() - 1)).toISOString();
            break;
        case 'week':
            start = new Date(new Date().setDate(now.getDate() - 7)).toISOString();
            break;
        case 'month':
            start = new Date(new Date().setMonth(now.getMonth() - 1)).toISOString();
            break;
        default:
            start = new Date(new Date().setDate(now.getDate() - 1)).toISOString();
    }
    
    return { start, end };
}

// Обработка вывода больших значений на график
function checkLargeValues(dataset) {
    // Проверяем, есть ли очень большие значения в наборе данных
    const values = dataset.filter(val => val !== null);
    
    if (values.length === 0) return false;
    
    const maxValue = Math.max(...values);
    const minValue = Math.min(...values);
    const range = maxValue - minValue;
    
    // Если максимальное значение больше 500 или диапазон очень большой
    if (maxValue > 500 || range > 500) {
        console.warn(`Large values detected: min=${minValue}, max=${maxValue}, range=${range}`);
        return true;
    }
    
    return false;
}

// Update chart with new data
function updateChart(data) {
    // Сначала скрываем контейнер с сообщением об ошибке
    const errorContainer = document.getElementById('chartErrorMessage');
    const errorText = document.getElementById('chartErrorText');
    
    if (errorContainer) {
        errorContainer.style.display = 'none';
    }
    
    if (!data || data.length === 0) {
        console.warn('Не получены данные для графика');
        if (errorContainer && errorText) {
            errorText.textContent = 'Нет данных для отображения на графике. Пожалуйста, выберите другие датчики или временной интервал.';
            errorContainer.style.display = 'block';
        }
        return;
    }

    console.log('Updating chart with data:', data);
    
    // Extract unique timestamps for x-axis
    const timestamps = data.map(item => new Date(item.Time));
    
    // Prepare datasets for each selected sensor
    const datasets = [];
    let hasLargeValues = false;
    
    selectedSensors.forEach((sensor, index) => {
        // Определяем ключ в данных на основе типа и номера датчика
        let sensorKey;
        
        // Обработка специальных типов (например, "Температура", для которой может не быть номера)
        if (sensor.number === null) {
            sensorKey = sensor.type === 'Температура' ? 'T' : sensor.type;
        } else {
            // Для датчиков с номером используем правило, например "Кольцевая деформация" -> "K_1"
            // Получаем код из метаданных
            const metadata = sensorMetadata.find(meta => 
                meta.type === sensor.type && meta.number === sensor.number
            );
            
            if (metadata && metadata.code) {
                sensorKey = metadata.code;
            } else {
                // Запасной вариант если не найден код
                const prefix = sensor.type.charAt(0).toUpperCase(); // Первая буква типа
                sensorKey = `${prefix}_${sensor.number}`;
            }
        }
        
        console.log(`Mapping sensor ${sensor.type} #${sensor.number} to key ${sensorKey}`);
        
        // Получаем значения для этого датчика
        const sensorData = data.map(item => {
            // Проверка существования данных в ответе
            if (item && sensorKey in item) {
                const value = item[sensorKey];
                // Проверяем, что значение корректно для отображения
                if (value === null || value === undefined || isNaN(value)) {
                    console.warn(`Invalid value for ${sensorKey} at time ${item.Time}: ${value}`);
                    return null; // Для пропуска точки на графике
                }
                return parseFloat(value); // Преобразуем в число на всякий случай
            } else {
                console.warn(`No data found for sensor key ${sensorKey} at time ${item.Time}`);
                return null;
            }
        });
        
        // Проверяем, есть ли валидные данные для отображения
        if (sensorData.every(val => val === null)) {
            console.warn(`No valid data for sensor ${sensorKey}, skipping dataset`);
            return; // Пропускаем этот датчик
        }
        
        // Проверяем, есть ли большие значения
        if (checkLargeValues(sensorData)) {
            hasLargeValues = true;
        }
        
        // Находим метаданные для метки
        const metadata = sensorMetadata.find(meta => 
            meta.type === sensor.type && meta.number === sensor.number
        );
        
        // Формируем метку с описанием и единицами измерения
        const label = metadata ? 
            `${metadata.description || metadata.code || sensorKey} ${metadata.units ? `(${metadata.units})` : ''}` : 
            sensorKey;
        
        datasets.push({
            label: label,
            data: sensorData,
            borderColor: chartColors[index % chartColors.length],
            backgroundColor: chartColors[index % chartColors.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.1,
            fill: false
        });
    });
    
    // Если нет данных для отображения, показываем сообщение
    if (datasets.length === 0) {
        console.warn('No datasets to display on chart');
        if (errorContainer && errorText) {
            errorText.textContent = 'Не удалось получить данные для выбранных датчиков. Пожалуйста, выберите другие датчики.';
            errorContainer.style.display = 'block';
        }
        return;
    }
    
    // Format timestamps for display
    const labels = timestamps.map(timestamp => {
        return new Intl.DateTimeFormat('ru', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(timestamp);
    });
    
    // Update chart data
    chart.data.labels = labels;
    chart.data.datasets = datasets;
    
    // Обновляем опции для корректного масштабирования
    const allValues = datasets.flatMap(dataset => dataset.data.filter(val => val !== null));
    
    // Если есть данные, настраиваем масштаб оси Y
    if (allValues.length > 0) {
        const minValue = Math.min(...allValues);
        const maxValue = Math.max(...allValues);
        
        // Добавляем буфер 10% сверху и снизу для лучшего отображения
        const range = maxValue - minValue;
        const buffer = range * 0.1;
        
        console.log(`Chart value range: min=${minValue}, max=${maxValue}, range=${range}`);
        
        // Отображаем предупреждение, если есть большие значения
        if (hasLargeValues && errorContainer && errorText) {
            errorText.textContent = 'График содержит очень большие значения. Масштаб был автоматически адаптирован.';
            errorContainer.className = 'alert alert-info';
            errorContainer.style.display = 'block';
        }
        
        // Обновляем настройки оси Y только если у нас есть значения для масштабирования
        chart.options.scales.y.min = range > 0 ? Math.max(0, minValue - buffer) : undefined;
        chart.options.scales.y.max = range > 0 ? maxValue + buffer : undefined;
    } else {
        // Нет значений для отображения
        if (errorContainer && errorText) {
            errorText.textContent = 'Нет данных для построения графика в указанном диапазоне.';
            errorContainer.style.display = 'block';
        }
    }
    
    chart.update();
}

// Function to display error message
function displayErrorMessage(message, type = 'danger') {
    if (!errorContainer) return;
    
    errorContainer.textContent = message;
    errorContainer.className = 'alert';
    
    switch (type) {
        case 'danger':
            errorContainer.classList.add('alert-danger');
            break;
        case 'warning':
            errorContainer.classList.add('alert-warning');
            break;
        case 'info':
            errorContainer.classList.add('alert-info');
            break;
        case 'success':
            errorContainer.classList.add('alert-success');
            break;
    }
    
    errorContainer.style.display = 'block';
}

// Get selected time period
function getSelectedTimePeriod() {
    const dayButton = document.getElementById('periodDay');
    const weekButton = document.getElementById('periodWeek');
    const monthButton = document.getElementById('periodMonth');
    const customButton = document.getElementById('periodCustom');
    
    if (dayButton && dayButton.classList.contains('active')) {
        return 'day';
    } else if (weekButton && weekButton.classList.contains('active')) {
        return 'week';
    } else if (monthButton && monthButton.classList.contains('active')) {
        return 'month';
    } else if (customButton && customButton.classList.contains('active')) {
        return 'custom';
    }
    
    // По умолчанию используем выбранный в атрибуте кнопки период
    const activeButton = document.querySelector('[data-time-period].active');
    if (activeButton) {
        return activeButton.getAttribute('data-time-period');
    }
    
    // Если ничего не найдено, возвращаем день
    return 'day';
}

// Get selected sensors
function getSelectedSensors() {
    const checkboxes = document.querySelectorAll('.sensor-checkbox:checked');
    return Array.from(checkboxes).map(checkbox => JSON.parse(checkbox.value));
}

// Format date for setting in input fields
function formatDateForInput(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Format time for input fields
function formatTimeForInput(date) {
    const d = new Date(date);
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
}

// Parse date and time from input fields
function parseCustomTimeRange() {
    const startDate = startDateInput.value;
    const startTime = startTimeInput.value || '00:00';
    const endDate = endDateInput.value;
    const endTime = endTimeInput.value || '23:59';
    
    const start = new Date(`${startDate}T${startTime}`);
    const end = new Date(`${endDate}T${endTime}`);
    
    return { start, end };
} 