FROM python:3.12-slim

# System deps (wkhtmltopdf for PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create secure directory for runtime data
RUN mkdir -p secure/storage/certificates

# Expose the app port
EXPOSE 8300

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8300"]
