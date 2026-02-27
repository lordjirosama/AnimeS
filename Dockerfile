FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc build-essential

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "main.py"]


# docker system prune -a -f
# docker build --no-cache -t fsb .
# docker run -d --name fsb
# docker ps
# docker logs fsb
