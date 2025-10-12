# Dockerfile for Dash/Flask app
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port (default 8080, can be overridden)
EXPOSE 8080

# Set environment variable for Flask
ENV FLASK_APP=app

# Optionally set a default container name (can be overridden)
ENV CONTAINER_NAME=PKS_DASHBOARD

# Run the app
CMD ["python", "-m", "app"]
