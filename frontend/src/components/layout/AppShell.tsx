import React, { useState } from 'react';
import {
  Bell,
  BookOpen,
  CalendarDays,
  ClipboardCheck,
  FileClock,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings2,
  ShieldCheck,
  Users,
  Video,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import type { UserRole } from '../../types';

interface AppShellProps {
  children: React.ReactNode;
}

interface NavigationItem {
  label: string;
  route: string;
  icon: LucideIcon;
}

const navigation: Record<UserRole, NavigationItem[]> = {
  student: [
    { label: 'Overview', route: 'overview-dashboard', icon: LayoutDashboard },
    { label: 'Course attendance', route: 'course-attendance', icon: BookOpen },
    { label: 'Attendance history', route: 'attendance-history', icon: FileClock },
    { label: 'Recovery planner', route: 'recovery-planner', icon: ClipboardCheck },
    { label: 'Timetable', route: 'timetable-schedule', icon: CalendarDays },
    { label: 'Requests', route: 'leave-medical-slips', icon: FileClock },
    { label: 'Notifications', route: 'notification-center', icon: Bell },
    { label: 'Profile & settings', route: 'student-settings', icon: Settings2 },
  ],
  faculty: [
    { label: 'Overview', route: 'faculty-workspace', icon: LayoutDashboard },
    { label: "Today's classes", route: 'faculty-timetable', icon: CalendarDays },
    { label: 'Camera attendance', route: 'camera-attendance-session', icon: Video },
    { label: 'Manual attendance', route: 'faculty-manual-attendance', icon: ClipboardCheck },
    { label: 'Defaulters', route: 'student-attendance-tracker', icon: Users },
    { label: 'Request review', route: 'faculty-approvals', icon: FileClock },
    { label: 'Analytics & students', route: 'faculty-analytics', icon: Users },
    { label: 'Announcements', route: 'faculty-announcements', icon: Bell },
    { label: 'Settings', route: 'faculty-settings', icon: Settings2 },
  ],
  admin: [
    { label: 'Overview', route: 'institutional-health-admin', icon: LayoutDashboard },
    { label: 'User directory', route: 'admin-users', icon: Users },
    { label: 'Academic structure', route: 'admin-academic-structure', icon: GraduationCap },
    { label: 'Academic governance', route: 'governance', icon: Settings2 },
    { label: 'System settings & audit', route: 'system-logs-settings', icon: ShieldCheck },
  ],
};

const roleHome: Record<UserRole, string> = {
  student: 'overview-dashboard',
  faculty: 'faculty-workspace',
  admin: 'institutional-health-admin',
};

const routeNames: Record<string, string> = {
  'overview-dashboard': 'Overview',
  'student-dashboard': 'Overview',
  'course-attendance': 'Course attendance',
  'student-ledger': 'Course attendance',
  'attendance-history': 'Attendance history',
  'student-history': 'Attendance history',
  'recovery-planner': 'Recovery planner',
  'timetable-schedule': 'Timetable',
  timetable: 'Timetable',
  'student-timetable': 'Timetable',
  'leave-medical-slips': 'Requests',
  regularization: 'Requests',
  'student-regularization': 'Requests',
  'regularization-form': 'New request',
  'student-regularization-new': 'New request',
  'regularization-detail': 'Request details',
  'student-regularization-detail': 'Request details',
  'notification-center': 'Notifications',
  'student-notifications': 'Notifications',
  'student-settings': 'Profile & settings',
  'faculty-workspace': 'Overview',
  'faculty-dashboard': 'Overview',
  'camera-attendance-session': 'Camera attendance',
  'faculty-mark-attendance': 'Camera attendance',
  'faculty-manual-attendance': 'Manual attendance',
  'faculty-timetable': "Today's classes",
  'student-attendance-tracker': 'Class roster',
  'faculty-approvals': 'Request review',
  'faculty-analytics': 'Analytics & students',
  'faculty-announcements': 'Announcements',
  'faculty-settings': 'Settings',
  'admin-users': 'User directory',
  'admin-students': 'Student accounts',
  'admin-faculty': 'Faculty accounts',
  'admin-academic-structure': 'Academic structure',
  'admin-academic-years': 'Academic years',
  'admin-semesters': 'Semesters',
  'admin-sections': 'Sections',
  'admin-courses': 'Courses',
  'admin-allocations': 'Faculty allocations',
  'admin-classrooms': 'Classrooms',
  'admin-timetable': 'Timetable management',
  'department-roster': 'Departments & students',
  'institutional-health-admin': 'Overview',
  'admin-dashboard': 'Overview',
  governance: 'Academic governance',
  'admin-governance': 'Academic governance',
  'system-logs-settings': 'System settings & audit',
};

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const {
    currentRole,
    currentUser,
    currentRoute,
    setCurrentRoute,
    notifications,
    signOut,
  } = useApp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const unreadCount = notifications.filter((notification) => notification.unread).length;

  const navigate = (route: string) => {
    setCurrentRoute(route);
    setMobileMenuOpen(false);
  };

  return (
    <div className="ams-shell">
      {mobileMenuOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="ams-backdrop lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside className={`ams-sidebar ${mobileMenuOpen ? 'ams-sidebar-open' : ''}`}>
        <div className="ams-brand">
          <button type="button" className="ams-brand-button" onClick={() => navigate(roleHome[currentRole])}>
            <span className="ams-brand-mark"><GraduationCap size={20} /></span>
            <span>
              <span className="ams-brand-name">SPIT Attendance</span>
              <span className="ams-brand-subtitle">Attendance Management System</span>
            </span>
          </button>
          <button
            type="button"
            className="ams-icon-button ams-sidebar-close lg:hidden"
            aria-label="Close navigation"
            onClick={() => setMobileMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="ams-navigation-label">{currentRole} workspace</div>
        <nav className="ams-navigation" aria-label={`${currentRole} navigation`}>
          {navigation[currentRole].map(({ label, route, icon: Icon }) => {
            const active = currentRoute === route ||
              (route === 'leave-medical-slips' && currentRoute.startsWith('regularization')) ||
              (route === 'camera-attendance-session' && currentRoute === 'faculty-mark-attendance') ||
              (route === 'institutional-health-admin' && currentRoute === 'admin-dashboard');
            return (
              <button
                key={route}
                type="button"
                aria-current={active ? 'page' : undefined}
                className={`ams-nav-item ${active ? 'ams-nav-item-active' : ''}`}
                onClick={() => navigate(route)}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span>{label}</span>
                {route === 'notification-center' && unreadCount > 0 && (
                  <span className="ams-nav-count">{unreadCount}</span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="ams-sidebar-bottom">
          <div className="ams-demo-note">Signed in · {currentRole}</div>
          <div className="ams-user-row">
            <span className="ams-avatar" aria-hidden="true">{currentUser.initials}</span>
            <span className="ams-user-copy">
              <span className="ams-user-name">{currentUser.name}</span>
              <span className="ams-user-id">{currentUser.rollOrEmpId}</span>
            </span>
            <button
              type="button"
              className="ams-icon-button"
              aria-label="Sign out"
              onClick={() => { void signOut(); }}
              title="Sign out"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <div className="ams-workspace">
        <header className="ams-topbar">
          <div className="ams-topbar-title">
            <button
              type="button"
              className="ams-icon-button lg:hidden"
              aria-label="Open navigation"
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu size={19} />
            </button>
            <span className="ams-crumb-root">SPIT AMS</span>
            <span className="ams-crumb-divider" aria-hidden="true">/</span>
            <span className="ams-crumb-current">{routeNames[currentRoute] ?? 'Overview'}</span>
          </div>
          <div className="ams-topbar-actions">
            <button
              type="button"
              className="ams-icon-button ams-notification-button"
              aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
              onClick={() => navigate(currentRole === 'student' ? 'notification-center' : 'notification-center')}
              title="Notifications"
            >
              <Bell size={18} />
              {unreadCount > 0 && <span className="ams-notification-dot" />}
            </button>
          </div>
        </header>
        <main className="ams-main">{children}</main>
      </div>
    </div>
  );
};
