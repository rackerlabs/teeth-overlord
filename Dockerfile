FROM jayofdoom/docker-ubuntu-14.04

ADD . /tmp/teeth-overlord

RUN apt-get update && apt-get -y install python python-pip python-dev git 

RUN pip install /tmp/teeth-overlord
