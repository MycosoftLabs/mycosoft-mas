FROM python:3.11-slim
WORKDIR /app
COPY ../../requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ../../mycosoft_mas ./mycosoft_mas
CMD ["python", "-m", "mycosoft_mas.core.myca_main"]
