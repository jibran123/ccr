#!/bin/bash
set -e

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
while ! nc -z ${MONGO_HOST:-mongo} ${MONGO_PORT:-27017}; do
    sleep 1
done
echo "MongoDB is ready!"

# Run migrations or initialization if needed
# python manage.py init_db

# Start the application
exec "$@"