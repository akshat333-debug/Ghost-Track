# Reproducible build and run of the submission on Linux.
# docker build -t pathfinder . && docker run --rm -v "$PWD/data:/data" pathfinder /data/imu0/data.csv /data/estimated_trajectory.txt
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
COPY src/ /src/
RUN g++ -O2 -std=c++17 -o /usr/local/bin/pathfinder /src/main.cpp
ENTRYPOINT ["pathfinder"]
