@echo off
REM docker run -e MSG="Hello World!" -e ADDR="0499123456" -e WHITELIST="[]" -e FILTER=1 -it lab5

echo Starting network topology by creating restricted cliient.
echo Drag the new window to an appropriate location

start "Client 1" docker run -e ADDR="1" -e WHITELIST="[2,3,4]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 2" docker run -e ADDR="2" -e WHITELIST="[1,5]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 3" docker run -e ADDR="3" -e WHITELIST="[1,5]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 4" docker run -e ADDR="4" -e WHITELIST="[1,6]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 5" docker run -e ADDR="5" -e WHITELIST="[2,3,7]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 6" docker run -e ADDR="6" -e WHITELIST="[4,8]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 7" docker run -e ADDR="7" -e WHITELIST="[5,8]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

start "Client 8" docker run -e ADDR="8" -e WHITELIST="[6,7]" -e FILTER=1 -it lab5
ping 127.0.0.1 -n 4 > nul
echo Running:
docker ps -aq

echo Done.