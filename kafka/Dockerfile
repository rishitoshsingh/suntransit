FROM confluentinc/cp-kafka:7.5.0

USER root  

COPY start-kafka.sh /start-kafka.sh
COPY create-topics.sh /create-topics.sh

RUN chmod +x /start-kafka.sh /create-topics.sh

USER appuser

CMD ["/start-kafka.sh"]