#!/bin/bash

echo "================================"
echo "CCR API Manager - Rebuild Script"
echo "================================"

# Change to project directory
cd ~/rws/ccr/ccr

# Stop existing containers
echo "Stopping existing containers..."
podman-compose down

# Rebuild the Flask app with no cache
echo "Building Flask app..."
podman-compose build --no-cache flask-app

# Start all services
echo "Starting services..."
podman-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check container status
echo "Container status:"
podman ps | grep -E "(flask-app|mongo)"

# Check Flask app logs
echo ""
echo "Flask app logs (last 20 lines):"
podman logs --tail 20 flask-app

# Test the application
echo ""
echo "Testing application endpoints:"
echo "1. Health check:"
curl -s http://localhost:5000/health | python3 -m json.tool

echo ""
echo "2. API search endpoint:"
curl -s "http://localhost:5000/api/search?q=&page=1&page_size=5" | python3 -m json.tool | head -50

echo ""
echo "================================"
echo "Application is running at: http://localhost:5000"
echo "MongoDB Express at: http://localhost:8081"
echo "================================"
echo ""
echo "To view logs:"
echo "  podman logs -f flask-app"
echo ""
echo "To restart:"
echo "  podman-compose restart flask-app"
echo ""