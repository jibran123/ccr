# CCR API Manager

A modern, scalable API management system built with Flask and MongoDB, containerized with Podman/Docker for easy deployment.

## 🚀 Features

- **Advanced Search Capabilities**
  - Simple text search across all fields
  - Property-based queries with operators (=, !=, >, <, contains, etc.)
  - Logical operations (AND/OR)
  - Regular expression support
  - Typo tolerance for field names

- **Modern Web Interface**
  - Responsive design
  - Real-time search with pagination
  - JSON viewer with syntax highlighting
  - Export functionality (JSON/CSV)
  - Search help and examples

- **Production Ready**
  - Modular architecture with clear separation of concerns
  - Comprehensive error handling
  - Health checks and metrics endpoints
  - Container-based deployment
  - Non-root container execution
  - Environment-based configuration

## 📁 Project Structure

```
ccr-api-manager/
├── app/                    # Application code
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   ├── routes/            # API endpoints
│   ├── utils/             # Utilities
│   ├── static/            # Frontend assets
│   └── templates/         # HTML templates
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docker/               # Docker configuration
└── docs/                 # Documentation
```

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Flask 3.0
- **Database**: MongoDB
- **Frontend**: Vanilla JavaScript, CSS3
- **Container**: Podman/Docker
- **Testing**: Pytest, Coverage

## 📦 Installation

### Prerequisites

- Python 3.11+
- Podman or Docker
- MongoDB (optional if using containers)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ccr-api-manager.git
cd ccr-api-manager
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run locally**
```bash
python run.py
```

Access the application at `http://localhost:5000`

### Container Deployment

1. **Using Podman Compose**
```bash
podman-compose up -d
```

2. **Using Docker Compose**
```bash
docker-compose up -d
```

3. **Build and run individually**
```bash
# Build the image
podman build -f docker/Dockerfile -t ccr-flask-app:latest .

# Run MongoDB
podman run -d --name mongo -p 27017:27017 mongo:latest

# Run the application
podman run -d --name flask-app -p 5000:5000 \
  -e MONGO_HOST=mongo \
  --network ccr_network \
  ccr-flask-app:latest
```

## 🧪 Testing

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific test categories
```bash
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

### Code quality checks
```bash
flake8 app/                # Linting
black app/ --check         # Format checking
mypy app/                  # Type checking
```

## 🔍 Search Query Examples

### Simple Search
```
user api
```

### Property Search
```
APIName=UserService
Platform!=AWS
Environment contains prod
APIVersion > 2.0
LastUpdated >= 2024-01-01
```

### Logical Operations
```
Platform=AWS AND Environment=production
APIName contains user OR APIName contains customer
```

### Regular Expressions
```
/^User.*Service$/
/api/v[0-9]+/
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main search interface |
| `/api/search` | GET/POST | Execute search query |
| `/api/suggestions/<field>` | GET | Get autocomplete suggestions |
| `/api/stats` | GET | Database statistics |
| `/api/export` | POST | Export results (JSON/CSV) |
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Readiness probe |
| `/health/live` | GET | Liveness probe |
| `/health/metrics` | GET | Prometheus metrics |

## 🔧 Configuration

Configuration is managed through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | production |
| `FLASK_PORT` | Application port | 5000 |
| `MONGO_HOST` | MongoDB hostname | mongo |
| `MONGO_PORT` | MongoDB port | 27017 |
| `MONGO_DB` | Database name | mydatabase |
| `MONGO_COLLECTION` | Collection name | APIs |
| `SECRET_KEY` | Flask secret key | (generated) |

## 🐛 Troubleshooting

### Container Issues

1. **MongoDB connection fails**
```bash
# Check if MongoDB is running
podman ps | grep mongo

# Check logs
podman logs mongo
```

2. **Application won't start**
```bash
# Check application logs
podman logs flask-app

# Verify environment variables
podman exec flask-app env
```

3. **Permission issues**
```bash
# Ensure proper file permissions
chmod +x docker/docker-entrypoint.sh
```

### Development Issues

1. **Import errors**
```bash
# Reinstall dependencies
pip install -r requirements-dev.txt
```

2. **Database connection errors**
```bash
# Verify MongoDB is accessible
python -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017/').server_info()"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add unit tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Use meaningful commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- Flask community for the excellent framework
- MongoDB team for the powerful database
- Podman/Docker for containerization tools

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Podman Documentation](https://docs.podman.io/)
- [Docker Documentation](https://docs.docker.com/)

## 🔮 Future Enhancements

- [ ] Add authentication and authorization
- [ ] Implement API rate limiting
- [ ] Add GraphQL support
- [ ] Enhance search with Elasticsearch
- [ ] Add real-time notifications
- [ ] Implement caching layer (Redis)
- [ ] Add API versioning
- [ ] Enhance monitoring with Grafana
- [ ] Add automated API documentation (Swagger/OpenAPI)
- [ ] Implement data backup and recovery

---

For more information or support, please open an issue on GitHub.