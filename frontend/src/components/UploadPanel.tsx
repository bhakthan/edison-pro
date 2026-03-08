import { useState, useRef, useEffect, useCallback } from 'react';
import {
  CloudUpload, FileText, CheckCircle, Loader2,
  AlertCircle, FileImage, RefreshCw, MessageSquare, LayoutTemplate,
} from 'lucide-react';
import { api } from '../api/client';
import type { AnalysisStatus } from '../types';

interface UploadPanelProps {
  activeDocument: string | null;
  onDocumentReady: (filename: string) => void;
  onGoToChat: () => void;
  onGoToTemplates: () => void;
}

const ACCEPTED = '.pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp,.gif,.bmp';
const VALID_EXT = /\.(pdf|png|jpg|jpeg|tif|tiff|webp|gif|bmp)$/i;

export function UploadPanel({ activeDocument, onDocumentReady, onGoToChat, onGoToTemplates }: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<AnalysisStatus | null>(null);
  const [documents, setDocuments] = useState<string[]>([]);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadDocuments(); }, []);

  const loadDocuments = async () => {
    try {
      setDocuments(await api.listDocuments());
    } catch { /* backend may not have docs yet */ }
  };

  const handleFiles = async (selectedFiles: File[]) => {
    if (!selectedFiles.length) {
      return;
    }

    const invalidFiles = selectedFiles.filter((file) => !VALID_EXT.test(file.name));
    if (invalidFiles.length > 0) {
      setError('Unsupported file type. Please upload a PDF or image (PNG, JPG, TIFF, WebP, BMP).');
      return;
    }

    const pdfFiles = selectedFiles.filter((file) => /\.pdf$/i.test(file.name));
    const imageFiles = selectedFiles.filter((file) => !/\.pdf$/i.test(file.name));

    if (pdfFiles.length > 1) {
      setError('Upload one PDF at a time. Batch upload is supported for image sets only.');
      return;
    }

    if (pdfFiles.length === 1 && imageFiles.length > 0) {
      setError('Do not mix a PDF with images in the same upload. Upload either one PDF or a batch of images.');
      return;
    }

    setError('');
    setUploading(true);
    setProgress(0);
    setUploadStatus(null);
    try {
      const status = await api.uploadDocument(selectedFiles, (p) => setProgress(p));
      setUploadStatus(status);
      await loadDocuments();
      if (status.file_count && status.file_count > 1) {
        onDocumentReady(`${status.file_count} images`);
      } else {
        onDocumentReady(status.filename || selectedFiles[0].name);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files || []);
    if (droppedFiles.length > 0) handleFiles(droppedFiles);
  }, []);

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      handleFiles(selectedFiles);
      e.target.value = '';
    }
  };

  const isReady = !!uploadStatus || !!activeDocument;

  return (
    <div className="flex flex-col gap-8 max-w-3xl mx-auto py-10 px-4 w-full">

      {/* Page heading */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Upload Engineering Document</h2>
        <p className="text-gray-500 text-sm">
          Upload a PDF, image scan, or engineering drawing — Edison Pro will extract, index, and
          make it ready for AI-powered Q&amp;A and template analysis.
        </p>
      </div>

      {/* Active document notice */}
      {activeDocument && !uploadStatus && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-green-800">Document ready</p>
            <p className="text-xs text-green-600 truncate">{activeDocument}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onGoToChat}
              className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              Chat
            </button>
            <button
              onClick={onGoToTemplates}
              className="px-3 py-1.5 bg-green-600 text-white text-xs font-semibold rounded-lg hover:bg-green-700 transition-colors"
            >
              Templates
            </button>
          </div>
        </div>
      )}

      {/* Drop zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        aria-label="Upload file drop zone"
        className={`relative flex flex-col items-center justify-center gap-5 p-14 rounded-2xl border-2 border-dashed select-none transition-all duration-200 ${
          isDragging
            ? 'border-blue-500 bg-blue-50 scale-[1.01] cursor-copy'
            : uploading
            ? 'border-gray-300 bg-gray-50 cursor-wait'
            : uploadStatus
            ? 'border-green-400 bg-green-50 cursor-pointer'
            : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50 cursor-pointer'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          onChange={onFileInput}
          className="sr-only"
          aria-label="File upload input"
        />

        {uploading ? (
          <>
            <Loader2 className="w-14 h-14 text-blue-500 animate-spin" />
            <div className="text-center">
              <p className="text-lg font-semibold text-gray-800">Uploading &amp; analysing…</p>
              <p className="text-sm text-gray-500 mt-1">
                Edison Pro is extracting content from your upload
              </p>
            </div>
            <div className="w-64 bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-500 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-sm font-medium text-blue-600">{progress}%</span>
          </>
        ) : uploadStatus ? (
          <>
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle className="w-9 h-9 text-green-600" />
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-gray-900">Document ready!</p>
              <p className="text-sm text-gray-500 mt-1">{uploadStatus.message}</p>
              {uploadStatus.file_count && uploadStatus.file_count > 1 ? (
                <p className="text-xs text-gray-400 mt-2">
                  Batch contains {uploadStatus.file_count} images and produced {uploadStatus.chunks ?? 0} chunks.
                </p>
              ) : null}
            </div>
            <p className="text-xs text-gray-400">Click to upload another document</p>
          </>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-blue-100 flex items-center justify-center">
              <CloudUpload className="w-9 h-9 text-blue-600" />
            </div>
            <div className="text-center">
              <p className="text-xl font-semibold text-gray-800">
                {isDragging ? 'Drop to upload' : 'Drop your file(s) here'}
              </p>
              <p className="text-gray-500 mt-1 text-sm">or click to browse</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {['PDF', 'PNG', 'JPG', 'TIFF', 'WebP', 'BMP'].map((t) => (
                <span
                  key={t}
                  className="px-2.5 py-1 bg-gray-100 text-gray-600 text-xs font-semibold rounded-full border border-gray-200"
                >
                  {t}
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-400">
              Upload one PDF or a batch of related images for one combined analysis
            </p>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* CTA buttons after upload */}
      {isReady && (
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={onGoToChat}
            className="flex items-center justify-center gap-3 p-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all duration-200"
          >
            <MessageSquare className="w-5 h-5" />
            Chat with Document
          </button>
          <button
            onClick={onGoToTemplates}
            className="flex items-center justify-center gap-3 p-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl font-semibold hover:from-green-700 hover:to-emerald-700 shadow-lg hover:shadow-xl transition-all duration-200"
          >
            <LayoutTemplate className="w-5 h-5" />
            Run a Template
          </button>
        </div>
      )}

      {/* Previously analyzed documents */}
      {documents.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
              Previously Analysed
            </h3>
            <button
              onClick={loadDocuments}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
          <div className="space-y-2">
            {documents.map((doc, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-xl"
              >
                {/\.pdf$/i.test(doc) ? (
                  <FileText className="w-5 h-5 text-red-500 flex-shrink-0" />
                ) : (
                  <FileImage className="w-5 h-5 text-blue-500 flex-shrink-0" />
                )}
                <span className="text-sm text-gray-800 flex-1 truncate">{doc}</span>
                <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full border border-green-100">
                  Ready
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* How it works */}
      <div className="p-6 bg-gradient-to-br from-slate-50 to-blue-50 rounded-2xl border border-gray-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-5">
          How it works
        </h3>
        <div className="grid grid-cols-3 gap-6">
          {[
            {
              step: '1',
              title: 'Upload',
              desc: 'Drop your engineering PDF, P&ID schematic, or image scan',
            },
            {
              step: '2',
              title: 'Ask or Template',
              desc: 'Chat freely or pick a professional analysis template',
            },
            {
              step: '3',
              title: 'Export',
              desc: 'Download tables, charts, and complete analysis reports',
            },
          ].map((s) => (
            <div key={s.step} className="text-center">
              <div className="w-9 h-9 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold mx-auto mb-3 shadow-md">
                {s.step}
              </div>
              <p className="text-sm font-semibold text-gray-800">{s.title}</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
