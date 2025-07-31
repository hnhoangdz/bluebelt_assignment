# Dextrends AI Frontend

A modern React frontend for the Dextrends AI Chatbot with a ChatGPT-like interface.

## Features

- 🔐 **Authentication**: Login and registration with JWT tokens
- 💬 **Chat Interface**: ChatGPT-like chat interface with conversation history
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🎨 **Modern UI**: Clean, modern design with smooth animations
- 🔄 **Real-time Updates**: Live message updates and typing indicators
- 📂 **Conversation Management**: Create, switch, and delete conversations

## Tech Stack

- **React 18** with TypeScript
- **React Router** for navigation
- **Axios** for API communication
- **Lucide React** for icons
- **CSS3** for styling

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running on port 8000

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   Create a `.env` file in the frontend directory:
   ```bash
   REACT_APP_API_URL=http://localhost:8000
   ```

3. **Start development server:**
   ```bash
   npm start
   ```

4. **Open your browser:**
   Navigate to `http://localhost:3000`

### Development

- **Start development server:** `npm start`
- **Build for production:** `npm run build`
- **Run tests:** `npm test`

## Project Structure

```
frontend/
├── public/
├── src/
│   ├── contexts/
│   │   └── AuthContext.tsx      # Authentication context
│   ├── pages/
│   │   ├── LoginPage.tsx        # Login page
│   │   ├── RegisterPage.tsx     # Registration page
│   │   ├── ChatbotPage.tsx      # Main chat interface
│   │   ├── AuthPages.css        # Auth pages styling
│   │   └── ChatbotPage.css      # Chat interface styling
│   ├── App.tsx                  # Main app component
│   ├── App.css                  # Global styles
│   └── index.tsx                # App entry point
├── Dockerfile                   # Docker configuration
├── nginx.conf                   # Nginx configuration
└── package.json
```

## Features in Detail

### Authentication

- **Login Page**: Username/password authentication
- **Register Page**: User registration with validation
- **JWT Token Management**: Automatic token storage and refresh
- **Protected Routes**: Route protection based on authentication status

### Chat Interface

- **Conversation Sidebar**: List of all conversations with management
- **Message Display**: User and AI messages with timestamps
- **Real-time Input**: Auto-expanding textarea with Enter to send
- **Loading States**: Typing indicators and loading spinners
- **Error Handling**: Graceful error display and recovery

### Conversation Management

- **New Chat**: Create new conversations
- **Switch Conversations**: Click to switch between conversations
- **Delete Conversations**: Remove conversations with confirmation
- **Auto-save**: Messages are automatically saved to the backend

## API Integration

The frontend communicates with the backend API endpoints:

- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user info
- `GET /api/v1/chat/conversations` - Get user conversations
- `POST /api/v1/chat/send` - Send a message
- `DELETE /api/v1/chat/conversations/:id` - Delete conversation

## Styling

The application uses modern CSS with:

- **Flexbox Layout**: Responsive and flexible layouts
- **CSS Grid**: For complex layouts
- **CSS Variables**: For consistent theming
- **Smooth Animations**: Transitions and hover effects
- **Mobile-First**: Responsive design approach

## Docker Deployment

### Build and Run

1. **Build the image:**
   ```bash
   docker build -t dextrends-frontend .
   ```

2. **Run the container:**
   ```bash
   docker run -p 3000:3000 dextrends-frontend
   ```

### Docker Compose

The frontend is included in the main `docker-compose.yaml`:

```bash
docker-compose up frontend
```

## Development Workflow

1. **Start the backend API** (port 8000)
2. **Start the frontend** (port 3000)
3. **Make changes** to React components
4. **Hot reload** will automatically update the browser
5. **Test features** in the browser

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the Dextrends AI Chatbot application.
