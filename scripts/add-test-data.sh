#!/bin/bash

# Add test data to CCR database

echo "Adding test deployment 1: user-authentication-api on IP4/prd..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "user-authentication-api",
    "platform_id": "IP4",
    "environment_id": "prd",
    "version": "2.1.0",
    "status": "RUNNING",
    "updated_by": "Jibran Patel",
    "properties": {
      "owner": "team-platform",
      "project": "customer-portal",
      "cost_center": "CC-1234"
    }
  }'

echo -e "\n\nAdding test deployment 2: user-authentication-api on OpenShift/tst..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "user-authentication-api",
    "platform_id": "OpenShift",
    "environment_id": "tst",
    "version": "2.0.5",
    "status": "RUNNING",
    "updated_by": "Jibran Patel",
    "properties": {
      "owner": "team-platform",
      "project": "customer-portal"
    }
  }'

echo -e "\n\nAdding test deployment 3: payment-gateway-api on IP4/prd..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "payment-gateway-api",
    "platform_id": "IP4",
    "environment_id": "prd",
    "version": "3.0.1",
    "status": "RUNNING",
    "updated_by": "Jane Smith",
    "properties": {
      "owner": "team-payments",
      "project": "payment-system",
      "replicas": 5
    }
  }'

echo -e "\n\nAdding test deployment 4: payment-gateway-api on AWS/acc..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "payment-gateway-api",
    "platform_id": "AWS",
    "environment_id": "acc",
    "version": "3.0.1",
    "status": "DEPLOYING",
    "updated_by": "Jane Smith",
    "properties": {
      "owner": "team-payments",
      "project": "payment-system"
    }
  }'

echo -e "\n\nAdding test deployment 5: analytics-service on IP5/prd..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "analytics-service",
    "platform_id": "IP5",
    "environment_id": "prd",
    "version": "1.5.2",
    "status": "RUNNING",
    "updated_by": "Bob Johnson",
    "properties": {
      "owner": "team-analytics",
      "project": "data-platform",
      "replicas": 3
    }
  }'

echo -e "\n\nAdding test deployment 6: analytics-service on Azure/dev..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "analytics-service",
    "platform_id": "Azure",
    "environment_id": "dev",
    "version": "1.6.0",
    "status": "STOPPED",
    "updated_by": "Bob Johnson",
    "properties": {
      "owner": "team-analytics"
    }
  }'

echo -e "\n\nAdding test deployment 7: notification-hub on OpenShift/prd..."
curl -X POST http://localhost:31500/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "api_name": "notification-hub",
    "platform_id": "OpenShift",
    "environment_id": "prd",
    "version": "2.2.0",
    "status": "RUNNING",
    "updated_by": "Alice Brown",
    "properties": {
      "owner": "team-notifications",
      "project": "communication-platform"
    }
  }'

echo -e "\n\nTest data added successfully!"
echo "Total: 7 API deployments across 3 APIs, 6 platforms, 4 environments"
