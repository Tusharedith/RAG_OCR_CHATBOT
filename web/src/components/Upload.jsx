// client/src/components/Upload.js
import React, { useState } from "react";
import axios from "axios";

function Upload({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setStatus("Uploading...");
      const res = await axios.post("http://localhost:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setStatus(`✅ Uploaded (${res.data.num_chunks} chunks)`);
      onUploaded(res.data);
    } catch (err) {
      console.error(err);
      setStatus("❌ Upload failed");
    }
  };

  const getStatusIcon = () => {
    if (status.includes("Uploading")) {
      return (
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-100"></div>
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-200"></div>
        </div>
      );
    }
    return null;
  };

  const getFileIcon = (fileName) => {
    if (!fileName) return null;
    
    const extension = fileName.split('.').pop().toLowerCase();
    
    if (['pdf'].includes(extension)) {
      return (
        <svg className="w-6 h-6 text-red-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M7.07,18.28C7.5,17.38 8.12,16.19 8.93,14.76C10.04,15.5 11.25,16.05 12.5,16.34C11.94,16.85 11.36,17.3 10.75,17.68C9.64,18.34 8.33,18.68 7.07,18.28M8.93,9.76C8.12,8.33 7.5,7.14 7.07,6.24C8.33,5.84 9.64,6.18 10.75,6.84C11.36,7.22 11.94,7.67 12.5,8.18C11.25,8.47 10.04,9.02 8.93,9.76Z"/>
        </svg>
      );
    } else if (['doc', 'docx'].includes(extension)) {
      return (
        <svg className="w-6 h-6 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
        </svg>
      );
    } else if (['txt'].includes(extension)) {
      return (
        <svg className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
        </svg>
      );
    }
    
    return (
      <svg className="w-6 h-6 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
      </svg>
    );
  };

  return (
    <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 
                  rounded-2xl shadow-2xl border border-blue-500/20 backdrop-blur-sm">
      {/* Animated background elements */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.15),transparent)] animate-pulse"></div>
      <div className="absolute -top-4 -right-4 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl animate-pulse"></div>
      <div className="absolute -bottom-4 -left-4 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl animate-pulse delay-1000"></div>
      
      <div className="relative p-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-teal-400 bg-clip-text text-transparent mb-2">
            Document Upload
          </h2>
          <p className="text-slate-400">Upload documents to build your knowledge base</p>
        </div>

        {/* Upload Zone */}
        <div className="relative mb-6">
          <input
            type="file"
            id="file-upload"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            onChange={(e) => setFile(e.target.files[0])}
            accept=".pdf,.doc,.docx,.txt"
          />
          
          <div className={`relative overflow-hidden border-2 border-dashed rounded-xl p-8 transition-all duration-300 ${
            file 
              ? 'border-green-400/50 bg-green-500/5' 
              : 'border-white/20 bg-white/5 hover:border-blue-400/50 hover:bg-white/10'
          }`}>
            <div className="text-center">
              {file ? (
                <div className="space-y-4 animate-in slide-in-from-bottom-4 duration-500">
                  <div className="flex justify-center">
                    <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-500 
                                 rounded-xl flex items-center justify-center shadow-lg">
                      {getFileIcon(file.name)}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-1">File Selected</h3>
                    <p className="text-green-400 font-medium">{file.name}</p>
                    <p className="text-slate-400 text-sm mt-1">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-cyan-500 
                                 rounded-xl flex items-center justify-center shadow-lg">
                      <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">
                      Drop your file here or click to browse
                    </h3>
                    <p className="text-slate-400 text-sm">
                      Supports PDF, DOC, DOCX, TXT files up to 50MB
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Upload Button */}
        <div className="flex justify-center mb-6">
          <button
            onClick={handleUpload}
            disabled={!file || status.includes("Uploading")}
            className="group relative px-8 py-4 bg-gradient-to-r from-blue-500 to-cyan-500 
                     text-white font-semibold rounded-xl shadow-lg transform transition-all duration-200 
                     hover:scale-105 hover:shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed
                     disabled:hover:scale-100 active:scale-95"
          >
            <div className="flex items-center space-x-3">
              {status.includes("Uploading") ? (
                <>
                  <div className="w-5 h-5">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  </div>
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  <span>Upload Document</span>
                </>
              )}
            </div>
            
            {/* Button glow effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl 
                         opacity-0 group-hover:opacity-20 group-hover:animate-pulse transition-opacity"></div>
          </button>
        </div>

        {/* Status Display */}
        {status && (
          <div className={`animate-in slide-in-from-bottom-4 duration-500 relative overflow-hidden 
                         ${status.includes('✅') ? 'bg-green-500/10 border-green-500/20' : 
                           status.includes('❌') ? 'bg-red-500/10 border-red-500/20' : 
                           'bg-blue-500/10 border-blue-500/20'} 
                         border rounded-xl p-6`}>
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                {status.includes('✅') ? (
                  <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-500 
                               rounded-lg flex items-center justify-center shadow-lg">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                ) : status.includes('❌') ? (
                  <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-pink-500 
                               rounded-lg flex items-center justify-center shadow-lg">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 
                               rounded-lg flex items-center justify-center shadow-lg">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  </div>
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className={`font-semibold ${
                    status.includes('✅') ? 'text-green-400' : 
                    status.includes('❌') ? 'text-red-400' : 'text-blue-400'
                  }`}>
                    {status}
                  </span>
                  {getStatusIcon()}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Supported Formats */}
        <div className="mt-6 pt-6 border-t border-white/10">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Supported Formats</h4>
          <div className="flex flex-wrap gap-2">
            {['PDF', 'DOC', 'DOCX', 'TXT'].map((format) => (
              <span key={format} 
                    className="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-400 font-medium">
                {format}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Upload;