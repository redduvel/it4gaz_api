# 3D Pipe Visualization API

This project provides an API and frontend for visualizing a 3D pipe that can be deformed based on sensor data.

## Features

- 3D visualization of a pipe using Three.js
- API endpoints to get pipe model data based on sensor readings
- Interactive controls to adjust visualization parameters
- Real-time deformation of the pipe based on sensor data

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, JavaScript, Three.js
- **Data Processing**: NumPy

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   python main.py
   ```
5. Open your browser and navigate to `http://localhost:5000/api/pipe/`

## API Endpoints

- `GET /api/pipe/`: Serves the 3D visualization frontend
- `GET /api/pipe/sensor-data`: Returns sensor data for pipe deformation
  - Query parameters:
    - `sensors`: Number of sensors (default: 10)
- `GET /api/pipe/pipe-model`: Returns 3D pipe model data based on sensor readings
  - Query parameters:
    - `sensors`: Number of sensors (default: 10)
    - `segments`: Number of segments around the pipe circumference (default: 32)

## How It Works

1. The backend generates mock sensor data (in a real application, this would come from actual sensors)
2. The pipe model is generated based on the sensor data, creating a deformed 3D pipe
3. The frontend fetches this model data and renders it using Three.js
4. Users can interact with the visualization using mouse controls and UI parameters

## Future Improvements

- Connect to real sensor data sources
- Add more deformation algorithms and visualization options
- Implement real-time updates using WebSockets
- Add analytics and data export features

## Deployment on Render.com

This application is configured for easy deployment on Render.com:

1. Create a new account or log in to your existing account on [Render.com](https://render.com)

2. From the Render dashboard, click on "New" and select "Blueprint" to deploy using the render.yaml configuration

3. Connect your GitHub repository

4. Configure the following environment variables in the Render dashboard:
   - `SUPABASE_URL`: Your Supabase URL
   - `SUPABASE_KEY`: Your Supabase API key
   - `FLASK_DEBUG`: Set to `False` for production

5. Deploy the application

Alternatively, you can deploy manually:

1. From the Render dashboard, click on "New" and select "Web Service"

2. Connect your GitHub repository

3. Configure the service with the following settings:
   - **Name**: it4gaz-api (or your preferred name)
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app`

4. Add the environment variables mentioned above

5. Click "Create Web Service"

The application will be deployed and available at the URL provided by Render.

## Monitoring and Logs

After deployment, you can monitor your application and view logs from the Render dashboard. This is useful for troubleshooting any issues that might arise in the production environment 