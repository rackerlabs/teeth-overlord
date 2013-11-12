from teeth/base:latest

ADD ./requirements.txt /opt/teeth-overlord/requirements.txt
ADD ./teeth-agent /opt/teeth-agent
RUN cd /opt/teeth-overlord && pip install -r requirements.txt
