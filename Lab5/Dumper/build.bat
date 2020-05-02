@echo off
docker build -t tcpdump .
docker network create demo-net