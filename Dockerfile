FROM python:3.11-slim

WORKDIR /app

# نصب dependencies سیستم
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌های requirements
COPY requirements.txt .

# نصب dependencies پایتون
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد برنامه
COPY . .

# ایجاد volume برای دیتابیس (اختیاری)
VOLUME /app/data

# اجرای برنامه
CMD ["python", "run.py"]
