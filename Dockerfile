# Start with a lean official Python image.
FROM python:3.11-slim

# Set the working directory inside the container.
WORKDIR /app

# NO MORE JAVA INSTALLATION NEEDED

# Copy your requirements file into the container.
COPY requirements.txt requirements.txt

# Install all your Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire project folder into the container.
COPY . .

# Command to run your application using Gunicorn.
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
