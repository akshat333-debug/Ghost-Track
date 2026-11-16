# Reproducible run of the submission on Linux. Standard library only, so there is nothing to install.
# docker build -t pathfinder . && docker run --rm -v "$PWD/data:/data" pathfinder /data/imu0/data.csv /data/estimated_trajectory.txt
FROM python:3.12-slim
COPY src/ /src/
ENTRYPOINT ["python3", "/src/main.py"]
