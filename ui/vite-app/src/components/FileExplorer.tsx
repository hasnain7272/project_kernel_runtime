/**
 * Premium Git-Mounted File Explorer
 * 
 * Features:
 * - Virtual file system view
 * - Git status indicators
 * - Real-time sync
 * - Inline diff viewer
 * - Drag-and-drop support
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

// Types
interface VirtualFile {
  path: string;
  type: 'file' | 'directory';
  status: 'unchanged' | 'modified' | 'added' | 'deleted' | 'untracked' | 'conflict';
  size: number;
  sha: string;
}

interface FileChangeEvent {
  event: 'file_changed' | 'file_deleted';
  path: string;
  status?: string;
  size?: number;
}

// Status badge colors
const statusColors: Record<string, string> = {
  unchanged: 'text-gray-500',
  modified: 'text-yellow-500',
  added: 'text-green-500',
  deleted: 'text-red-500',
  untracked: 'text-blue-400',
  conflict: 'text-red-600',
};

const statusBgColors: Record<string, string> = {
  unchanged: 'bg-gray-500/10',
  modified: 'bg-yellow-500/10',
  added: 'bg-green-500/10',
  deleted: 'bg-red-500/10',
  untracked: 'bg-blue-400/10',
  conflict: 'bg-red-600/10',
};

// Icons
const FileIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const FolderIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
  </svg>
);

const RefreshIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const GitBranchIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
  </svg>
);

// Components
interface FileTreeItemProps {
  file: VirtualFile;
  level: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onDoubleClick: (file: VirtualFile) => void;
  expanded: Set<string>;
  onToggleExpand: (path: string) => void;
}

const FileTreeItem: React.FC<FileTreeItemProps> = ({
  file,
  level,
  selectedPath,
  onSelect,
  onDoubleClick,
  expanded,
  onToggleExpand,
}) => {
  const isSelected = selectedPath === file.path;
  const isExpanded = expanded.has(file.path);
  const isDirectory = file.type === 'directory';
  
  const paddingLeft = `${level * 16 + 8}px`;
  
  const handleClick = () => {
    onSelect(file.path);
  };
  
  const handleDoubleClick = () => {
    if (isDirectory) {
      onToggleExpand(file.path);
    } else {
      onDoubleClick(file);
    }
  };
  
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand(file.path);
  };
  
  return (
    <div
      className={`
        flex items-center py-1 px-2 cursor-pointer select-none
        transition-colors duration-150
        ${isSelected ? 'bg-blue-500/20 border-l-2 border-blue-500' : 'hover:bg-white/5 border-l-2 border-transparent'}
        ${statusBgColors[file.status] || ''}
      `}
      style={{ paddingLeft }}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
    >
      {/* Expand/Collapse Toggle */}
      {isDirectory && (
        <button
          onClick={handleToggle}
          className="mr-1 p-0.5 hover:bg-white/10 rounded"
        >
          <svg
            className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      )}
      
      {/* Icon */}
      {isDirectory ? (
        <FolderIcon className="w-4 h-4 mr-2 text-yellow-400" />
      ) : (
        <FileIcon className={`w-4 h-4 mr-2 ${statusColors[file.status] || 'text-gray-400'}`} />
      )}
      
      {/* File Name */}
      <span className={`flex-1 truncate text-sm ${isDirectory ? 'font-medium text-gray-200' : 'text-gray-300'}`}>
        {file.path.split('/').pop()}
      </span>
      
      {/* Status Badge */}
      {file.status !== 'unchanged' && (
        <span className={`text-xs px-1.5 py-0.5 rounded ${statusColors[file.status]} bg-opacity-10 bg-white`}>
          {file.status.charAt(0).toUpperCase() + file.status.slice(1)}
        </span>
      )}
      
      {/* File Size */}
      {!isDirectory && file.size > 0 && (
        <span className="text-xs text-gray-500 ml-2">
          {formatFileSize(file.size)}
        </span>
      )}
    </div>
  );
};

// Helper functions
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Main Component
interface FileExplorerProps {
  sessionId: string;
  onFileSelect?: (file: VirtualFile) => void;
  onFileOpen?: (file: VirtualFile) => void;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({
  sessionId,
  onFileSelect,
  onFileOpen,
}) => {
  const [files, setFiles] = useState<VirtualFile[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set(['.']));
  const [isLoading, setIsLoading] = useState(true);
  const [changes, setChanges] = useState({ modified: 0, added: 0, deleted: 0 });
  const [mountInfo, setMountInfo] = useState<{ repo_url?: string; branch?: string } | null>(null);
  
  const tenantId = useSessionStore(s => s.tenantId) || localStorage.getItem('tenant_id') || 'local';
  const wsUrl = `/api/v1/git/mount/${sessionId}/files/stream?tenant_id=${tenantId}`;
  useEffect(() => { console.log("[FileExplorer] Connecting WebSocket:", wsUrl); }, [wsUrl]);
  const { lastMessage, sendMessage } = useWebSocket(wsUrl);
  
  // Load file tree
  const loadTree = useCallback(async () => {
    try {
      setIsLoading(true);
      const { apiClient } = await import('@/api/client');
      const response = await apiClient.get<any>(`/git/mount/${sessionId}/tree`);
      
      if (response.error) throw new Error(response.error);
      const data = response.data;
      
      setFiles(data.items);
      
      // Calculate changes
      const stats = data.items.reduce((acc: any, file: VirtualFile) => {
        if (file.status === 'modified') acc.modified++;
        if (file.status === 'added') acc.added++;
        if (file.status === 'deleted') acc.deleted++;
        return acc;
      }, { modified: 0, added: 0, deleted: 0 });
      setChanges(stats);
      
    } catch (error: any) {
      console.error('Failed to load file tree:', error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);
  
  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const event: FileChangeEvent = JSON.parse(lastMessage.data);
      
      if (event.event === 'file_changed') {
        setFiles(prev => prev.map(f => 
          f.path === event.path 
            ? { ...f, status: event.status as any, size: event.size || f.size }
            : f
        ));
      } else if (event.event === 'file_deleted') {
        setFiles(prev => prev.filter(f => f.path !== event.path));
      }
    }
  }, [lastMessage]);
  
  // Initial load
  useEffect(() => {
    loadTree();
  }, [loadTree]);

  // Refresh from external events (e.g. Chat pane upload)
  useEffect(() => {
    const handleRefresh = () => loadTree();
    window.addEventListener('refresh-workspace', handleRefresh);
    return () => window.removeEventListener('refresh-workspace', handleRefresh);
  }, [loadTree]);
  
  // Build tree structure
  const buildTree = (items: VirtualFile[]): VirtualFile[] => {
    // Group by directory
    const tree: VirtualFile[] = [];
    const seen = new Set<string>();
    
    items.forEach(item => {
      const parts = item.path.split('/');
      let currentPath = '';
      
      parts.forEach((part, idx) => {
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        
        if (!seen.has(currentPath)) {
          seen.add(currentPath);
          
          const isFile = idx === parts.length - 1;
          if (!isFile || currentPath === item.path) {
            tree.push({
              ...item,
              path: currentPath,
              type: isFile ? 'file' : 'directory',
            });
          }
        }
      });
    });
    
    return tree.sort((a, b) => {
      // Directories first
      if (a.type !== b.type) {
        return a.type === 'directory' ? -1 : 1;
      }
      return a.path.localeCompare(b.path);
    });
  };
  
  const handleSelect = (path: string) => {
    setSelectedPath(path);
    const file = files.find(f => f.path === path);
    if (file && onFileSelect) {
      onFileSelect(file);
    }
  };
  
  const handleDoubleClick = (file: VirtualFile) => {
    if (onFileOpen) {
      onFileOpen(file);
    }
  };
  
  const handleToggleExpand = (path: string) => {
    setExpandedDirs(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };
  
  // Filter visible files (respect expanded state)
  const visibleFiles = buildTree(files).filter(file => {
    if (file.path === '.') return true;
    
    const parts = file.path.split('/');
    let currentPath = '';
    
    for (let i = 0; i < parts.length - 1; i++) {
      currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i];
      if (!expandedDirs.has(currentPath)) {
        return false;
      }
    }
    
    return true;
  });
  
  const totalChanges = changes.modified + changes.added + changes.deleted;
  
  return (
    <div className="h-full flex flex-col bg-gray-900 border-r border-gray-700">
      {/* Header */}
      <div className="p-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <GitBranchIcon className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-gray-200">Explorer</span>
          </div>
          <button
            onClick={loadTree}
            disabled={isLoading}
            className="p-1.5 hover:bg-white/10 rounded transition-colors"
            title="Refresh"
          >
            <RefreshIcon className={`w-4 h-4 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        
        {/* Changes Summary */}
        {totalChanges > 0 && (
          <div className="flex gap-3 text-xs">
            {changes.modified > 0 && (
              <span className="text-yellow-400">
                {changes.modified} modified
              </span>
            )}
            {changes.added > 0 && (
              <span className="text-green-400">
                {changes.added} added
              </span>
            )}
            {changes.deleted > 0 && (
              <span className="text-red-400">
                {changes.deleted} deleted
              </span>
            )}
          </div>
        )}
      </div>
      
      {/* File Tree */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
            Loading files...
          </div>
        ) : visibleFiles.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <p>No files in repository</p>
            <p className="text-xs mt-1">Mount a Git repository to get started</p>
          </div>
        ) : (
          <div className="py-1">
            {visibleFiles.map(file => {
              const level = file.path === '.' ? 0 : file.path.split('/').length - 1;
              return (
                <FileTreeItem
                  key={file.path}
                  file={file}
                  level={level}
                  selectedPath={selectedPath}
                  onSelect={handleSelect}
                  onDoubleClick={handleDoubleClick}
                  expanded={expandedDirs}
                  onToggleExpand={handleToggleExpand}
                />
              );
            })}
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="p-2 border-t border-gray-700 bg-gray-800/50 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>{files.length} files</span>
          <span>{totalChanges} changes</span>
        </div>
      </div>
    </div>
  );
};

// Inline Diff Viewer
interface DiffViewerProps {
  oldContent: string;
  newContent: string;
  oldLabel?: string;
  newLabel?: string;
  fileName?: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  oldContent,
  newContent,
  oldLabel = 'HEAD',
  newLabel = 'Modified',
  fileName,
}) => {
  const [diff, setDiff] = useState<{ type: 'add' | 'remove' | 'context'; content: string; lineNum: number }[]>([]);
  
  useEffect(() => {
    // Simple diff algorithm
    const oldLines = oldContent.split('\n');
    const newLines = newContent.split('\n');
    
    // This is a simplified diff - for production use a proper diff library
    const result: typeof diff = [];
    let oldIdx = 0;
    let newIdx = 0;
    
    while (oldIdx < oldLines.length || newIdx < newLines.length) {
      const oldLine = oldLines[oldIdx];
      const newLine = newLines[newIdx];
      
      if (oldLine === newLine) {
        result.push({ type: 'context', content: oldLine, lineNum: oldIdx + 1 });
        oldIdx++;
        newIdx++;
      } else if (oldIdx < oldLines.length) {
        result.push({ type: 'remove', content: oldLine, lineNum: oldIdx + 1 });
        oldIdx++;
      } else if (newIdx < newLines.length) {
        result.push({ type: 'add', content: newLine, lineNum: newIdx + 1 });
        newIdx++;
      }
    }
    
    setDiff(result);
  }, [oldContent, newContent]);
  
  return (
    <div className="flex flex-col h-full bg-gray-900 rounded overflow-hidden">
      {/* Header */}
      {fileName && (
        <div className="px-3 py-2 bg-gray-800 border-b border-gray-700 flex justify-between">
          <span className="text-sm font-medium text-gray-200">{fileName}</span>
          <div className="flex gap-4 text-xs">
            <span className="text-red-400">{oldLabel}</span>
            <span className="text-green-400">{newLabel}</span>
          </div>
        </div>
      )}
      
      {/* Diff Content */}
      <div className="flex-1 overflow-auto font-mono text-xs">
        {diff.map((line, idx) => (
          <div
            key={idx}
            className={`flex px-3 py-0.5 ${
              line.type === 'add' ? 'bg-green-900/30' :
              line.type === 'remove' ? 'bg-red-900/30' :
              ''
            }`}
          >
            <span className="w-8 text-gray-500 select-none text-right mr-3">
              {line.lineNum}
            </span>
            <span className={`w-4 mr-2 ${
              line.type === 'add' ? 'text-green-500' :
              line.type === 'remove' ? 'text-red-500' :
              'text-gray-600'
            }`}>
              {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}
            </span>
            <span className={`flex-1 whitespace-pre ${
              line.type === 'add' ? 'text-green-300' :
              line.type === 'remove' ? 'text-red-300' :
              'text-gray-300'
            }`}>
              {line.content}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Mount Dialog
interface MountDialogProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  onMount: (info: { repo_url: string; branch: string }) => void;
}

export const MountDialog: React.FC<MountDialogProps> = ({
  isOpen,
  onClose,
  sessionId,
  onMount,
}) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [authToken, setAuthToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleMount = async () => {
    if (!repoUrl) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const { apiClient } = await import('@/api/client');
      const response = await apiClient.post<any>('/git/mount', {
        session_id: sessionId,
        repo_url: repoUrl,
        branch,
        auth_token: authToken || undefined,
      });
      
      if (response.error) throw new Error(response.error);
      const data = response.data;
      
      onMount({ repo_url: data.repo_url, branch: data.branch });
      onClose();
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Mount Git Repository</h2>
        
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">
            {error}
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Repository URL</label>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/user/repo"
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          
          <div>
            <label className="block text-sm text-gray-400 mb-1">Branch</label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Auth Token (optional)
            </label>
            <input
              type="password"
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxx"
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-gray-500">
              Token will be encrypted and stored securely
            </p>
          </div>
        </div>
        
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleMount}
            disabled={isLoading || !repoUrl}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white rounded transition-colors flex items-center gap-2"
          >
            {isLoading && (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            Mount Repository
          </button>
        </div>
      </div>
    </div>
  );
};

export default FileExplorer;