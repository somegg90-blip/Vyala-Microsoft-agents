# Use Python 3.11 slim image
FROM python:3.11-slim

# Install wget and curl to download Qdrant
RUN apt-get update && apt-get install -y wget curl && rm -rf /var/lib/apt/lists/*

# Download Qdrant binary
RUN wget -O /qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.9.1/qdrant-x86_64-unknown-linux-gnu.tar.gz && \
    tar -xzf /qdrant.tar.gz && \
    mv qdrant /usr/local/bin/ && \
    rm /qdrant.tar.gz

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make run script executable
RUN chmod +x run.sh

# Expose Streamlit port
EXPOSE 7860

# Run the startup script
CMD ["./run.sh"]