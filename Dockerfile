# OpenShift-friendly base image (non-root)
FROM registry.access.redhat.com/ubi9/python-311

# Switch to root only to install system packages
USER 0

# Add Microsoft repo + install ODBC driver for SQL Server
RUN curl -sSL https://packages.microsoft.com/config/rhel/9/prod.repo \
    -o /etc/yum.repos.d/mssql-release.repo \
 && ACCEPT_EULA=Y microdnf install -y \
    msodbcsql18 \
    unixODBC-devel \
    gcc-c++ \
 && microdnf clean all

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pyodbc

# Drop back to non-root user (required by OpenShift)
USER 1001

WORKDIR /app

# Copy backend code
COPY main.py .

# Expose app port
EXPOSE 8000

# Start the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
