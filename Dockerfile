FROM python:3.11

WORKDIR /usr/src/app

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copying requirements files
COPY requirements.txt .
COPY install_requirements.sh .

# Grant execute permissions to the script
RUN chmod +x install_requirements.sh

# Installing dependencies
RUN ./install_requirements.sh

# Copying the rest of the application files
COPY . .

# Running the main Python script
CMD ["python", "main.py"]