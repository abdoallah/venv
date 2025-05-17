FROM python:3.11

# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    gnupg \
    curl \
    unixodbc \
    unixodbc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft repository for SQL Server ODBC Driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install SQL Server ODBC Driver
RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# List installed drivers for debugging
RUN odbcinst -j && \
    cat /etc/odbcinst.ini || echo "No odbcinst.ini file"

# Set environment variable to indicate we're in Docker
ENV RUNNING_IN_DOCKER=1

# Set working directory
WORKDIR /app

# Create output directory for Excel files
RUN mkdir -p /app/output

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install flask-cors explicitly
RUN pip install flask-cors

# Copy source code
COPY . .

# Expose Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "-u", "sql_web_app.py"]