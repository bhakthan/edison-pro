# EDISON PRO - Frontend

A modern TypeScript React frontend for EDISON PRO, an AI-powered electrical transformer data analysis system.

This frontend is part of the root EDISON PRO repository and inherits the project license and repository policies. See ../LICENSE, ../SECURITY.md, ../SUPPORT.md, and ../CODE_OF_CONDUCT.md.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## 🏗️ Architecture

### Tech Stack
- **React 18** - UI framework
- **TypeScript 5** - Type safety
- **Vite** - Build tool and dev server
- **Axios** - HTTP client for API calls
- **TanStack Query** - Data fetching and caching
- **Lucide React** - Icon library

### Project Structure
```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # API client with REST endpoints
│   ├── types/
│   │   └── index.ts           # TypeScript interfaces
│   ├── App.tsx                # Main chat interface
│   ├── App.css                # Modern gradient styling
│   └── main.tsx               # Application entry point
├── .env                       # Environment configuration
└── package.json
```

## 🔌 Backend Integration

### REST API Requirements

The frontend expects a REST API with these endpoints:

#### `POST /ask`
Ask a question about transformer data.

**Request:**
```json
{
  "question": "What is the average transformer rating?",
  "history": [
    ["Previous question", "Previous answer"]
  ]
}
```

**Response:**
```json
{
  "answer": "The average rating is 150 kVA",
  "sources": [
    {"title": "Transformer Data", "score": 0.95}
  ],
  "tables": [
    {
      "title": "Ratings",
      "data": [["ID", "Rating"], ["T001", "150"]]
    }
  ],
  "files": ["path/to/chart.html"],
  "charts": ["Chart data"],
  "code_executed": "df.mean()",
  "analysis_status": "Success"
}
```

#### `POST /upload`
Upload transformer data files.

**Request:** `multipart/form-data` with `file` field

**Response:**
```json
{
  "status": "success",
  "message": "File uploaded successfully"
}
```

#### `GET /status`
Check system health.

**Response:**
```json
{
  "status": "operational",
  "indexing_status": "idle",
  "document_count": 42
}
```

#### `GET /documents`
List indexed documents.

**Response:**
```json
{
  "documents": [
    {"filename": "data.csv", "upload_date": "2024-01-15"}
  ]
}
```

### Setting Up the Backend REST API

The Python backend currently uses Gradio (port 7861). You need to add a FastAPI wrapper:

**1. Install FastAPI:**
```bash
cd ..  # Go to parent directory
pip install fastapi uvicorn python-multipart
```

**2. Create `api_server.py`:**
```python
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Optional
import os

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    history: List[Tuple[str, str]] = []

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    # TODO: Call your existing ask_question function
    # from edisonpro_ui.py or code_agent_handler.py
    return {
        "answer": "Response from backend",
        "sources": [],
        "tables": [],
        "files": [],
        "charts": [],
        "code_executed": None,
        "analysis_status": "Success"
    }

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # TODO: Save and process uploaded file
    return {"status": "success", "message": f"Uploaded {file.filename}"}

@app.get("/status")
async def get_status():
    return {
        "status": "operational",
        "indexing_status": "idle",
        "document_count": 0
    }

@app.get("/documents")
async def list_documents():
    return {"documents": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7861)
```

**3. Run the API server:**
```bash
python api_server.py
```

### Environment Configuration

Edit `.env` to set the backend URL:

```env
VITE_API_URL=http://localhost:7861
```

## 🎨 Features

### Chat Interface
- **Message History**: Persistent conversation tracking
- **Auto-scroll**: Automatically scrolls to latest messages
- **Loading States**: Visual feedback during API calls
- **Error Handling**: Graceful error display

### Sample Questions
Quick access buttons for common queries:
- Average transformer rating
- Top 5 transformers by load
- Distribution across zones
- Chart visualizations

### Response Display
- **Markdown Formatting**: Rich text answers
- **Data Tables**: Interactive tabular data
- **File Downloads**: Access to generated reports
- **Chart Rendering**: Visual data representations
- **Code Execution**: Shows Python code used for analysis

### Modern UI/UX
- **Gradient Design**: Purple/pink theme with animations
- **Responsive Layout**: Works on desktop and mobile
- **Custom Scrollbars**: Styled for modern look
- **Loading Animations**: Pulse, float, and spin effects
- **Message Avatars**: User/assistant distinction

## 🔧 Development

### Available Scripts

```bash
# Development server with hot reload
npm run dev

# Type checking
npm run build

# Preview production build
npm run preview

# Linting
npm run lint
```

### TypeScript Types

All API interfaces are defined in `src/types/index.ts`:

```typescript
interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatResponse {
  answer: string;
  sources?: Source[];
  tables?: Table[];
  files?: string[];
  charts?: string[];
  code_executed?: string;
  analysis_status?: string;
}
```

### API Client Configuration

The Axios client in `src/api/client.ts` includes:
- **2-minute timeout** for o3-pro model processing
- **Progress tracking** for file uploads
- **Error interceptors** for debugging
- **Environment-based URLs** via VITE_API_URL

## 🚦 Testing Backend Connection

1. **Start Backend:**
   ```bash
   cd ..
   python api_server.py
   ```

2. **Start Frontend:**
   ```bash
   npm run dev
   ```

3. **Test in Browser:**
   - Open `http://localhost:5173`
   - Click a sample question
   - Check browser console for API calls
   - Verify CORS headers if errors occur

4. **Debug CORS Issues:**
   - Check `allow_origins` in FastAPI
   - Verify VITE_API_URL matches backend port
   - Check browser Network tab for preflight requests

## 📦 Production Build

```bash
# Build for production
npm run build

# Output will be in dist/ directory
# Serve with any static file server
```

### Deployment Options

1. **Static Hosting** (Vercel, Netlify, GitHub Pages):
   ```bash
   npm run build
   # Upload dist/ folder
   ```

2. **Docker**:
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   RUN npm run build
   EXPOSE 5173
   CMD ["npm", "run", "preview"]
   ```

3. **With Backend** (Nginx reverse proxy):
   - Frontend on `/` 
   - Backend API on `/api`

## 🔍 Troubleshooting

### "Cannot connect to backend"
- Check backend is running on correct port
- Verify VITE_API_URL in `.env`
- Check CORS configuration

### "Module not found" errors
- Run `npm install` to install dependencies
- Delete `node_modules` and reinstall if needed

### TypeScript errors
- Run `npm run build` to see all type errors
- Check `src/types/index.ts` for interface definitions

### Blank page in production
- Check browser console for errors
- Verify API_URL is set for production environment
- Check CORS headers from production backend

## 🤝 Integration with Python Backend

The frontend communicates with the existing EDISON PRO Python backend:

1. **Gradio UI** (port 7861): Original chat interface
2. **REST API** (port 7861): New FastAPI wrapper for frontend
3. **Azure AI Projects**: Code Agent for chart generation
4. **Azure AI Search**: Document retrieval and RAG

Both interfaces can run simultaneously on different ports if needed.

## 📝 Next Steps

- [ ] Implement FastAPI wrapper in `api_server.py`
- [ ] Connect frontend to REST endpoints
- [ ] Add file upload UI component
- [ ] Implement Plotly chart rendering
- [ ] Add authentication/authorization
- [ ] Configure production deployment
- [ ] Add E2E tests with Playwright

## 📄 License

Same as EDISON PRO parent project.
