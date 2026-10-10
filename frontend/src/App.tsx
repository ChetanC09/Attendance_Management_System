import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { AppShell } from './components/layout/AppShell';
import { ToastContainer } from './components/common/ToastContainer';
import { WorkflowPreviewView } from './components/common/WorkflowPreviewView';
import { LoginView } from './components/auth/LoginView';

// Student Views
import { StudentDashboardView } from './components/student/StudentDashboardView';
import { CourseAttendanceView } from './components/student/CourseAttendanceView';
import { TimetableView } from './components/student/TimetableView';
import { RegularizationListView } from './components/student/RegularizationListView';
import { RegularizationFormView } from './components/student/RegularizationFormView';
import { RegularizationDetailView } from './components/student/RegularizationDetailView';
import { AttendanceHistoryView } from './components/student/AttendanceHistoryView';
import { NotificationCenterView } from './components/student/NotificationCenterView';
import { RecoveryPlannerView } from './components/student/RecoveryPlannerView';

// Faculty Views
import { FacultyOverviewView } from './components/faculty/FacultyOverviewView';
import { FacultyMarkAttendanceView } from './components/faculty/FacultyMarkAttendanceView';
import { FacultyApprovalsView } from './components/faculty/FacultyApprovalsView';

// Admin Views
import { AdminDashboardView } from './components/admin/AdminDashboardView';
import { AdminGovernanceView } from './components/admin/AdminGovernanceView';
import { SystemLogsSettingsView } from './components/admin/SystemLogsSettingsView';
import { AdminResourceManager } from './components/admin/AdminResourceManager';
import { AdminUsersView } from './components/admin/AdminUsersView';
import { AdminLectureOperations } from './components/admin/AdminLectureOperations';
import { AccountSettingsView } from './components/common/AccountSettingsView';
import { FacultyAnalyticsView } from './components/faculty/FacultyAnalyticsView';
import { FacultyAnnouncementsView } from './components/faculty/FacultyAnnouncementsView';


const MainRouter: React.FC = () => {
  const { currentRoute, currentRole, authenticated, checkingSession } = useApp();

  if (checkingSession) return <div className="grid min-h-screen place-items-center text-sm text-slate-600">Loading your account…</div>;
  if (!authenticated) return <LoginView />;

  if (currentRoute === 'login') {
    return <LoginView />;
  }

  const adminRoute = currentRoute.startsWith('admin-') || ['institutional-health-admin', 'admin-dashboard', 'governance', 'admin-governance', 'system-logs-settings', 'department-roster'].includes(currentRoute);
  const facultyRoute = currentRoute.startsWith('faculty-') || ['faculty-workspace', 'faculty-dashboard', 'camera-attendance-session', 'faculty-mark-attendance', 'faculty-manual-attendance', 'student-attendance-tracker'].includes(currentRoute);
  if (adminRoute && currentRole !== 'admin') return <AppShell>{currentRole === 'faculty' ? <FacultyOverviewView /> : <StudentDashboardView />}</AppShell>;
  if (facultyRoute && currentRole !== 'faculty') return <AppShell>{currentRole === 'admin' ? <AdminDashboardView /> : <StudentDashboardView />}</AppShell>;
  if (!adminRoute && !facultyRoute && currentRole !== 'student') return <AppShell>{currentRole === 'admin' ? <AdminDashboardView /> : <FacultyOverviewView />}</AppShell>;

  const renderCurrentView = () => {
    if (currentRoute.startsWith('attendance-history/')) return <AttendanceHistoryView />;
    switch (currentRoute) {
      // Student Routes & Aliases
      case 'overview-dashboard':
      case 'student-dashboard':
        return <StudentDashboardView />;

      case 'course-attendance':
      case 'student-ledger':
        return <CourseAttendanceView />;

      case 'timetable-schedule':
      case 'timetable':
      case 'student-timetable':
        return <TimetableView />;

      case 'leave-medical-slips':
      case 'regularization':
      case 'student-regularization':
        return <RegularizationListView />;

      case 'regularization-form':
      case 'student-regularization-new':
        return <RegularizationFormView />;

      case 'regularization-detail':
      case 'student-regularization-detail':
        return <RegularizationDetailView />;

      case 'attendance-history':
      case 'student-history':
        return <AttendanceHistoryView />;

      case 'recovery-planner':
        return <RecoveryPlannerView />;

      case 'notification-center':
      case 'student-notifications':
        return <NotificationCenterView />;
      case 'student-settings':
        return <AccountSettingsView />;

      // Faculty Routes & Aliases
      case 'faculty-workspace':
      case 'faculty-dashboard':
        return <FacultyOverviewView />;

      case 'camera-attendance-session':
      case 'faculty-mark-attendance':
        return <FacultyMarkAttendanceView mode="camera" />;

      case 'faculty-manual-attendance':
        return <FacultyMarkAttendanceView mode="manual" />;

      case 'faculty-timetable':
        return <TimetableView />;

      case 'student-attendance-tracker':
        return <FacultyAnalyticsView />;

      case 'department-roster':
        return <AdminResourceManager route="admin-departments" />;

      case 'faculty-approvals':
        return <FacultyApprovalsView />;
      case 'faculty-analytics':
        return <FacultyAnalyticsView />;
      case 'faculty-announcements':
        return <FacultyAnnouncementsView />;
      case 'faculty-settings':
        return <AccountSettingsView />;

      // Admin Routes & Aliases
      case 'institutional-health-admin':
      case 'admin-dashboard':
        return <AdminDashboardView />;

      case 'system-logs-settings':
        return <SystemLogsSettingsView />;

      case 'governance':
      case 'admin-governance':
        return <AdminGovernanceView />;
      case 'admin-users':
        return <AdminUsersView />;
      case 'admin-students':
        return <AdminUsersView role="STUDENT" />;
      case 'admin-faculty':
        return <AdminUsersView role="FACULTY" />;
      case 'admin-academic-structure':
        return <WorkflowPreviewView title="Academic structure" description="Browse the academic entities used to organize courses and attendance." areas={[
          { label: 'Departments', route: 'admin-departments', detail: 'Create, edit, and activate academic departments.' },
          { label: 'Academic years', route: 'admin-academic-years', detail: 'Academic-year records and active periods.' },
          { label: 'Semesters', route: 'admin-semesters', detail: 'Semester dates and academic periods.' },
          { label: 'Sections', route: 'admin-sections', detail: 'Student sections and divisions.' },
          { label: 'Courses', route: 'admin-courses', detail: 'Course catalogue and course details.' },
          { label: 'Faculty allocations', route: 'admin-allocations', detail: 'Faculty, course, and section assignments.' },
          { label: 'Classrooms', route: 'admin-classrooms', detail: 'Classroom catalogue and availability.' },
          { label: 'Timetable', route: 'admin-timetable', detail: 'Scheduled classes and conflict review.' },
        ]} />;
      case 'admin-departments':
      case 'admin-academic-years':
      case 'admin-semesters':
      case 'admin-sections':
      case 'admin-courses':
      case 'admin-allocations':
      case 'admin-classrooms':
      case 'admin-timetable':
        return <><AdminResourceManager route={currentRoute} />{currentRoute === 'admin-timetable' && <AdminLectureOperations />}</>;

      default:
        return currentRole === 'faculty' ? <FacultyOverviewView /> :
          currentRole === 'admin' ? <AdminDashboardView /> : <StudentDashboardView />;
    }
  };

  return (
    <AppShell>
      {renderCurrentView()}
    </AppShell>
  );
};

export default function App() {
  return (
    <AppProvider>
      <MainRouter />
      <ToastContainer />
    </AppProvider>
  );
}
