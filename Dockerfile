FROM python:3.12.14-slim
WORKDIR /opt/memory-discover-lab
COPY . .
RUN python -m pip install --no-cache-dir -c requirements-lock-core.txt -c lab/constraints-tested.txt -e ./lab
CMD ["python", "scripts/reproduce_system.py", "--out", "/results/system", "--reference-root", "evaluation/results/repaired"]
