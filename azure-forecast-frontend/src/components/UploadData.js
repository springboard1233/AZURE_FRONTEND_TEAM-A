import React, { useState } from 'react';
import axios from 'axios';

const UploadData = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files);
    setStatus('');
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setStatus('Please select a file first.');
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setStatus('✅ Upload successful!');
    } catch (error) {
      setStatus('❌ Upload failed: ' + error.response?.data?.error || error.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ margin: '2rem 0' }}>
      <h2>Upload Azure Data File</h2>
      <input type="file" accept=".csv,.xlsx" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={uploading} style={{ marginLeft: '1rem' }}>
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
      <span style={{ marginLeft: '1rem' }}>{status}</span>
    </div>
  );
};

export default UploadData;
