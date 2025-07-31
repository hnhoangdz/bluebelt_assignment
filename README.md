# Dextrends AI Chat Platform

A sophisticated conversational AI platform that implements advanced RAG (Retrieval Augmented Generation) with memory management, vector search, and intelligent context understanding. Built for Dextrends, a leading technology company specializing in digital financial services and blockchain solutions.

## 🚀 Key Features

### Advanced AI Capabilities
- **RAG-Powered Conversations**: Intelligent responses using company knowledge base and FAQ data
- **Memory Management**: Persistent conversation context with Mem0 integration
- **Vector Search**: Semantic search across company offerings using Qdrant
- **Intent Recognition**: Smart query classification and routing
- **Personalization**: User-specific responses based on interaction history

### Enterprise-Grade Architecture
- **Multi-Database Design**: PostgreSQL, Redis, and Qdrant for optimized data storage
- **Session Management**: Isolated conversation contexts with persistent memory
- **Authentication & Authorization**: Secure JWT-based authentication with session tracking
- **Real-time Chat Interface**: Modern React-based UI with WebSocket-like experience
- **Analytics & Monitoring**: Comprehensive tracking of conversations, performance, and user engagement

### Production-Ready Infrastructure
- **Containerized Deployment**: Full Docker orchestration with health checks
- **Scalable Design**: Microservices architecture with independent scaling
- **Security Features**: Rate limiting, input validation, and secure error handling
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │   FastAPI API   │    │   OpenAI GPT    │
│   (TypeScript)  │◄──►│   (Python)      │◄──►│   (Embeddings)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   RAG Pipeline  │              │
         │              │  Query→Context  │              │
         │              │  →Generation    │              │
         │              └─────────────────┘              │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   PostgreSQL    │    │   Qdrant Vector │
│   (Static Files)│    │   (User Data)   │    │   (Embeddings)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   Redis Cache   │              │
         │              │   (Sessions)    │              │
         │              └─────────────────┘              │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                        ┌─────────────────┐
                        │   Mem0 Memory   │
                        │   (Context)     │
                        └─────────────────┘
```

## 🛠️ Technology Stack

### Backend (FastAPI)
- **Framework**: FastAPI with async/await support
- **Database ORM**: SQLAlchemy with PostgreSQL
- **Cache Layer**: Redis for sessions and rate limiting
- **Vector Database**: Qdrant for semantic search
- **AI Integration**: OpenAI API (GPT-4, text-embedding-3-small)
- **Memory Service**: Mem0 for conversation context
- **Authentication**: JWT tokens with bcrypt password hashing
- **API Documentation**: Automatic OpenAPI/Swagger generation

### Frontend (React)
- **Framework**: React 18 with TypeScript
- **Routing**: React Router v6
- **State Management**: React Context API
- **HTTP Client**: Fetch API with error handling
- **UI Components**: Custom components with Lucide React icons
- **Styling**: Modern CSS with CSS Grid and Flexbox
- **Build Tool**: Create React App with production optimization

### Infrastructure & DevOps
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose with service dependencies
- **Web Server**: Nginx for static file serving and reverse proxy
- **Health Monitoring**: Docker health checks for all services
- **Environment Management**: Configurable via environment variables

### Database Architecture
- **PostgreSQL**: Primary database for users, sessions, conversations
- **Redis**: Session storage, caching, and rate limiting
- **Qdrant**: Vector embeddings for semantic search
- **Data Models**: UUID primary keys, JSONB for flexible metadata

## 📋 Prerequisites

- Docker and Docker Compose v2
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- OpenAI API key with GPT-4 access
- Mem0 API key (optional, for enhanced memory features)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bluebelt_assignment
```

### 2. Environment Setup

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# Application Settings
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Database Configuration
DATABASE_URL=postgresql://dextrends_user:dextrends_password@localhost:5432/dextrends_chatbot

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Mem0 Configuration (Optional)
MEM0_API_KEY=your-mem0-api-key-here
```

### 3. Launch Services

```bash
# Start all services with Docker Compose
docker compose up -d

# View service logs
docker compose logs -f

# Check service health
docker compose ps
```

### 4. Initialize Vector Database

```bash
# Upload company data and FAQ to Qdrant
docker exec dextrends_backend python /app/upload_data.py
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### Manual Setup (Alternative)

If you prefer to run services manually:

#### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (using Docker)
docker run -d --name postgres -e POSTGRES_DB=dextrends_chatbot -e POSTGRES_USER=dextrends_user -e POSTGRES_PASSWORD=dextrends_password -p 5432:5432 postgres:15-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run database migrations
python -c "from backend.core.database import init_db; init_db()"

# Start the backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📚 API Documentation

Once the backend is running, you can access the API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔐 Authentication

The system uses JWT-based authentication. Here's how to use it:

### 1. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword123"
  }'
```

### 3. Use the Token

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 💬 Chat API Usage

### 1. Create a Session

```bash
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. Send a Message

```bash
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you tell me about Dextrends services?",
    "context": {}
  }'
```

### 3. Get Conversation History

```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations?session_id=YOUR_SESSION_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📊 Analytics

The system provides comprehensive analytics:

### User Analytics

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/user?days=30" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### System Analytics (Admin)

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/system?days=30" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🧪 Testing

### Backend Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest src/tests/ -v --cov=src

# Run with coverage report
pytest src/tests/ --cov=src --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

## 🚀 Deployment

### Production Deployment

1. **Environment Configuration**
   ```bash
   # Set production environment
   export ENVIRONMENT=production
   export DEBUG=false
   ```

2. **Database Migration**
   ```bash
   # Run migrations
   alembic upgrade head
   ```

3. **Build and Deploy**
   ```bash
   # Build Docker images
   docker-compose -f docker-compose.prod.yml build

   # Deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

## 📁 Project Structure

```
bluebelt_assignment/
├── src/                    # Backend source code
│   ├── api/               # API routes
│   ├── core/              # Core functionality
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   ├── tests/             # Test files
│   ├── config.py          # Configuration
│   └── main.py            # FastAPI application
├── frontend/              # Frontend application
│   ├── components/        # React components
│   ├── pages/             # Next.js pages
│   ├── styles/            # CSS styles
│   └── package.json       # Dependencies
├── docker-compose.yaml    # Docker services
├── Dockerfile             # Backend Dockerfile
├── requirements.txt       # Python dependencies
├── init.sql              # Database initialization
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `development` |
| `DEBUG` | Debug mode | `true` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `MEM0_API_KEY` | Mem0 API key | Optional |

### Database Configuration

The system uses PostgreSQL with the following schema:

- `users` - User accounts and profiles
- `sessions` - User sessions and context
- `conversations` - Chat messages and responses
- `analytics` - User interaction tracking

### Redis Configuration

Redis is used for:
- Session storage
- Rate limiting
- Response caching
- Token blacklisting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Contact the development team
- Check the documentation at `/docs`

## 🔄 Changelog

### Version 1.0.0
- Initial release
- Core chatbot functionality
- User authentication
- Analytics tracking
- Modern UI with OpenUI

---

**Built with ❤️ for Dextrends** 