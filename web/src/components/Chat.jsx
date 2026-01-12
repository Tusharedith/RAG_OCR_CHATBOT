import React, { useState, useEffect } from "react";
import axios from "axios";

function Chat({ uploadedDoc }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState([]);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [chatMode, setChatMode] = useState('general');

  useEffect(() => {
    setChatMode(uploadedDoc ? 'document' : 'general');
    if (answer) {
      setAnswer("");
      setCitations([]);
    }
  }, [uploadedDoc]);

  const askQuestion = async () => {
    if (!question.trim()) return;
    
    setIsLoading(true);
    setAnswer("⏳ Thinking...");
    setCitations([]);
    setSelectedCitation(null);

    try {
      let response;
      
      if (chatMode === 'document' && uploadedDoc) {
        response = await axios.post("http://localhost:8000/query", {
          question: question,
          document_id: uploadedDoc.document_id,
          top_k: 5
        });
        setAnswer(response.data.answer);
        const citationsData = response.data.citations || [];
        console.log("Received citations:", citationsData);
        setCitations(citationsData);
      } else {
        response = await axios.post("http://localhost:8000/query", {
          question: question,
          document_id: uploadedDoc?.document_id || "default",
          top_k: 5
        });
        setAnswer(response.data.answer);
        setCitations([]);
      }
    } catch (err) {
      console.error(err);
      setAnswer("❌ Error getting answer. Please try again.");
      setCitations([]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderAnswerWithCitations = (text) => {
    if (!text) return text;
    if (citations.length === 0) return text;
    
    const parts = text.split(/(🔗\d+)/g);
    
    return parts.map((part, index) => {
      const citationMatch = part.match(/🔗(\d+)/);
      
      if (citationMatch) {
        const citationId = part;
        const citation = citations.find(c => {
          if (c.id === citationId) return true;
          const numMatch = citationId.match(/🔗(\d+)/);
          if (numMatch) {
            const num = numMatch[1];
            return c.id === `🔗${num}` || c.id === num || c.id === `cite_${num}`;
          }
          return false;
        });
        
        if (citation) {
          return (
            <button
              key={index}
              onClick={() => setSelectedCitation(citation)}
              className="inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-medium rounded 
                       bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 hover:text-purple-200
                       border border-purple-500/30 hover:border-purple-500/50
                       transition-all duration-200 cursor-pointer transform hover:scale-105"
              title={citation.label || citation.modality || `Source ${index + 1}`}
            >
              {citationId}
            </button>
          );
        } else {
          console.warn(`Citation marker ${citationId} found but no matching citation in array:`, citations);
        }
      }
      
      return <span key={index}>{part}</span>;
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      askQuestion();
    }
  };

  return (
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 rounded-2xl shadow-2xl border border-purple-500/20 backdrop-blur-sm">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(120,119,198,0.15),transparent)] animate-pulse"></div>
      <div className="absolute -top-4 -right-4 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl animate-pulse"></div>
      <div className="absolute -bottom-4 -left-4 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl animate-pulse delay-1000"></div>
      
      <div className="relative p-8">
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
              AI Assistant
            </h2>
            
            <div className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-300 ${
              chatMode === 'document' 
                ? 'bg-green-500/10 border-green-500/30 text-green-400' 
                : 'bg-blue-500/10 border-blue-500/30 text-blue-400'
            }`}>
              {chatMode === 'document' ? 'Document Mode' : 'General Chat'}
            </div>
          </div>
          
          <p className="text-slate-400">
            {chatMode === 'document' 
              ? 'Ask me anything about your uploaded document'
              : 'Ask me anything and I\'ll help you out'
            }
          </p>
        </div>

        <div className="relative mb-6">
          <textarea
            className="w-full p-6 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl 
                     text-white placeholder-slate-400 resize-none transition-all duration-300
                     focus:border-purple-400/50 focus:ring-2 focus:ring-purple-400/20 focus:bg-white/10
                     hover:border-white/20 hover:bg-white/[0.07]"
            rows="4"
            placeholder={
              chatMode === 'document' 
                ? "Ask me about your document... What would you like to know?"
                : "Type your message here... I'm ready to help!"
            }
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          
          <button
            onClick={askQuestion}
            disabled={!question.trim() || isLoading}
            className="absolute bottom-4 right-4 group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="relative">
              <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full 
                           flex items-center justify-center shadow-lg transform transition-all duration-200 
                           group-hover:scale-110 group-hover:shadow-purple-500/50 group-active:scale-95
                           group-disabled:hover:scale-100">
                {isLoading ? (
                  <svg className="w-5 h-5 text-white animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </div>
              {!isLoading && (
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full 
                             opacity-0 group-hover:opacity-20 group-hover:animate-ping"></div>
              )}
            </div>
          </button>

          <div className="absolute -bottom-6 right-0 text-xs text-slate-500">
            Ctrl + Enter to send
          </div>
        </div>

        {answer && (
          <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
            <div className="relative overflow-hidden bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <div className={`absolute top-0 left-0 w-full h-1 ${
                chatMode === 'document' 
                  ? 'bg-gradient-to-r from-purple-500 to-pink-500' 
                  : 'bg-gradient-to-r from-blue-500 to-cyan-500'
              }`}></div>
              
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shadow-lg ${
                    chatMode === 'document' 
                      ? 'bg-gradient-to-br from-purple-500 to-pink-500' 
                      : 'bg-gradient-to-br from-blue-500 to-cyan-500'
                  }`}>
                    {chatMode === 'document' ? (
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                    )}
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
                    {chatMode === 'document' ? 'Document Answer' : 'Assistant Reply'}
                    {answer === "⏳ Thinking..." && (
                      <div className="ml-3 flex space-x-1">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce delay-100"></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce delay-200"></div>
                      </div>
                    )}
                  </h3>
                  <div className="text-slate-200 leading-relaxed whitespace-pre-wrap">
                    {renderAnswerWithCitations(answer)}
                  </div>
                </div>
              </div>
            </div>

            {citations && citations.length > 0 && chatMode === 'document' && (
              <div className="relative overflow-hidden bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6
                           animate-in slide-in-from-bottom-4 duration-700 delay-200">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
                
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-lg 
                                 flex items-center justify-center shadow-lg">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="text-lg font-semibold text-white mb-4">
                      Citations from Document {citations.length > 0 && `(${citations.length})`}
                    </h4>
                    <div className="space-y-3">
                      {citations.map((citation, index) => {
                        const citationKey = citation.id || `citation-${index}`;
                        return (
                          <div key={citationKey} 
                               onClick={() => setSelectedCitation(citation)}
                               className={`group flex flex-col space-y-2 p-4 rounded-lg 
                                        border transition-all duration-200 cursor-pointer
                                        ${selectedCitation?.id === citation.id 
                                          ? 'bg-purple-500/20 border-purple-500/50' 
                                          : 'bg-white/5 border-white/5 hover:border-white/10 hover:bg-white/10'
                                        }`}
                               style={{ animationDelay: `${index * 100}ms` }}>
                            <div className="flex items-center space-x-3">
                              <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-500 
                                             rounded-md flex items-center justify-center text-white text-sm font-medium">
                                  {citation.id || `🔗${index + 1}`}
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex flex-col space-y-1">
                                  <span className="text-slate-200 font-medium">
                                    {citation.label || citation.modality || `Source ${index + 1}`}
                                  </span>
                                  <div className="flex items-center space-x-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium
                                      ${citation.modality === 'text' ? 'bg-blue-500/20 text-blue-300' :
                                        citation.modality === 'table' ? 'bg-green-500/20 text-green-300' :
                                        citation.modality === 'figure' ? 'bg-orange-500/20 text-orange-300' :
                                        'bg-purple-500/20 text-purple-300'}`}>
                                      {citation.modality || 'text'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                              </div>
                            </div>
                            {selectedCitation?.id === citation.id && citation.excerpt && (
                              <div className="pl-11 text-sm text-slate-300 leading-relaxed border-l-2 border-purple-500/30 ml-4">
                                <p className="italic">"{citation.excerpt}"</p>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-center pt-4">
              <button
                onClick={() => {
                  setQuestion("");
                  setAnswer("");
                  setCitations([]);
                  setSelectedCitation(null);
                }}
                className="text-slate-400 hover:text-slate-200 text-sm transition-colors duration-200 
                         flex items-center space-x-2 group"
              >
                <svg className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" 
                     fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Clear Conversation</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Chat;