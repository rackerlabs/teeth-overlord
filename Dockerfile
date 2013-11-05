FROM ubuntu:12.10
RUN apt-get update
RUN apt-get install -q -y python python-dev python-pip build-essential git-core
RUN pip install Twisted==13.1.0
ADD ./requirements.txt /tmp/teeth-overlord-requirements.txt
RUN pip install -r /tmp/teeth-overlord-requirements.txt
ADD . /opt/teeth-overlord
