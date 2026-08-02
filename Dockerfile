FROM syntrixsoft/repo:synestatex_ai_env

WORKDIR /app

COPY . /app

ADD ./docker_files/start.sh /start.sh

RUN chmod +x /start.sh

EXPOSE 8000

CMD ["sh", "/start.sh"]
