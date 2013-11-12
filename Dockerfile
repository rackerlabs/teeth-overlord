from teeth/base:latest

ADD ./requirements.txt /opt/teeth-overlrod/requirements.txt
ADD ./src/teeth-agent /opt/teeth-overlord/src/teeth-agent
RUN cd /opt/teeth-overlord && pip install -r requirements.txt
