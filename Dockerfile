FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /myproject
COPY . /myproject
RUN pip install -r requirements.txt
WORKDIR /myproject/scheduler_infomin_solutions
