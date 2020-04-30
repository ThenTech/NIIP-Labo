if (docker ps -aq) {
    Write-Host "Stopping all docker processes..."
    docker stop $(docker ps -aq)
}

Write-Host "Pruning existing images..."
docker system prune -f

Write-Host "Building lab5 image..."
docker build -t lab5 .
