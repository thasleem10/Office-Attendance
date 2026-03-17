FROM python:3.9-slim-bullseye

# 1. Install PRE-COMPILED system packages ONLY
# We do NOT install build-essential or cmake to guarantee ZERO compilation attempt.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dlib \
    python3-numpy \
    python3-opencv \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Configure Python to use these system packages
ENV PYTHONPATH="/usr/lib/python3/dist-packages"

WORKDIR /app

# 3. Handle requirements
COPY requirements.txt .
# We remove numpy, opencv, and dlib from requirements.txt to prevent pip from looking for them
RUN sed -i '/numpy/d' requirements.txt && \
    sed -i '/opencv/d' requirements.txt && \
    sed -i '/dlib/d' requirements.txt

# 4. Install other dependencies
# Using --no-deps for face_recognition is the CRITICAL fix.
# It prevents pip from even checking if dlib or numpy are installed.
RUN pip install --no-cache-dir face_recognition==1.3.0 --no-deps
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy code and setup
COPY . .
RUN mkdir -p data model static/uploads

EXPOSE 10000

# Run the app
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]
