from teeth/base:latest

RUN gpg --keyserver pgp.mit.edu --recv-keys F758CE318D77295D 2B5C1B00
RUN gpg --export --armor F758CE318D77295D | sudo apt-key add -
RUN gpg --export --armor 2B5C1B00 | sudo apt-key add -
RUN echo "deb http://www.apache.org/dist/cassandra/debian 20x main" > /etc/apt/sources.list.d/casasndra.list
RUN apt-get update && apt-get -y install cassandra=2.0.2

ENTRYPOINT ["/usr/sbin/cassanrdra", "-f"]
