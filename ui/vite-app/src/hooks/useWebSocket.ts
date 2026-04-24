/**
 * WebSocket Hook for Real-time Communication
 * 
 * Features:
 * - Automatic reconnection
 * - Message queueing during offline
 * - Connection state tracking
 * - Auth token injection
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { getAuthToken } from '@/api/client';

interface WebSocketMessage {
  data: any;
  timestamp: number;
}

interface UseWebSocketOptions {
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Event) => void;
  onMessage?: (data: any) => void;
}

export function useWebSocket(
  path: string,
  options: UseWebSocketOptions = {}
) {
  const {
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<any[]>([]);

  // Get WebSocket URL
  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_API_URL || window.location.host;
    const token = getAuthToken();
    const suffix = token && !path.includes('token=')
      ? `${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`
      : '';
    return `${protocol}//${host}${path}${suffix}`;
  }, [path]);

  // Connect
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setConnectionError(null);

    try {
      const ws = new WebSocket(getWsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttemptsRef.current = 0;
        
        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const msg = messageQueueRef.current.shift();
          ws.send(JSON.stringify(msg));
        }
        
        onOpen?.();
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        onClose?.(event);

        // Auto reconnect
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`[WebSocket] Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval * reconnectAttemptsRef.current); // Exponential backoff
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setConnectionError('Connection failed');
        onError?.(error);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage({ data, timestamp: Date.now() });
          onMessage?.(data);
        } catch (e) {
          // Handle non-JSON messages
          setLastMessage({ data: event.data, timestamp: Date.now() });
          onMessage?.(event.data);
        }
      };

    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      setConnectionError('Failed to connect');
      setIsConnecting(false);
    }
  }, [getWsUrl, autoReconnect, reconnectInterval, maxReconnectAttempts, onOpen, onClose, onError, onMessage]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnect
  }, [maxReconnectAttempts]);

  // Send message
  const sendMessage = useCallback((data: any) => {
    const message = typeof data === 'string' ? data : JSON.stringify(data);
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
      return true;
    } else {
      // Queue message for when connection is restored
      messageQueueRef.current.push(data);
      return false;
    }
  }, []);

  // Reconnect manually
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect, disconnect]);

  // Auto connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    isConnecting,
    lastMessage,
    connectionError,
    sendMessage,
    connect,
    disconnect,
    reconnect,
  };
}

export default useWebSocket;
