# Python 3.11 slim base -- small image, and all our dependencies
# (fastapi, pandas, scikit-learn, psycopg[binary]) have prebuilt wheels
# for this, so no extra system build tools are needed.
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (separate layer) so Docker can cache this step --
# rebuilding only re-runs pip install when requirements.txt actually changes,
# not on every code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects its own PORT environment variable at runtime (usually
# 8080) and requires the container to listen on THAT port, not a hardcoded
# one -- this is the single most common Cloud Run deployment mistake.
ENV PORT=8080
EXPOSE 8080

# "exec" form (not a shell wrapping uvicorn as a child process) so uvicorn
# receives shutdown signals directly from Cloud Run -- without this,
# container restarts/deploys can hang or kill connections ungracefully.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
