from __future__ import annotations

import io
from datetime import UTC, datetime
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.academic import (
    Course,
    CourseAllocation,
    Department,
    Section,
    StudentProfile,
)
from app.models.attendance import Attendance, AttendanceStatus
from app.models.timetable import Lecture, LectureStatus
from app.models.user import User
from app.services.analytics import course_counts, defaulter_list


def _base_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    bold_cell = ParagraphStyle(
        "BoldCell",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    danger_cell = ParagraphStyle(
        "DangerCell",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#b91c1c"),
    )
    success_cell = ParagraphStyle(
        "SuccessCell",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#15803d"),
    )
    header_cell = ParagraphStyle(
        "HeaderCell",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#ffffff"),
    )
    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "heading": heading_style,
        "body": body_style,
        "bold": bold_cell,
        "danger": danger_cell,
        "success": success_cell,
        "header": header_cell,
    }


def generate_defaulters_pdf(db: Session, allocation_id: UUID, threshold: float) -> bytes:
    """Generate official PDF defaulter list for a course allocation."""
    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise ValueError("Course allocation not found")

    course = db.get(Course, allocation.course_id)
    section = db.get(Section, allocation.section_id)
    faculty = db.get(User, allocation.faculty_id)
    defaulters = defaulter_list(db, allocation_id, threshold)

    conducted = (
        db.scalar(
            select(func.count(Lecture.id)).where(
                Lecture.allocation_id == allocation_id,
                Lecture.status == LectureStatus.CONDUCTED,
            )
        )
        or 0
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = _base_styles()
    story = []

    # Header
    story.append(Paragraph("ATTENDANCE MANAGEMENT SYSTEM", styles["subtitle"]))
    story.append(Paragraph("Course Defaulter Notice & Report", styles["title"]))
    story.append(
        Paragraph(
            f"Generated on {datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')} · Official Academic Report",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=14))

    # Allocation Metadata Grid
    meta_data = [
        [
            Paragraph(f"<b>Course:</b> {course.code if course else ''} — {course.name if course else ''}", styles["body"]),
            Paragraph(f"<b>Section:</b> {section.name if section else ''}", styles["body"]),
        ],
        [
            Paragraph(f"<b>Faculty:</b> {faculty.full_name if faculty else ''}", styles["body"]),
            Paragraph(f"<b>Conducted Lectures:</b> {conducted}", styles["body"]),
        ],
        [
            Paragraph(f"<b>Attendance Threshold:</b> {threshold:.1f}%", styles["body"]),
            Paragraph(f"<b>Total Defaulters:</b> {len(defaulters)} students", styles["danger"] if defaulters else styles["body"]),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[300, 240])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Defaulter Table
    story.append(Paragraph(f"Students Below Required Threshold ({threshold:.1f}%)", styles["heading"]))

    if defaulters:
        table_rows = [
            [
                Paragraph("Roll / Institutional ID", styles["header"]),
                Paragraph("Student Full Name", styles["header"]),
                Paragraph("Attended", styles["header"]),
                Paragraph("Conducted", styles["header"]),
                Paragraph("Attendance Rate", styles["header"]),
                Paragraph("Status", styles["header"]),
            ]
        ]
        for row in defaulters:
            table_rows.append([
                Paragraph(row["institutional_id"], styles["body"]),
                Paragraph(row["full_name"], styles["bold"]),
                Paragraph(str(row["attended_lectures"]), styles["body"]),
                Paragraph(str(row["conducted_lectures"]), styles["body"]),
                Paragraph(f"{row['attendance_percentage']:.1f}%", styles["danger"]),
                Paragraph("DEFAULTER", styles["danger"]),
            ])

        data_table = Table(table_rows, colWidths=[120, 160, 60, 60, 80, 60])
        data_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#fef2f2")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(data_table)
    else:
        story.append(
            Paragraph(
                "✓ All enrolled students currently meet or exceed the attendance threshold for this course.",
                styles["success"],
            )
        )

    # Footer note
    story.append(Spacer(1, 24))
    story.append(
        Paragraph(
            "Note: Students listed as defaulters must submit regularization or medical slips to course faculty "
            "prior to the final examination eligibility deadline.",
            styles["subtitle"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def generate_institutional_defaulters_pdf(db: Session, threshold: float) -> bytes:
    """Generate institutional-wide defaulters list across all active course allocations."""
    allocations = db.execute(
        select(CourseAllocation.id, Course.code, Course.name, Section.name)
        .join(Course, Course.id == CourseAllocation.course_id)
        .join(Section, Section.id == CourseAllocation.section_id)
        .where(CourseAllocation.is_active.is_(True))
        .order_by(Course.code, Section.name)
    ).all()

    all_defaulters = []
    for alloc_id, course_code, course_name, sec_name in allocations:
        rows = defaulter_list(db, alloc_id, threshold)
        for r in rows:
            all_defaulters.append({
                **r,
                "course_code": course_code,
                "course_name": course_name,
                "section_name": sec_name,
            })

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = _base_styles()
    story = []

    story.append(Paragraph("ATTENDANCE MANAGEMENT SYSTEM", styles["subtitle"]))
    story.append(Paragraph("Institutional Defaulter Master Report", styles["title"]))
    story.append(
        Paragraph(
            f"Generated on {datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')} · Threshold: {threshold:.1f}%",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#b91c1c"), spaceAfter=14))

    # Summary
    story.append(
        Paragraph(
            f"Total Active Allocations Reviewed: <b>{len(allocations)}</b> &nbsp;|&nbsp; "
            f"Total Defaulter Incidents Recorded: <b style='color:#b91c1c;'>{len(all_defaulters)}</b>",
            styles["body"],
        )
    )
    story.append(Spacer(1, 12))

    if all_defaulters:
        table_rows = [
            [
                Paragraph("ID", styles["header"]),
                Paragraph("Student Name", styles["header"]),
                Paragraph("Course", styles["header"]),
                Paragraph("Section", styles["header"]),
                Paragraph("Attended / Total", styles["header"]),
                Paragraph("Rate", styles["header"]),
            ]
        ]
        for row in all_defaulters:
            table_rows.append([
                Paragraph(row["institutional_id"], styles["body"]),
                Paragraph(row["full_name"], styles["bold"]),
                Paragraph(f"{row['course_code']}", styles["body"]),
                Paragraph(row["section_name"], styles["body"]),
                Paragraph(f"{row['attended_lectures']} / {row['conducted_lectures']}", styles["body"]),
                Paragraph(f"{row['attendance_percentage']:.1f}%", styles["danger"]),
            ])

        data_table = Table(table_rows, colWidths=[90, 150, 80, 80, 80, 60])
        data_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(data_table)
    else:
        story.append(
            Paragraph("No students are currently below the attendance threshold across any courses.", styles["success"])
        )

    doc.build(story)
    return buffer.getvalue()


def generate_student_attendance_pdf(db: Session, student_id: UUID) -> bytes:
    """Generate comprehensive student attendance transcript and defaulter status report."""
    student = db.get(User, student_id)
    if not student:
        raise ValueError("Student not found")

    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    dept = db.get(Department, profile.department_id) if profile and profile.department_id else None
    section = db.get(Section, profile.section_id) if profile and profile.section_id else None

    # Get course counts
    courses = course_counts(db, student_id)
    total_conducted = sum(c["conducted_lectures"] for c in courses)
    total_attended = sum(c["attended_lectures"] for c in courses)
    overall_percentage = round((total_attended / total_conducted * 100), 2) if total_conducted else 100.0

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = _base_styles()
    story = []

    story.append(Paragraph("OFFICIAL ATTENDANCE TRANSCRIPT", styles["subtitle"]))
    story.append(Paragraph("Student Attendance & Eligibility Statement", styles["title"]))
    story.append(
        Paragraph(
            f"Issued on {datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')} · Institutional Document",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=14))

    # Student Info Grid
    student_meta = [
        [
            Paragraph(f"<b>Student Name:</b> {student.full_name}", styles["body"]),
            Paragraph(f"<b>Institutional ID:</b> {student.institutional_id}", styles["body"]),
        ],
        [
            Paragraph(f"<b>Email:</b> {student.email}", styles["body"]),
            Paragraph(f"<b>Department:</b> {dept.name if dept else 'General'}", styles["body"]),
        ],
        [
            Paragraph(f"<b>Section:</b> {section.name if section else 'N/A'}", styles["body"]),
            Paragraph(f"<b>Overall Attendance:</b> <b>{overall_percentage:.1f}%</b> ({total_attended}/{total_conducted})", styles["danger"] if overall_percentage < 75 else styles["success"]),
        ],
    ]
    meta_table = Table(student_meta, colWidths=[270, 270])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Course Breakdown Table
    story.append(Paragraph("Enrolled Courses & Attendance Status", styles["heading"]))
    course_rows = [
        [
            Paragraph("Course Code", styles["header"]),
            Paragraph("Course Name", styles["header"]),
            Paragraph("Conducted", styles["header"]),
            Paragraph("Attended", styles["header"]),
            Paragraph("Percentage", styles["header"]),
            Paragraph("Standing", styles["header"]),
        ]
    ]

    for c in courses:
        is_defaulter = c["attendance_percentage"] < 75.0
        course_rows.append([
            Paragraph(c["course_code"], styles["body"]),
            Paragraph(c["course_name"], styles["bold"]),
            Paragraph(str(c["conducted_lectures"]), styles["body"]),
            Paragraph(str(c["attended_lectures"]), styles["body"]),
            Paragraph(f"{c['attendance_percentage']:.1f}%", styles["danger"] if is_defaulter else styles["body"]),
            Paragraph("DEFAULTER" if is_defaulter else "ELIGIBLE", styles["danger"] if is_defaulter else styles["success"]),
        ])

    data_table = Table(course_rows, colWidths=[90, 190, 65, 65, 70, 60])
    data_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(data_table)

    # Recent Attendance Activity (last 15 records)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Recent Attendance Records", styles["heading"]))

    recent = db.execute(
        select(Lecture.starts_at, Course.code, Course.name, Attendance.status)
        .select_from(Attendance)
        .join(Lecture, Lecture.id == Attendance.lecture_id)
        .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
        .join(Course, Course.id == CourseAllocation.course_id)
        .where(Attendance.student_id == student_id)
        .order_by(Lecture.starts_at.desc())
        .limit(15)
    ).all()

    if recent:
        history_rows = [
            [
                Paragraph("Date & Time", styles["header"]),
                Paragraph("Course", styles["header"]),
                Paragraph("Status", styles["header"]),
            ]
        ]
        for starts_at, code, name, att_status in recent:
            st_text = att_status.value if hasattr(att_status, "value") else str(att_status)
            style_to_use = styles["success"] if st_text in {"PRESENT", "EXCUSED"} else styles["danger"]
            history_rows.append([
                Paragraph(starts_at.strftime("%Y-%m-%d %H:%M"), styles["body"]),
                Paragraph(f"{code} — {name}", styles["body"]),
                Paragraph(st_text, style_to_use),
            ])
        hist_table = Table(history_rows, colWidths=[140, 280, 120])
        hist_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(hist_table)
    else:
        story.append(Paragraph("No individual attendance entries recorded yet.", styles["subtitle"]))

    doc.build(story)
    return buffer.getvalue()
