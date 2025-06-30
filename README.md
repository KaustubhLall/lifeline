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
