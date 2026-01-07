# RAG Chatbot Frontend

React application for chatting with your documents using RAG (Retrieval-Augmented Generation).

## Features

- 📄 Upload PDF documents
- 💬 Chat interface with conversation history
- 🎨 Beautiful UI with Tailwind CSS
- 🔄 Real-time document management
- 📱 Responsive design

## Prerequisites

- Node.js 16+ and npm
- RAG API running on EC2 (http://56.228.16.40:8000)

## Installation

```bash
# Install dependencies
npm install
```

## Configuration

Update the API URL in `.env`:

```env
REACT_APP_API_URL=http://YOUR-EC2-PUBLIC-IP:8000
```

## Development

```bash
# Start development server
npm start
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build for Production

```bash
# Create production build
npm run build
```

The `build/` folder contains optimized files ready for deployment.

## Deployment to S3

```bash
# Build the app
npm run build

# Upload to S3 (replace bucket name)
aws s3 sync build/ s3://your-bucket-name --acl public-read

# Enable static website hosting
aws s3 website s3://your-bucket-name --index-document index.html
```

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── pages/
│   │   ├── DocumentsList.js   # Documents list page
│   │   └── Chat.js             # Chat interface
│   ├── services/
│   │   └── api.js              # API service (axios)
│   ├── App.js                  # Main app with routing
│   ├── index.js                # Entry point
│   └── index.css               # Tailwind CSS
├── package.json
├── tailwind.config.js
└── .env
```

## API Endpoints Used

- `GET /documents` - List all documents
- `POST /upload` - Upload new document
- `DELETE /documents/{doc_id}` - Delete document
- `POST /ask` - Ask question with conversation history

## Technologies

- **React 18** - UI library
- **React Router** - Navigation
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **Create React App** - Build tooling
