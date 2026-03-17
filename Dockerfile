FROM python:3.9-slim-bullseye

# 1. Install pre-compiled system packages
# This avoids the 8GB RAM compilation limit on Render entirely.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dlib \
    python3-numpy \
    python3-opencv \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Tell Python where to find the system-installed packages
ENV PYTHONPATH="/usr/lib/python3/dist-packages"

WORKDIR /app

# 3. Handle requirements
COPY requirements.txt .
# We remove dlib, numpy, and opencv from requirements.txt 
# because we already installed them via the system-level 'apt' command above.
RUN sed -i '/dlib/d' requirements.txt && \
    sed -i '/numpy/d' requirements.txt && \
    sed -i '/opencv/d' requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy code and setup
COPY . .
RUN mkdir -p data model static/uploads

EXPOSE 10000

# Run the app
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]
