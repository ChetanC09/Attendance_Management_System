import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { UserRole, UserProfile, NotificationItem } from '../types';
import { api, jsonBody, type ApiUser } from '../services/api';

export interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title?: string;
  message: string;
}

interface AppContextType {
  currentRole: UserRole;
  currentUser: UserProfile;
  authenticated: boolean;
  checkingSession: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  currentRoute: string;
  setCurrentRoute: (route: string) => void;
  selectedRequestId: string | null;
  setSelectedRequestId: (id: string | null) => void;

  notifications: NotificationItem[];

  // Actions
  addToast: (
    msgOrObj: string | { message: string; type?: 'success' | 'info' | 'warning' | 'error'; title?: string },
    type?: 'success' | 'info' | 'warning' | 'error',
    title?: string
  ) => void;
  dismissToast: (id: string) => void;
  toasts: ToastMessage[];

  markNotificationAsRead: (id: string) => void;
  markAllNotificationsAsRead: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const routeFromPath = (pathname: string): { route: string; requestId: string | null } => {
  const detailPrefix = '/app/regularization-detail/';
  if (pathname.startsWith(detailPrefix)) {
    return { route: 'regularization-detail', requestId: decodeURIComponent(pathname.slice(detailPrefix.length)) || null };
  }
  return {
    route: pathname.startsWith('/app/') ? decodeURIComponent(pathname.slice('/app/'.length)) : 'login',
    requestId: null,
  };
};

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRole, setCurrentRole] = useState<UserRole>('student');
  const [currentRoute, setCurrentRouteState] = useState<string>(() => routeFromPath(window.location.pathname).route);
  const [selectedRequestId, setSelectedRequestIdState] = useState<string | null>(() => routeFromPath(window.location.pathname).requestId);
  const selectedRequestIdRef = useRef(selectedRequestId);
  const setSelectedRequestId = useCallback((id: string | null) => {
    selectedRequestIdRef.current = id;
    setSelectedRequestIdState(id);
  }, []);
  const setCurrentRoute = useCallback((route: string) => {
    const detailPath = route === 'regularization-detail' && selectedRequestIdRef.current
      ? `/app/regularization-detail/${encodeURIComponent(selectedRequestIdRef.current)}`
      : null;
    const path = route === 'login' ? '/auth/login' : detailPath || `/app/${encodeURIComponent(route)}`;
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setCurrentRouteState(route);
  }, []);
  const [apiUser, setApiUser] = useState<ApiUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const authenticated = Boolean(apiUser);
  const mapUser = (user: ApiUser): UserProfile => ({
    id: user.id, name: user.full_name, rollOrEmpId: user.institutional_id, email: user.email,
    role: user.role.toLowerCase() as UserRole, department: '—', initials: user.full_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase(),
  });
  const currentUser = apiUser ? mapUser(apiUser) : {
    id: '', name: '', rollOrEmpId: '', email: '', role: currentRole, department: '—', initials: '',
  };

  useEffect(() => {
    api<ApiUser>('/api/auth/me').then((user) => {
      setApiUser(user); setCurrentRole(user.role.toLowerCase() as UserRole);
      if (window.location.pathname === '/' || window.location.pathname === '/auth/login') setCurrentRoute(user.role === 'ADMIN' ? 'institutional-health-admin' : user.role === 'FACULTY' ? 'faculty-workspace' : 'overview-dashboard');
    }).catch(() => { setApiUser(null); setCurrentRoute('login'); }).finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    const onPopState = () => {
      const parsed = routeFromPath(window.location.pathname);
      setCurrentRouteState(parsed.route);
      setSelectedRequestId(parsed.requestId);
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (!apiUser) { setNotifications([]); return; }
    api<Array<{ id: string; title: string; message: string; channel: string; status: string; read_at: string | null; created_at: string }>>('/api/notifications')
      .then((rows) => setNotifications(rows.map((row) => ({ id: row.id, title: row.title, message: row.message, category: 'system', timestamp: row.created_at, unread: !row.read_at, badge: row.channel }))))
      .catch(() => setNotifications([]));
  }, [apiUser]);

  const signIn = async (email: string, password: string) => {
    const session = await api<{ user: ApiUser }>('/api/auth/login', { method: 'POST', body: jsonBody({ email, password }) });
    setApiUser(session.user);
    const role = session.user.role.toLowerCase() as UserRole;
    setCurrentRole(role);
    setCurrentRoute(role === 'admin' ? 'institutional-health-admin' : role === 'faculty' ? 'faculty-workspace' : 'overview-dashboard');
  };
  const signOut = async () => {
    try { await api<void>('/api/auth/logout', { method: 'POST' }); }
    finally { setApiUser(null); setCurrentRoute('login'); }
  };

  const addToast = (
    msgOrObj: string | { message: string; type?: 'success' | 'info' | 'warning' | 'error'; title?: string },
    type: 'success' | 'info' | 'warning' | 'error' = 'success',
    title?: string
  ) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    if (typeof msgOrObj === 'object') {
      setToasts((prev) => [
        ...prev,
        {
          id,
          type: msgOrObj.type || 'success',
          title: msgOrObj.title,
          message: msgOrObj.message,
        },
      ]);
    } else {
      setToasts((prev) => [...prev, { id, type, title, message: msgOrObj }]);
    }
    setTimeout(() => {
      dismissToast(id);
    }, 3800);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const markNotificationAsRead = (id: string) => {
    void api(`/api/notifications/${id}/read`, { method: 'POST' }).then(() => setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, unread: false } : n))));
  };

  const markAllNotificationsAsRead = () => {
    void Promise.all(notifications.filter((item) => item.unread).map((item) => api(`/api/notifications/${item.id}/read`, { method: 'POST' })))
      .then(() => setNotifications((prev) => prev.map((n) => ({ ...n, unread: false }))));
  };

  return (
    <AppContext.Provider
      value={{
        currentRole,
        currentUser,
        authenticated,
        checkingSession,
        signIn,
        signOut,
        currentRoute,
        setCurrentRoute,
        selectedRequestId,
        setSelectedRequestId,
        notifications,
        toasts,
        addToast,
        dismissToast,
        markNotificationAsRead,
        markAllNotificationsAsRead,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

