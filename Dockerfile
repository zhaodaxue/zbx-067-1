FROM python:3.11-slim

WORKDIR /app

COPY gpx_elevation_check.py /app/gpx_elevation_check.py

RUN chmod +x /app/gpx_elevation_check.py

ENTRYPOINT ["python", "/app/gpx_elevation_check.py"]
CMD ["--help"]
