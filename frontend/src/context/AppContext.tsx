import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  UserRole,
  UserProfile,
  CourseStanding,
  TimetableSlot,
  RegularizationRequest,
  NotificationItem,
  AttendanceRecord,
  DepartmentStat,
  GovernancePolicy,
  ClassroomStudent,
  EnrolledStudent,
  AuditLogEntry,
} from '../types';
import {
  currentUserProfiles,
  initialCourseStandings,
  initialTimetableSlots,
  initialRegularizationRequests,
  initialNotifications,
  initialAttendanceRecords,
  initialClassroomStudents,
  initialDepartmentStats,
  initialGovernancePolicy,
  initialEnrolledStudents,
  initialAuditLogs,
} from '../data/mockData';
import { api, jsonBody, type ApiUser } from '../services/api';

export interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title?: string;
  message: string;
}

interface AppContextType {
  currentRole: UserRole;
  setCurrentRole: (role: UserRole) => void;
  currentUser: UserProfile;
  authenticated: boolean;
  checkingSession: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  currentRoute: string;
  setCurrentRoute: (route: string) => void;
  selectedRequestId: string | null;
  setSelectedRequestId: (id: string | null) => void;

  // Data
  courses: CourseStanding[];
  timetable: TimetableSlot[];
  regularizationRequests: RegularizationRequest[];
  notifications: NotificationItem[];
  attendanceRecords: AttendanceRecord[];
  classroomStudents: ClassroomStudent[];
  departmentStats: DepartmentStat[];
  governancePolicy: GovernancePolicy;
  enrolledStudents: EnrolledStudent[];
  auditLogs: AuditLogEntry[];

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
  submitRegularizationRequest: (req: Omit<RegularizationRequest, 'id' | 'filingDate' | 'status'>) => void;
  approveRegularizationRequest: (id: string, comment?: string) => void;
  rejectRegularizationRequest: (id: string, comment?: string) => void;

  updateClassroomStudentStatus: (studentId: string, status: ClassroomStudent['attendanceStatus'], reason: string) => void;
  updateGovernancePolicy: (policy: Partial<GovernancePolicy>) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRole, setCurrentRole] = useState<UserRole>('student');
  const [currentRoute, setCurrentRouteState] = useState<string>(() => {
    const path = window.location.pathname;
    return path.startsWith('/app/') ? decodeURIComponent(path.slice('/app/'.length)) : 'login';
  });
  const setCurrentRoute = useCallback((route: string) => {
    const path = route === 'login' ? '/auth/login' : `/app/${encodeURIComponent(route)}`;
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setCurrentRouteState(route);
  }, []);
  const [apiUser, setApiUser] = useState<ApiUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>('REG-2026-0419');

  const [courses] = useState<CourseStanding[]>(initialCourseStandings);
  const [timetable] = useState<TimetableSlot[]>(initialTimetableSlots);
  const [regularizationRequests, setRegularizationRequests] = useState<RegularizationRequest[]>(
    initialRegularizationRequests
  );
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [attendanceRecords] = useState<AttendanceRecord[]>(initialAttendanceRecords);
  const [classroomStudents, setClassroomStudents] = useState<ClassroomStudent[]>(initialClassroomStudents);
  const [departmentStats] = useState<DepartmentStat[]>(initialDepartmentStats);
  const [governancePolicy, setGovernancePolicy] = useState<GovernancePolicy>(initialGovernancePolicy);
  const [enrolledStudents] = useState<EnrolledStudent[]>(initialEnrolledStudents);
  const [auditLogs] = useState<AuditLogEntry[]>(initialAuditLogs);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const authenticated = Boolean(apiUser);
  const mapUser = (user: ApiUser): UserProfile => ({
    id: user.id, name: user.full_name, rollOrEmpId: user.institutional_id, email: user.email,
    role: user.role.toLowerCase() as UserRole, department: '—', initials: user.full_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase(),
  });
  const currentUser = apiUser ? mapUser(apiUser) : currentUserProfiles[currentRole];

  useEffect(() => {
    api<ApiUser>('/api/auth/me').then((user) => {
      setApiUser(user); setCurrentRole(user.role.toLowerCase() as UserRole);
      if (window.location.pathname === '/' || window.location.pathname === '/auth/login') setCurrentRoute(user.role === 'ADMIN' ? 'institutional-health-admin' : user.role === 'FACULTY' ? 'faculty-workspace' : 'overview-dashboard');
    }).catch(() => { setApiUser(null); setCurrentRoute('login'); }).finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    const onPopState = () => setCurrentRouteState(window.location.pathname.startsWith('/app/') ? decodeURIComponent(window.location.pathname.slice('/app/'.length)) : 'login');
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

  const submitRegularizationRequest = (
    reqData: Omit<
      RegularizationRequest,
      'id' | 'filingDate' | 'status'
    >
  ) => {
    const newId = `DEMO-${Date.now()}`;
    const newRequest: RegularizationRequest = {
      ...reqData,
      id: newId,
      filingDate: new Date().toLocaleString(),
      status: 'under_review',
    };

    setRegularizationRequests((prev) => [newRequest, ...prev]);
    setSelectedRequestId(newId);
    setCurrentRoute('regularization-detail');
    addToast({ type: 'info', title: 'Preview request added', message: 'This request exists only in local sample state and was not sent to the backend.' });
  };

  const approveRegularizationRequest = (id: string, comment?: string) => {
    setRegularizationRequests((prev) =>
      prev.map((r) => {
        if (r.id === id) {
          return {
            ...r,
            status: 'approved',
            advisorEndorsement: {
              advisorName: currentUser.name,
              timestamp: new Date().toLocaleString(),
              comment: comment || 'Approved by Faculty',
            },
          };
        }
        return r;
      })
    );

    addToast({ type: 'info', title: 'Preview decision updated', message: 'Only the local request status changed. No attendance record or backend data was modified.' });
  };

  const rejectRegularizationRequest = (id: string, comment?: string) => {
    setRegularizationRequests((prev) =>
      prev.map((r) => {
        if (r.id === id) {
          return {
            ...r,
            status: 'rejected',
            advisorEndorsement: {
              advisorName: currentUser.name,
              timestamp: new Date().toLocaleString(),
              comment: comment || 'Request declined in local preview.',
            },
          };
        }
        return r;
      })
    );
    addToast({ type: 'info', title: 'Preview decision updated', message: 'Only the local request status changed; it was not sent to the backend.' });
  };

  const updateClassroomStudentStatus = (
    studentId: string,
    status: ClassroomStudent['attendanceStatus'],
    reason: string,
  ) => {
    setClassroomStudents((prev) =>
      prev.map((st) => {
        if (st.id === studentId) {
          return {
            ...st,
            attendanceStatus: status,
            overrideType: 'manual',
            manualReason: reason,
            timeMarked: status === 'verified' || status === 'late'
              ? new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : undefined,
          };
        }
        return st;
      })
    );
  };

  const updateGovernancePolicy = (newVals: Partial<GovernancePolicy>) => {
    setGovernancePolicy((prev) => ({
      ...prev,
      ...newVals,
    }));
    addToast({ type: 'info', title: 'Preview updated locally', message: 'This sample setting is not saved to the backend.' });
  };

  return (
    <AppContext.Provider
      value={{
        currentRole,
        setCurrentRole,
        currentUser,
        authenticated,
        checkingSession,
        signIn,
        signOut,
        currentRoute,
        setCurrentRoute,
        selectedRequestId,
        setSelectedRequestId,
        courses,
        timetable,
        regularizationRequests,
        notifications,
        attendanceRecords,
        classroomStudents,
        departmentStats,
        governancePolicy,
        enrolledStudents,
        auditLogs,
        toasts,
        addToast,
        dismissToast,
        markNotificationAsRead,
        markAllNotificationsAsRead,
        submitRegularizationRequest,
        approveRegularizationRequest,
        rejectRegularizationRequest,
        updateClassroomStudentStatus,
        updateGovernancePolicy,
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

