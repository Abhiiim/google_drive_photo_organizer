# Google Drive Face Organizer

A FastAPI + React.js application that automatically organizes photos in Google Drive folders by detecting and grouping faces.

## Features

- Automatically detects faces in photos using face_recognition library
- Groups similar faces using clustering algorithms
- Creates person-based folders in Google Drive
- Handles group photos by creating shortcuts (no duplicates)
- Real-time progress tracking via React web interface

## Project Structure

```
face-organizer-app/
├── backend/                 # FastAPI backend
│   ├── app.py              # Main FastAPI application
│   ├── database.py         # SQLAlchemy models
│   ├── google_drive.py     # Google Drive API client
│   ├── face_detector.py    # Face detection logic
│   ├── photo_organizer.py  # Main organization logic
│   └── requirements.txt    # Python dependencies
├── frontend/               # React.js frontend
│   ├── public/
│   ├── src/
│   │   ├── App.js         # Main React component
│   │   ├── App.css        # Styling
│   │   ├── index.js       # React entry point
│   │   └── index.css      # Global styles
│   └── package.json       # Node.js dependencies
└── README.md
```

## Setup

### 1. Backend Setup

**Create and activate virtual environment:**

On macOS/Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

On Windows:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### 2. Database Setup

Create a PostgreSQL database and update the connection string in `backend/database.py`:

```python
DATABASE_URL = "postgresql://username:password@localhost/face_organizer"
```

### 3. Google Drive API Setup

**Step-by-step guide:**

1. **Go to Google Cloud Console**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Sign in with your Google account

2. **Create/Select Project**
   - Click project dropdown at top
   - Create new project or select existing one
   - Name it something like "Face Organizer"

3. **Enable Google Drive API**
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click on it and press "Enable"

4. **Configure OAuth Consent Screen** (if first time)
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "External" user type
   - Fill required fields (App name, support email, developer email)
   - Add your email to test users
   - Save and continue

5. **Create Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop application"
   - Name it "Face Organizer Desktop"
   - Click "Create"

6. **Download credentials.json**
   - Click "Download JSON" in the success dialog
   - Save as `credentials.json` in the `backend` folder
   - **Important**: Keep this file secure and don't commit to version control

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Run the Application

**Backend (Terminal 1):**
```bash
cd backend
# Make sure virtual environment is activated
source venv/bin/activate  # On macOS/Linux
# or venv\Scripts\activate on Windows
python app.py
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm start
```

The React app will be available at `http://localhost:3000`
The API will be available at `http://localhost:8000`

## API Endpoints

### POST /api/organize
Start photo organization process.

**Request:**
```json
{
  "drive_folder_link": "https://drive.google.com/drive/folders/your-folder-id"
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "processing"
}
```

### GET /api/status/{job_id}
Get organization progress status.

**Response:**
```json
{
  "status": "processing|completed|error",
  "message": "Current status message",
  "total_photos": 100,
  "processed": 50,
  "persons_found": 5,
  "folders_created": 6
}
```

## React Frontend Features

- Clean, modern UI with gradient background
- Real-time progress tracking with animated progress bar
- Responsive design for mobile and desktop
- Error handling with user-friendly messages
- Statistics display showing processing results
- Automatic status polling during processing

## How It Works

1. **Face Detection**: Uses face_recognition library to detect faces in all photos
2. **Clustering**: Groups similar faces using DBSCAN clustering algorithm
3. **Folder Creation**: Creates person folders (Person_1, Person_2, etc.) and No_Face_Detected folder
4. **Photo Organization**:
   - Single face photos: Moved to that person's folder
   - Multiple face photos: Original moved to first person's folder, shortcuts created in others
   - No face photos: Moved to No_Face_Detected folder

## Database Schema

### persons
- id: Primary key
- name: Person folder name (Person_1, Person_2, etc.)
- folder_id: Google Drive folder ID
- sample_face_path: Reference photo for this person

### photo_faces
- id: Primary key
- photo_name: Original photo filename
- photo_drive_id: Google Drive file ID
- person_ids: JSON array of person IDs found in photo
- is_original: Whether this is the original file location
- original_folder_id: Where the original file is stored

## Limitations

- Currently processes first 50 images for demo purposes (remove limit in production)
- Requires manual Google OAuth authentication on first run
- Face clustering accuracy depends on photo quality and lighting
- No person name customization in current version

## Production Considerations

- Use Redis for job tracking instead of in-memory storage
- Implement proper error handling and retry logic
- Add authentication and rate limiting
- Optimize face detection for large photo collections
- Add support for video files
- Implement face merging/splitting tools