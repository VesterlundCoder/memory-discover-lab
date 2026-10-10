FROM python:3.12-slim
WORKDIR /opt/memory-discover-lab
COPY . .
RUN python -m pip install --no-cache-dir -e ./lab
CMD ["python", "scripts/evaluate_system.py", "step1", "--out", "/results/step1"]
