import { useState, useEffect, useRef } from 'react';
import { useDocumentStore } from '../stores/documentStore';
import type { Collection, Document } from '../types/api';

interface KnowledgeVaultProps {
  onClose?: () => void;
}

export function KnowledgeVault({ onClose }: KnowledgeVaultProps) {
  const {
    collections,
    documents,
    selectedCollectionId,
    isLoading,
    fetchCollections,
    fetchDocuments,
    createCollection,
    deleteCollection,
    selectCollection,
    uploadDocument,
    deleteDocument,
  } = useDocumentStore();

  const [isExpanded, setIsExpanded] = useState(false);
  const [showNewCollection, setShowNewCollection] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isExpanded && collections.length === 0) {
      fetchCollections();
    }
  }, [isExpanded, collections.length, fetchCollections]);

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;
    try {
      await createCollection(newCollectionName.trim());
      setNewCollectionName('');
      setShowNewCollection(false);
    } catch {
      // Error handled in store
    }
  };

  const handleDeleteCollection = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this collection and all its documents?')) {
      try {
        await deleteCollection(id);
      } catch {
        // Error handled in store
      }
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await uploadDocument(file, selectedCollectionId ?? undefined);
    } catch {
      // Error handled in store
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteDocument = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this document?')) {
      try {
        await deleteDocument(id);
      } catch {
        // Error handled in store
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="mb-4">
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider hover:bg-gray-800 rounded"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Knowledge Vault
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {/* Actions */}
          <div className="flex gap-2 px-3">
            <button
              className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded transition-colors"
              onClick={() => setShowNewCollection(true)}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Collection
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.csv,.docx"
              className="hidden"
              onChange={handleUpload}
            />
            <button
              className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded transition-colors disabled:opacity-50"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>

          {/* New Collection Form */}
          {showNewCollection && (
            <div className="px-3 flex gap-2">
              <input
                type="text"
                placeholder="Collection name"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateCollection()}
                className="flex-1 px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
              <button
                className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
                onClick={handleCreateCollection}
              >
                Add
              </button>
              <button
                className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
                onClick={() => {
                  setShowNewCollection(false);
                  setNewCollectionName('');
                }}
              >
                Cancel
              </button>
            </div>
          )}

          {/* Collections List */}
          {isLoading && collections.length === 0 ? (
            <div className="flex justify-center py-4">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
            </div>
          ) : collections.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-gray-500">
              No collections yet
            </div>
          ) : (
            <div className="space-y-1">
              {/* All Documents option */}
              <button
                className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs rounded transition-colors ${
                  selectedCollectionId === null
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`}
                onClick={() => selectCollection(null)}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                All Documents
              </button>

              {collections.map((collection) => (
                <div
                  key={collection.id}
                  className={`group flex items-center gap-2 px-3 py-1.5 text-xs rounded cursor-pointer transition-colors ${
                    selectedCollectionId === collection.id
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`}
                  onClick={() => selectCollection(collection.id)}
                >
                  <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span className="flex-1 truncate">{collection.name}</span>
                  <span className="text-gray-500">{collection.document_count}</span>
                  <button
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-600 rounded"
                    onClick={(e) => handleDeleteCollection(collection.id, e)}
                    title="Delete collection"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Documents in selected collection */}
          {documents.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-700/50">
              <h4 className="px-3 text-xs font-medium text-gray-500 uppercase mb-2">Documents</h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="group flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:bg-gray-800 rounded"
                  >
                    <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <span className="flex-1 truncate" title={doc.filename}>
                      {doc.filename}
                    </span>
                    {doc.status === 'processing' && (
                      <span className="text-yellow-500">Processing...</span>
                    )}
                    {doc.status === 'failed' && (
                      <span className="text-red-500" title={doc.error_message || 'Failed'}>Failed</span>
                    )}
                    {doc.status === 'ready' && (
                      <span className="text-gray-500">{formatFileSize(doc.file_size)}</span>
                    )}
                    <button
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-600 rounded"
                      onClick={(e) => handleDeleteDocument(doc.id, e)}
                      title="Delete document"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
