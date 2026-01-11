import React, { useState, useRef } from "react";
import Upload from "./components/Upload";
import Chat from "./components/Chat";

function App() {
  const [uploadedDoc, setUploadedDoc] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const uploadRef = useRef(null);

  const handleUploadClick = () => {
    if (uploadRef.current) {
      uploadRef.current.triggerUpload();
    }
  };

  const handleDocumentUploaded = (doc) => {
    setUploadedDoc(doc);
    setIsProcessing(false);
  };

  const handleUploadStart = () => {
    setIsProcessing(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-3/4 right-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-purple-500/5 to-blue-500/5 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>
      
      {/* Floating particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-purple-400/30 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 10}s`,
              animationDuration: `${10 + Math.random() * 20}s`
            }}
          />
        ))}
      </div>

      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Upload and Chat Actions Bar */}
        <div className="fixed top-6 right-6 z-50 flex space-x-3">
          {/* Upload Button */}
          <button
            onClick={handleUploadClick}
            disabled={isProcessing}
            className="group relative p-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white 
                     rounded-2xl shadow-lg transform transition-all duration-200 
                     hover:scale-105 hover:shadow-blue-500/25 active:scale-95
                     disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            <div className="relative">
              {isProcessing ? (
                <svg className="w-6 h-6 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              )}
            </div>
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl 
                         opacity-0 group-hover:opacity-20 group-hover:animate-pulse transition-opacity"></div>
          </button>

          {/* Document Status Indicator */}
          {isProcessing ? (
            <div className="flex items-center space-x-2 px-4 py-3 bg-yellow-500/10 backdrop-blur-sm 
                         border border-yellow-500/20 rounded-2xl text-yellow-400 text-sm font-medium">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
              <span>Processing...</span>
            </div>
          ) : uploadedDoc ? (
            <div className="flex items-center space-x-2 px-4 py-3 bg-green-500/10 backdrop-blur-sm 
                         border border-green-500/20 rounded-2xl text-green-400 text-sm font-medium">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>Document Ready</span>
            </div>
          ) : null}
        </div>

        {/* Header */}
        <div className="text-center mb-12 animate-in slide-in-from-top-6 duration-1000">
          <div className="inline-flex items-center space-x-3 mb-6">
            <div className="relative">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 via-pink-500 to-blue-500 rounded-2xl shadow-2xl flex items-center justify-center">
                <span className="text-2xl">📚</span>
              </div>
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500 via-pink-500 to-blue-500 rounded-2xl opacity-20 blur-xl animate-pulse"></div>
            </div>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-black mb-4">
            <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
              RAG Chatbot
            </span>
          </h1>
          
         
        </div>

        {/* Upload Section */}
        <div className="mb-8 animate-in slide-in-from-left-6 duration-1000 delay-300">
          <Upload 
            ref={uploadRef}
            onUploaded={handleDocumentUploaded}
            onUploadStart={handleUploadStart}
          />
        </div>

        {/* Connection Arrow */}
        <div className="flex justify-center mb-8 animate-in fade-in duration-1000 delay-500">
          <div className="relative">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-full 
                         flex items-center justify-center shadow-lg animate-bounce">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </div>
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-full 
                         opacity-20 animate-ping"></div>
          </div>
        </div>

        {/* Chat Section - Always visible */}
        <div className="animate-in slide-in-from-right-6 duration-1000 delay-700">
          <Chat uploadedDoc={uploadedDoc} />
        </div>

       

        {/* Footer */}
        <div className="mt-16 text-center animate-in fade-in duration-1000 delay-1000">
          <div className="text-slate-600 text-sm">
            Built with ❤️ using modern AI technologies
          </div>
        </div>
      </div>

      {/* Custom CSS for floating animation */}
      <style jsx>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0; }
          10%, 90% { opacity: 1; }
          50% { transform: translateY(-100px) rotate(180deg); opacity: 0.8; }
        }
        .animate-float {
          animation: float linear infinite;
        }
      `}</style>
    </div>
  );
}

export default App;