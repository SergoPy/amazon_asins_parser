FROM python:3.9

# Встановлення змінних середовища
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/web_app_v2/env/bin:$PATH"

# Створення робочого каталогу
RUN mkdir /web_app_v2
WORKDIR /web_app_v2

# Встановлення необхідного софту
RUN apt-get -y update && apt-get install -y firefox-esr && apt-get clean && rm -rf /var/lib/apt/lists/*

# Встановлення Python-залежностей
RUN python3 -m venv /web_app_v2/env
RUN /web_app_v2/env/bin/pip install --upgrade pip wheel setuptools

COPY requirements.txt .
RUN /web_app_v2/env/bin/pip install -r requirements.txt

# Копіювання коду
COPY ./amazon ./amazon
COPY startup.sh .

# Створення некореневого користувача
RUN useradd -ms /bin/bash myuser
RUN chown -R myuser:myuser /web_app_v2
USER myuser

# Запуск додатка
CMD ["bash", "./startup.sh"]
