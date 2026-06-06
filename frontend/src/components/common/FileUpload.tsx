import React, { useRef, useState } from 'react';
import { Upload, X, File, Image as ImageIcon } from 'lucide-react';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  selectedFiles,
  onRemoveFile,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      validateAndAddFiles(filesArray);
    }
  };

  const validateAndAddFiles = (files: File[]) => {
    setError(null);
    const validFiles: File[] = [];
    const maxSizeBytes = 10 * 1024 * 1024; // 10MB limit
    const allowedExtensions = ['jpg', 'jpeg', 'png', 'pdf', 'mp4', 'mkv', 'avi'];

    for (const file of files) {
      const extension = file.name.split('.').pop()?.toLowerCase();
      if (!extension || !allowedExtensions.includes(extension)) {
        setError(`Invalid file type: ${file.name}. Allowed: JPG, PNG, PDF, MP4, AVI`);
        return;
      }
      if (file.size > maxSizeBytes) {
        setError(`File exceeds 10MB: ${file.name}`);
        return;
      }
      validFiles.push(file);
    }

    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  };

  const triggerSelect = () => {
    fileInputRef.current?.click();
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Upload Zone */}
      <div
        onClick={triggerSelect}
        className="border-2 border-dashed border-gov-border rounded-lg p-6 text-center cursor-pointer hover:border-gov-indigo bg-gov-light hover:bg-slate-100 transition-all"
      >
        <input
          type="file"
          ref={fileInputRef}
          multiple
          onChange={handleFileChange}
          className="hidden"
          accept=".jpg,.jpeg,.png,.pdf,.mp4,.mkv,.avi"
        />
        <Upload className="h-10 w-10 mx-auto text-gov-slate mb-2" />
        <p className="text-sm font-bold text-slate-800">Drag & Drop or Click to Upload Supporting Evidence</p>
        <p className="text-xs text-gov-slate mt-1">Accepted formats: PDF, JPG, PNG, MP4 (Max size: 10MB per file)</p>
      </div>

      {error && (
        <div className="text-xs font-bold text-red-600 bg-red-50 p-2.5 rounded border border-red-200">
          {error}
        </div>
      )}

      {/* Files List & Previews */}
      {selectedFiles.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {selectedFiles.map((file, idx) => {
            const isImage = file.type.startsWith('image/');
            const objectUrl = isImage ? URL.createObjectURL(file) : '';

            return (
              <div
                key={idx}
                className="flex items-center justify-between p-3 border border-slate-200 rounded-lg bg-white shadow-sm"
              >
                <div className="flex items-center space-x-3 overflow-hidden">
                  {isImage ? (
                    <img
                      src={objectUrl}
                      alt="preview"
                      className="h-10 w-10 object-cover rounded border border-slate-200"
                    />
                  ) : (
                    <div className="h-10 w-10 bg-slate-100 rounded flex items-center justify-center border border-slate-200 flex-shrink-0">
                      <File className="h-5 w-5 text-gov-slate" />
                    </div>
                  )}
                  <div className="truncate pr-2">
                    <p className="text-xs font-semibold text-slate-800 truncate">{file.name}</p>
                    <p className="text-[10px] text-gov-slate">{formatSize(file.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveFile(idx)}
                  className="p-1 hover:bg-red-50 text-slate-400 hover:text-red-600 rounded transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
export default FileUpload;
