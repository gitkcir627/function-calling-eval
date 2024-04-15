FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    vim \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /funtion-calling-eval
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /funtion-calling-eval/berkeley-function-call-leaderboard

# dummy command to keep  container running 
CMD ["tail", "-f", "/dev/null"]




#sudo docker image rm zhihao/funtion-calling-eval
#sudo docker build -t zhihao/funtion-calling-eval .
#
#sudo docker run \
#-it --name funtion-calling-eval --rm --privileged \
#-v $(pwd)/:/funtion-calling-eval/berkeley-function-call-leaderboard/ \
#zhihao/funtion-calling-eval bash
#
#sudo docker exec -it funtion-calling-eval bash
