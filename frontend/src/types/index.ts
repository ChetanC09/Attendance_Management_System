export type UserRole = 'student' | 'faculty' | 'admin';

export interface UserProfile {
  id: string;
  name: string;
  rollOrEmpId: string;
  email: string;
  role: UserRole;
  department: string;
  semester?: string;
  avatarUrl?: string;
  initials: string;
}

export interface AttendanceRecord {
  id: string;
  courseCode: string;
  courseTitle: string;
  instructor: string;
  date: string;
  timeSlot: string;
  hallOrRoom: string;
  sessionTopic: string;
  status: 'present' | 'late' | 'absent' | 'excused';
  verificationMethod: 'vision' | 'manual' | 'regularization';
  disputeAvailable?: boolean;
}

export interface CourseStanding {
  code: string;
  title: string;
  credits: number;
  type: 'theory' | 'practical';
  instructor: string;
  hall: string;
  schedule: string;
  conducted: number;
  attended: number;
  excused: number;
  absent: number;
  percentage: number;
  bufferCushion: number; // how many classes can miss or need to attend
  standingStatus: 'healthy' | 'watchlist' | 'debarred';
  notes?: string;
  assignmentsComplete?: string;
}

export interface TimetableSlot {
  id: string;
  day: 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday';
  startTime: string;
  endTime: string;
  courseCode: string;
  courseName: string;
  type: 'lecture' | 'lab' | 'tutorial' | 'break';
  room: string;
  instructor: string;
  status: 'scheduled' | 'live' | 'upcoming' | 'cancelled' | 'rescheduled';
  cancelReason?: string;
  rescheduleNotice?: string;
}

export interface RegularizationRequest {
  id: string;
  studentId: string;
  studentName: string;
  rollNo: string;
  courseCode: string;
  courseName: string;
  sessionDate: string;
  sessionTime: string;
  hall: string;
  instructor: string;
  filingDate: string;
  requestType: 'leave' | 'regularization';
  narrative: string;

  status: 'approved' | 'under_review' | 'rejected' | 'draft';
  advisorEndorsement?: {
    advisorName: string;
    timestamp: string;
    comment: string;

  };
}

/** Matches backend/app/schemas/exceptions.py (frontend uses local camelCase models above). */
export interface RequestCreatePayload {
  lecture_id: string;
  request_type: 'LEAVE' | 'REGULARIZATION';
  reason: string;
}

export interface RequestReviewPayload {
  reason?: string;
}

export interface RequestResponseDTO {
  id: string;
  student_id: string;
  lecture_id: string | null;
  request_type: 'LEAVE' | 'REGULARIZATION';
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reason: string;
  reviewed_by: string | null;
  review_reason: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: 'warning' | 'timetable' | 'decision' | 'system' | 'announcement';
  courseCode?: string;
  timestamp: string;
  unread: boolean;
  linkText?: string;
  linkTarget?: string;
  badge?: string;
}

export interface DepartmentStat {
  code: string;
  name: string;
  facultyCount: number;
  enrolledStudents: number;
  meanAttendance: number;
  riskCount: number;
  riskPercentage: number;
}

export interface GovernancePolicy {
  minimumExamEligibility: number; // e.g., 75%
}

export interface ClassroomStudent {
  id: string;
  name: string;
  rollNo: string;
  seatNo: string;
  semesterRate: number;
  attendanceStatus: 'verified' | 'pending' | 'flag' | 'absent' | 'excused' | 'late';
  overrideType?: 'vision' | 'manual' | 'regularization';
  manualReason?: string;
  avatarUrl?: string;
  timeMarked?: string;
}

export interface EnrolledStudentCourse {
  code: string;
  name: string;
  conducted: number;
  attended: number;
  percentage: number;
  tier: 'safe' | 'condonation' | 'debarred';
  requiredToReach75: number;
}

export interface EnrolledStudent {
  id: string;
  name: string;
  rollNo: string;
  email: string;
  avatarUrl?: string;
  branch: string;
  semester: string;
  division: string;
  totalConducted: number;
  totalAttended: number;
  aggregatePercentage: number;
  tier: 'safe' | 'condonation' | 'debarred';
  pendingRegularizations: number;
  proctorName: string;
  proctorEmail: string;
  guardianPhone: string;
  courses: EnrolledStudentCourse[];
  medicalSlips: {
    id: string;
    date: string;
    reason: string;
    status: 'approved' | 'under_review' | 'rejected';
    sessionsImpacted: number;
  }[];
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  eventType: string;
  operator: string;
  role: string;
  details: string;
  severity: 'info' | 'warning' | 'critical' | 'success';
}

