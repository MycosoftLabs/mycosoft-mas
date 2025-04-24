# Start MAS backend services
Write-Host "Starting MAS backend services..."
docker-compose up -d

# Wait for services to be ready
Write-Host "Waiting for services to be ready..."
Start-Sleep -Seconds 10

# Start MYCA APP development server
Write-Host "Starting MYCA APP development server..."
npm run dev 