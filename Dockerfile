from teeth/overlord_base:latest

ADD ./teeth_overlord /opt/teeth-overlord/teeth_overlord
ADD ./twisted /opt/teeth-overlord/twisted
ENV PYTHONPATH /opt/teeth-overlord
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/twistd", "--nodaemon"]
