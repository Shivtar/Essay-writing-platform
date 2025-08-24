# 1. Start with a lean official Python image.
FROM python:3.12-slim

# 2. Set the working directory inside the container.
WORKDIR /app

# 3. Install the Java Runtime Environment (JRE). This is the key step.
# It runs system commands to update the package list and install Java.
RUN apt-get update && apt-get install -y default-jre --no-install-recommends && rm -rf /var/lib/apt/lists/*

# 4. Copy your requirements file into the container.
COPY requirements.txt requirements.txt

# 5. Install all your Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy your entire project folder into the container.
COPY . .

# 7. Tell Docker what command to run when the container starts.
# This uses Gunicorn to run your Flask app (named 'app' inside your 'app.py' file).
# It binds to port 10000, which is what Render expects by default.
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
