import { useEffect, useRef, useState, useCallback } from "react";

export type RemoteUpdate = {
  type: "row_update" | "cursor" | "presence";
  user_id: string;
  user_name: string;
  [key: string]: unknown;
};

export type ConnectedUser = {
  user_id: string;
  user_name: string;
};

function getWsBase(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  if (apiUrl.startsWith("https://")) return "wss://" + apiUrl.slice("https://".length);
  if (apiUrl.startsWith("http://")) return "ws://" + apiUrl.slice("http://".length);
  return apiUrl;
}

export function useWebSocket(
  projectId: string | null,
  userId: string,
  userName: string
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef<boolean>(true);

  const [isConnected, setIsConnected] = useState(false);
  const [remoteUpdates, setRemoteUpdates] = useState<RemoteUpdate[]>([]);
  const [connectedUsers, setConnectedUsers] = useState<ConnectedUser[]>([]);

  const send = useCallback((payload: object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }, []);

  const sendUpdate = useCallback(
    (rowId: string | number, changes: Record<string, unknown>) => {
      send({ type: "row_update", row_id: rowId, changes });
    },
    [send]
  );

  const sendCursor = useCallback(
    (position: { rowId?: string | number; column?: string; x?: number; y?: number }) => {
      send({ type: "cursor", position });
    },
    [send]
  );

  useEffect(() => {
    if (!projectId) {
      setIsConnected(false);
      return;
    }

    shouldReconnectRef.current = true;

    const connect = () => {
      const base = getWsBase();
      const url = `${base}/ws/project/${encodeURIComponent(
        projectId
      )}?user_id=${encodeURIComponent(userId)}&user_name=${encodeURIComponent(userName)}`;

      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (e) {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as RemoteUpdate;
          if (msg.type === "presence" && Array.isArray((msg as { users?: ConnectedUser[] }).users)) {
            setConnectedUsers((msg as { users: ConnectedUser[] }).users);
          }
          setRemoteUpdates((prev) => [...prev.slice(-99), msg]);
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        if (shouldReconnectRef.current) {
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          // ignore
        }
      };
    };

    const scheduleReconnect = () => {
      if (reconnectTimerRef.current) return;
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        if (shouldReconnectRef.current) connect();
      }, 3000);
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // ignore
        }
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [projectId, userId, userName]);

  return { sendUpdate, sendCursor, remoteUpdates, connectedUsers, isConnected };
}

export default useWebSocket;
