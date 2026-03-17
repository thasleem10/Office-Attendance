# Stage 1: Build stage (The heavy lifting)
FROM python:3.10-slim-bullseye as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 1. Install cmake and dlib separately with EXTREME memory conservation
# CMAKE_BUILD_PARALLEL_LEVEL=1 forces a single core for compilation
# DLIB_NO_GUI_SUPPORT and DLIB_USE_CUDA=0 reduce the code complexity
RUN pip install --no-cache-dir cmake
RUN CMAKE_BUILD_PARALLEL_LEVEL=1 \
    DLIB_USE_CUDA=0 \
    DLIB_NO_GUI_SUPPORT=1 \
    pip install --no-cache-dir dlib==19.24.2

# 2. Install the rest of the requirements
COPY requirements.txt .
# Filter out dlib from requirements.txt so pip doesn't try to re-process it
RUN sed -i '/dlib/d' requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime stage (The lightweight version)
FROM python:3.10-slim-bullseye

# Install runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    liblapack3 \
    libx11-6 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Ensure data and model directories exist
RUN mkdir -p data model static/uploads

# Expose port
EXPOSE 10000

# Run with extra timeout for AI model loading
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]
