import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = process.env.NODE_ENV === 'production'
  ? 'https://your-api-domain.com'
  : 'http://localhost:8000';

function App() {
  const [folderLink, setFolderLink] = useState('');
  const [currentJobId, setCurrentJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let interval;
    if (currentJobId && isProcessing) {
      interval = setInterval(checkStatus, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentJobId, isProcessing]);

  const startOrganization = async () => {
    if (!folderLink.trim()) {
      alert('Please enter a Google Drive folder link');
      return;
    }

    setError(null);
    setIsProcessing(true);
    setStatus({
      status: 'processing',
      message: 'Starting organization...',
      total_photos: 0,
      processed: 0,
      persons_found: 0,
      folders_created: 0
    });

    try {
      const response = await axios.post(`${API_BASE}/api/organize`, {
        drive_folder_link: folderLink
      });

      setCurrentJobId(response.data.job_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start organization');
      setIsProcessing(false);
    }
  };

  const checkStatus = async () => {
    if (!currentJobId) return;

    try {
      const response = await axios.get(`${API_BASE}/api/status/${currentJobId}`);
      const statusData = response.data;

      setStatus(statusData);

      if (statusData.status === 'completed') {
        setIsProcessing(false);
      } else if (statusData.status === 'error') {
        setError(statusData.message);
        setIsProcessing(false);
      }
    } catch (err) {
      setError('Failed to get status');
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setFolderLink('');
    setCurrentJobId(null);
    setStatus(null);
    setIsProcessing(false);
    setError(null);
  };

  const getProgressPercentage = () => {
    if (!status || status.total_photos === 0) return 0;
    return Math.round((status.processed / status.total_photos) * 100);
  };

  return (
    <div className="container">
      <div className="card">
        <h1>Google Drive Face Organizer</h1>
        <p>Organize your photos by faces automatically</p>

        {!isProcessing && !status && (
          <div className="form-section">
            <label htmlFor="folderLink">Google Drive Folder Link:</label>
            <input
              type="text"
              id="folderLink"
              value={folderLink}
              onChange={(e) => setFolderLink(e.target.value)}
              placeholder="https://drive.google.com/drive/folders/your-folder-id"
              disabled={isProcessing}
            />
            <button
              onClick={startOrganization}
              disabled={isProcessing || !folderLink.trim()}
              className="primary-button"
            >
              Start Organization
            </button>
          </div>
        )}

        {isProcessing && status && (
          <div className="status-section">
            <h3>Processing Status</h3>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${getProgressPercentage()}%` }}
              ></div>
            </div>
            <p className="status-message">{status.message}</p>
            <div className="stats">
              <span>Photos: {status.total_photos || 0}</span>
              <span>Processed: {status.processed || 0}</span>
              <span>Faces: {status.faces_detected || 0}</span>
              <span>Persons: {status.persons_found || 0}</span>
            </div>
            {status.multi_face_summary && (
              <div className="multi-face-stats">
                <small>
                  Single: {status.multi_face_summary.single_face_photos || 0} |
                  Multi: {status.multi_face_summary.multi_face_photos || 0} |
                  No Face: {status.multi_face_summary.no_face_photos || 0}
                </small>
              </div>
            )}
          </div>
        )}

        {!isProcessing && status && status.status === 'completed' && (
          <div className="result-section">
            <h3>Organization Complete!</h3>
            <p>Your photos have been organized by faces.</p>
            <div className="final-stats">
              <div className="stat-item">
                <strong>{status.total_photos}</strong>
                <span>Photos Processed</span>
              </div>
              <div className="stat-item">
                <strong>{status.persons_found}</strong>
                <span>Persons Found</span>
              </div>
              <div className="stat-item">
                <strong>{status.faces_detected}</strong>
                <span>Faces Detected</span>
              </div>
            </div>
            {status.multi_face_summary && (
              <div className="detailed-stats">
                <h4>Photo Breakdown:</h4>
                <div className="breakdown-stats">
                  <div className="breakdown-item">
                    <strong>{status.multi_face_summary.single_face_photos}</strong>
                    <span>Single Face Photos</span>
                  </div>
                  <div className="breakdown-item">
                    <strong>{status.multi_face_summary.multi_face_photos}</strong>
                    <span>Multi Face Photos</span>
                  </div>
                  <div className="breakdown-item">
                    <strong>{status.multi_face_summary.no_face_photos}</strong>
                    <span>No Face Photos</span>
                  </div>
                </div>
              </div>
            )}
            <button onClick={resetForm} className="secondary-button">
              Organize Another Folder
            </button>
          </div>
        )}

        {error && (
          <div className="error-section">
            <h3>Error</h3>
            <p>{error}</p>
            <button onClick={resetForm} className="secondary-button">
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;