import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  Image as ImageIcon, 
  Trash2, 
  AlertCircle, 
  CheckCircle2, 
  Info,
  Paperclip
} from 'lucide-react';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB per file
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpg'
];
const ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png'];

export default function MedicalDocumentUpload({ 
  attachments = [], 
  onChangeAttachments 
}) {
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const fileInputRef = useRef(null);

  // Helper to format bytes to human readable string
  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  // Helper to validate a single file
  const validateFile = (file) => {
    // 1. Extension / MIME check
    const extension = `.${file.name.split('.').pop().toLowerCase()}`;
    const isMimeValid = ALLOWED_MIME_TYPES.includes(file.type);
    const isExtValid = ALLOWED_EXTENSIONS.includes(extension);

    if (!isMimeValid && !isExtValid) {
      return `"${file.name}" has an unsupported format. Only PDF, JPG, JPEG, and PNG files are accepted.`;
    }

    // 2. Size check
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      return `"${file.name}" exceeds the 10 MB limit (${sizeMB} MB). Please choose a smaller file.`;
    }

    // 3. Duplicate filename check
    const isDuplicate = attachments.some(
      existing => existing.name === file.name && existing.size === file.size
    );
    if (isDuplicate) {
      return `"${file.name}" is already attached.`;
    }

    return null;
  };

  // Process newly selected or dropped files
  const handleFiles = (fileList) => {
    setValidationError(null);
    if (!fileList || fileList.length === 0) return;

    const newValidFiles = [];
    let firstError = null;

    Array.from(fileList).forEach((file) => {
      const error = validateFile(file);
      if (error) {
        if (!firstError) firstError = error;
      } else {
        newValidFiles.push({
          id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
          name: file.name,
          size: file.size,
          formattedSize: formatFileSize(file.size),
          type: file.type || 'application/octet-stream',
          isPdf: file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf',
          fileObject: file
        });
      }
    });

    if (firstError) {
      setValidationError(firstError);
    }

    if (newValidFiles.length > 0) {
      onChangeAttachments([...attachments, ...newValidFiles]);
    }

    // Reset input value to allow re-selecting same file if removed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleRemoveFile = (fileId) => {
    onChangeAttachments(attachments.filter(f => f.id !== fileId));
    setValidationError(null);
  };

  return (
    <div className="medical-upload-section" aria-labelledby="upload-section-title">
      {/* Header */}
      <div className="upload-header-row">
        <div className="upload-title-box">
          <Paperclip size={20} className="upload-title-icon" aria-hidden="true" />
          <div>
            <h3 id="upload-section-title" className="upload-main-title">
              Attach Medical Reports <span className="upload-optional-tag">(Optional)</span>
            </h3>
            <p className="upload-subtitle">
              Upload prescriptions or medical reports to help the medical team understand the patient's condition, if available.
            </p>
          </div>
        </div>
      </div>

      {/* Drop Zone Area */}
      <div 
        className={`upload-dropzone ${dragActive ? 'dropzone-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <UploadCloud size={32} className="dropzone-cloud-icon" aria-hidden="true" />
        <div className="dropzone-text-group">
          <p className="dropzone-primary-text">
            Drag & drop files here, or{' '}
            <button
              type="button"
              className="dropzone-browse-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              browse from device
            </button>
          </p>
          <p className="dropzone-hint-text">
            Accepted formats: <strong>PDF, JPG, JPEG, PNG</strong> • Max <strong>10 MB</strong> per file
          </p>
        </div>

        {/* Hidden standard file picker */}
        <input 
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          onChange={(e) => handleFiles(e.target.files)}
          style={{ display: 'none' }}
          aria-label="Upload medical documents"
        />
      </div>

      {/* Validation Error Banner */}
      {validationError && (
        <div className="upload-error-banner" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{validationError}</span>
        </div>
      )}

      {/* List of Attached Files */}
      {attachments.length > 0 && (
        <div className="attached-files-list" aria-label="Attached medical reports">
          <div className="attached-count-heading">
            <CheckCircle2 size={15} color="#059669" aria-hidden="true" />
            <span>{attachments.length} {attachments.length === 1 ? 'file' : 'files'} attached locally:</span>
          </div>

          <div className="attached-files-grid">
            {attachments.map((file) => (
              <div key={file.id} className="attached-file-card">
                <div className="file-icon-box" aria-hidden="true">
                  {file.isPdf ? (
                    <FileText size={22} className="file-icon-pdf" />
                  ) : (
                    <ImageIcon size={22} className="file-icon-img" />
                  )}
                </div>

                <div className="file-meta-box">
                  <div className="file-name" title={file.name}>{file.name}</div>
                  <div className="file-size-type">
                    <span>{file.formattedSize}</span>
                    <span>•</span>
                    <span className="file-type-pill">{file.isPdf ? 'PDF' : 'IMAGE'}</span>
                  </div>
                </div>

                <button
                  type="button"
                  className="btn-remove-attachment"
                  onClick={() => handleRemoveFile(file.id)}
                  aria-label={`Remove ${file.name}`}
                  title="Remove file"
                >
                  <Trash2 size={16} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Implementation Transparency Disclaimer */}
      <div className="upload-integration-notice">
        <Info size={14} aria-hidden="true" />
        <span>
          <strong>Phase 2 Local Attachment:</strong> Files are validated and included in your local triage session. Persistent hospital document storage will be connected in Phase 3.
        </span>
      </div>
    </div>
  );
}
