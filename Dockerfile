from carbide/overlord_base:latest

ADD ./carbide_overlord /opt/carbide-overlord/carbide_overlord
ADD ./twisted /opt/carbide-overlord/twisted
ENV PYTHONPATH /opt/carbide-overlord
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/twistd", "--nodaemon"]
