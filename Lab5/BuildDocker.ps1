docker stop $(docker ps -aq)
docker system prune
docker build -t lab5 .