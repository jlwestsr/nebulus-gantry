import { useState } from 'react';
import { chatApi } from '../services/api';

interface ExportActionsProps {
  conversationId: number | null;
  disabled?: boolean;
}

type ExportFormat = 'json' | 'pdf' | 'excel';
type ExportType = 'export' | 'report';

export function ExportActions({ conversationId, disabled = false }: ExportActionsProps) {
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);

  const handleExport = async (format: ExportFormat, type: ExportType = 'export') => {
    if (!conversationId || isExporting) return;

    const exportKey = `${type}-${format}`;
    setIsExporting(exportKey);
    setShowDropdown(false);

    try {
      let url: string;
      let filename: string;

      if (type === 'report') {
        url = `/api/chat/conversations/${conversationId}/report`;
        filename = `dealership-report-${conversationId}.pdf`;
      } else {
        url = `/api/chat/conversations/${conversationId}/export?format=${format}`;
        const extension = format === 'excel' ? 'xlsx' : format;
        filename = `conversation-${conversationId}.${extension}`;
      }

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Get the blob and download it
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Export failed:', error);
      // You could add toast notification here
      alert(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsExporting(null);
    }
  };

  if (!conversationId) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={disabled || !!isExporting}
        className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors rounded disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Export options"
        title="Export"
      >
        {isExporting ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
            <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"></path>
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        )}
      </button>

      {showDropdown && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />

          {/* Dropdown menu */}
          <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-20">
            <div className="py-1">
              {/* Export section */}
              <div className="px-3 py-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
                Export Conversation
              </div>

              <button
                onClick={() => handleExport('json')}
                disabled={!!isExporting}
                className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export as JSON
                {isExporting === 'export-json' && <div className="ml-auto w-3 h-3 animate-spin rounded-full border border-blue-400 border-t-transparent"></div>}
              </button>

              <button
                onClick={() => handleExport('pdf')}
                disabled={!!isExporting}
                className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Export as PDF (Chat)
                {isExporting === 'export-pdf' && <div className="ml-auto w-3 h-3 animate-spin rounded-full border border-blue-400 border-t-transparent"></div>}
              </button>

              <button
                onClick={() => handleExport('excel')}
                disabled={!!isExporting}
                className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export to Excel
                {isExporting === 'export-excel' && <div className="ml-auto w-3 h-3 animate-spin rounded-full border border-blue-400 border-t-transparent"></div>}
              </button>

              {/* Divider */}
              <div className="border-t border-gray-700 my-1"></div>

              {/* Report section */}
              <div className="px-3 py-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
                Business Report
              </div>

              <button
                onClick={() => handleExport('pdf', 'report')}
                disabled={!!isExporting}
                className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Generate Report
                {isExporting === 'report-pdf' && <div className="ml-auto w-3 h-3 animate-spin rounded-full border border-blue-400 border-t-transparent"></div>}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
