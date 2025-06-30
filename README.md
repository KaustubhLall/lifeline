# LifeLine - AI Assistant with Memory

LifeLine is an advanced AI conversational assistant that remembers important details about users across conversations. It features intelligent memory extraction, retrieval-augmented generation (RAG), multiple chat modes, and speech-to-text capabilities.

## 🌟 Features

### Core AI Capabilities
- **Multiple AI Models**: Support for GPT-4.1, GPT-4o, GPT-4o Mini, and GPT-4.1 Nano
- **Intelligent Memory System**: Automatic extraction and storage of user information from conversations
- **RAG (Retrieval-Augmented Generation)**: Semantic search and retrieval of relevant memories
- **Multiple Chat Modes**: Conversational, Coaching, Therapeutic, Productivity, and Creative modes
- **Speech-to-Text**: Real-time audio transcription with OpenAI Whisper

### Memory & Context Management
- **Automatic Memory Extraction**: LLM-powered extraction of personal information, preferences, goals, and insights
- **Semantic Memory Search**: Vector embeddings for intelligent memory retrieval
- **Memory Types**: Personal, Preferences, Goals, Insights, Facts, and Context
- **Conversation Continuity**: Maintains context across multiple conversations
- **Enhanced Prompting**: Dynamic prompt construction with memory context and conversation history

### User Interface
- **Responsive Design**: Mobile-first responsive interface
- **Real-time Chat**: Smooth conversation experience with typing indicators
- **Conversation Management**: Create, organize, and manage multiple conversations
- **Voice Input**: Speech-to-text integration with microphone support
- **User Authentication**: Secure login and registration system

## 🏗️ Architecture

### Backend (Django REST Framework)
```
backend/LifeLine/
├── api/
│   ├── models/
│   │   ├── user_auth.py      # User authentication model
│   │   └── chat.py           # Conversation, Message, Memory models
│   ├── views/
│   │   ├── login.py          # Authentication endpoints
│   │   └── views.py          # Main API endpoints
│   ├── utils/
│   │   ├── llm.py           # OpenAI API integration
│   │   ├── memory_utils.py   # Memory extraction and RAG
│   │   └── prompts.py        # Dynamic prompt generation
│   └── serializers.py        # API serializers
```

### Frontend (React)
```
frontend/src/
├── components/
│   ├── ChatInput.js          # Message input with STT
│   ├── ChatWindow.js         # Message display
│   ├── ChatSidebar.js        # Conversation list
│   ├── Header.js             # App header with controls
│   └── Auth components       # Login/Signup
├── hooks/
│   ├── useAuth.js            # Authentication state
│   ├── useConversations.js   # Chat management
│   ├── useSpeechToText.js    # STT functionality
│   └── useMobileLayout.js    # Responsive layout
└── pages/
    └── App.js                # Main application
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 14+
- OpenAI API key

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lifeline/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**
   Create a `.env` file in the backend directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   DJANGO_SECRET_KEY=your_django_secret_key
   DEBUG=True
   ```

5. **Database setup**
   ```bash
   cd LifeLine
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the server**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd lifeline/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure API endpoint**
   Update `src/config.js` with your backend URL:
   ```javascript
   const config = {
     API_URL: 'http://localhost:8000/api'
   };
   export default config;
   ```

4. **Run the development server**
   ```bash
   npm start
   ```

The application will be available at `http://localhost:3000`

## 🔧 Configuration

### AI Models
The application supports multiple OpenAI models:
- **GPT-4.1 Nano**: Fast, cost-effective for general conversations
- **GPT-4o Mini**: Balanced performance and cost
- **GPT-4o**: High-quality responses with multimodal capabilities
- **GPT-4.1**: Most advanced reasoning capabilities

### Chat Modes
- **Conversational**: General friendly conversation with memory
- **Coaching**: Goal-oriented coaching and personal development
- **Therapeutic**: Emotional support (not professional therapy)
- **Productivity**: Work efficiency and time management
- **Creative**: Creative projects and brainstorming

### Memory System
The AI automatically extracts and stores:
- **Personal Information**: Names, locations, relationships
- **Preferences**: Likes, dislikes, interests
- **Goals**: Objectives and aspirations
- **Insights**: Important learnings and realizations
- **Context**: Situational information for continuity

## 📊 Memory & RAG System

### Automatic Memory Extraction
- Uses GPT-4o Mini to analyze conversations
- Extracts memorable information with confidence scoring
- Generates vector embeddings for semantic search
- Tracks importance scores and access patterns

### Enhanced Retrieval
- **Semantic Search**: Cosine similarity matching
- **Context Reranking**: Dynamic relevance scoring
- **Multi-factor Scoring**: Combines similarity, importance, and recency
- **Conversation Memory**: Maintains session-specific context

### Memory Types & Scoring
- **Importance Score**: 0.0 to 1.0 based on significance
- **Access Tracking**: Frequency and recency of use
- **Confidence Scoring**: Auto-extraction reliability
- **Tag System**: Categorization and organization

## 🎙️ Speech-to-Text Features

### Audio Processing
- **Real-time Recording**: Browser-based audio capture
- **Format Support**: WebM, WAV, MP4, OGG
- **Quality Optimization**: Echo cancellation, noise suppression
- **Mobile Compatibility**: iOS and Android support

### Transcription
- **OpenAI Whisper**: High-accuracy speech recognition
- **Multiple Languages**: Automatic language detection
- **Error Handling**: Graceful fallback for unsupported browsers
- **Security**: HTTPS required for microphone access

## 🔐 Security & Privacy

### Authentication
- **Token-based Auth**: Secure API authentication
- **User Isolation**: Complete data separation between users
- **Session Management**: Automatic token refresh

### Data Protection
- **Encrypted Storage**: Secure database storage
- **API Security**: Rate limiting and input validation
- **Memory Privacy**: User-specific memory isolation
- **Audit Logging**: Comprehensive request logging

## 🛠️ API Endpoints

### Authentication
- `POST /api/register/` - User registration
- `POST /api/login/` - User login

### Conversations
- `GET /api/conversations/` - List conversations
- `POST /api/conversations/` - Create conversation
- `GET /api/conversations/{id}/` - Get conversation details
- `PATCH /api/conversations/{id}/` - Update conversation
- `DELETE /api/conversations/{id}/` - Delete conversation

### Messages
- `GET /api/conversations/{id}/messages/` - List messages
- `POST /api/conversations/{id}/messages/` - Send message

### Memory Management
- `GET /api/memories/` - List memories
- `POST /api/memories/` - Create memory
- `GET /api/memories/{id}/` - Get memory details
- `PATCH /api/memories/{id}/` - Update memory
- `DELETE /api/memories/{id}/` - Delete memory

### Audio Processing
- `POST /api/transcribe/` - Transcribe audio to text

## 🔍 Advanced Features

### Enhanced Prompt Engineering
- **Dynamic System Prompts**: Mode-specific instructions
- **Memory Integration**: Contextual memory insertion
- **Conversation History**: Token-aware history management
- **User Personalization**: Name and preference integration

### Performance Optimization
- **Background Processing**: Async memory extraction
- **Token Counting**: Efficient context management
- **Caching**: Memory and conversation caching
- **Pagination**: Efficient data loading

### Error Handling
- **Budget Management**: API quota monitoring
- **Model Fallbacks**: Graceful model switching
- **Network Resilience**: Retry mechanisms
- **User Feedback**: Clear error messages

## 🎨 Customization

### Adding New Chat Modes
1. Add mode to `SYSTEM_PROMPTS` in `utils/prompts.py`
2. Update frontend `chatModes` array in `App.js`
3. Implement mode-specific logic if needed

### Memory Types
Extend the `MEMORY_TYPES` in `models/chat.py`:
```python
MEMORY_TYPES = [
    ('personal', 'Personal Information'),
    ('preference', 'User Preference'),
    ('goal', 'Goal or Objective'),
    # Add your custom types here
]
```

## 📈 Monitoring & Analytics

### Logging
- **Comprehensive Logging**: All API calls and errors
- **Memory Tracking**: Extraction and retrieval metrics
- **Performance Monitoring**: Response times and token usage
- **User Activity**: Conversation and memory patterns

### Metrics
- **Memory Statistics**: Extraction success rates
- **Model Performance**: Response quality metrics
- **Usage Patterns**: User engagement analytics
- **Error Rates**: System reliability monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing the GPT models and Whisper API
- Django REST Framework for the robust backend framework
- React for the dynamic frontend framework
- The open-source community for various libraries and tools

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Check the documentation
- Review the code comments for implementation details

---

**LifeLine** - Where AI remembers, understands, and grows with you.

## 🚀 Deployment

### Prerequisites

Before deploying, ensure you have:
- AWS EC2 instance running Amazon Linux 2
- GitHub repository with your code
- Required GitHub Secrets configured
- Domain name or public IP address

### GitHub Secrets Setup

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `EC2_SSH_PRIVATE_KEY` | Your EC2 private key (.pem file content) | `-----BEGIN RSA PRIVATE KEY-----...` |
| `EC2_HOSTNAME` | Your EC2 public IP address | `54.144.219.238` |
| `EC2_USER_NAME` | EC2 username (usually `ec2-user`) | `ec2-user` |
| `DJANGO_SECRET_KEY` | Django secret key for production | `your-secret-key-here` |
| `OPENAI_API_KEY` | OpenAI API key for AI features | `sk-...` |

### Deployment Methods

#### Method 1: Manual Trigger (Recommended)

1. **Go to GitHub Actions**:
   - Navigate to your repository on GitHub
   - Click the **Actions** tab
   - Select **Deploy to EC2** workflow

2. **Click "Run workflow"**:
   - Click the **Run workflow** button
   - Choose the branch you want to deploy from the dropdown
   - Click **Run workflow** to start deployment

3. **Monitor Progress**:
   - Watch the real-time logs in the Actions tab
   - Each step will show progress and any errors

#### Method 2: Automatic Deployment

The workflow automatically triggers on:
- **Push to main branch**: `git push origin main`
- **Push to develop branch**: `git push origin develop`
- **Pull requests to main**: When you create a PR targeting main

### Deployment Process

The automated deployment performs these steps:

1. **Build Phase**:
   - Installs Node.js and Python dependencies
   - Builds React frontend for production
   - Runs backend tests (optional)

2. **Deploy Phase**:
   - Copies files to your EC2 instance via SSH
   - Sets up Python virtual environment
   - Configures Nginx web server
   - Creates systemd service for Django backend
   - Applies database migrations

3. **Health Check**:
   - Verifies frontend is accessible
   - Tests backend API endpoints
   - Confirms all services are running

### Post-Deployment

After successful deployment, your application will be available at:

- **Frontend**: `http://your-ec2-ip/`
- **Backend API**: `http://your-ec2-ip/api/`
- **Health Check**: `http://your-ec2-ip/api/health/`
- **Django Admin**: `http://your-ec2-ip/admin/`

### Troubleshooting Deployment

#### Common Issues

1. **SSH Connection Failed**:
   ```bash
   # Check your private key format
   # Ensure EC2 security group allows SSH (port 22)
   # Verify the hostname/IP is correct
   ```

2. **Frontend Build Errors**:
   ```bash
   # Ensure package.json and package-lock.json are committed
   # Check Node.js version compatibility
   ```

3. **Backend Service Issues**:
   ```bash
   # SSH into your EC2 instance to check logs:
   ssh -i your-key.pem ec2-user@your-ip
   sudo journalctl -u lifeline-backend -f
   ```

4. **Nginx Configuration**:
   ```bash
   # Check Nginx status and logs:
   sudo systemctl status nginx
   sudo tail -f /var/log/nginx/error.log
   ```

#### Manual Deployment Verification

SSH into your EC2 instance and run:

```bash
# Check backend service
sudo systemctl status lifeline-backend

# Check nginx service
sudo systemctl status nginx

# Test backend API directly
curl http://localhost:8000/api/health/

# Test frontend
curl http://localhost/
```

### Updating Your Deployment

To deploy updates:

1. **Push changes** to your repository
2. **Trigger deployment** using GitHub Actions
3. The system will automatically:
   - Stop existing services
   - Backup current deployment
   - Install new version
   - Restart services

### Rollback Procedure

If deployment fails, you can rollback:

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ec2-user@your-ip

# List available backups
ls -la /home/ec2-user/lifeline/backup-*

# Restore from backup (replace with actual backup timestamp)
sudo systemctl stop lifeline-backend nginx
sudo mv /home/ec2-user/lifeline/current /home/ec2-user/lifeline/failed-deployment
sudo mv /home/ec2-user/lifeline/backup-YYYYMMDD_HHMMSS /home/ec2-user/lifeline/current
sudo systemctl start lifeline-backend nginx
```

### Local Development Setup

For local development without deployment:

1. **Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   cd LifeLine
   python manage.py migrate
   python manage.py runserver
   ```

2. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Environment Variables**:
   Create `.env` file in backend/LifeLine/:
   ```
   DJANGO_SECRET_KEY=your-dev-secret-key
   OPENAI_API_KEY=your-openai-key
   DEBUG=True
   ```
