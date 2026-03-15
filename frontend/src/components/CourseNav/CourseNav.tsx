/**
 * CourseNav — sidebar "Courses" section showing enrolled courses with assignment links.
 *
 * Fetches enrolled courses from GET /api/v1/courses on mount.
 * Shows empty state when no courses enrolled: prompts for enrollment code.
 * Each course links to /courses/{id}.
 */
import { useState, useEffect } from "react";
import { getCourses } from "../../api/courses";
import { Course } from "../../store/courseSlice";

interface Props {
  /** Called when user clicks a course link — receives the course ID. */
  onCourseSelect?: (courseId: string) => void;
  /** Currently active course ID (for highlighting). */
  activeCourseId?: string | null;
}

export function CourseNav({ onCourseSelect, activeCourseId }: Props) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCourses()
      .then(setCourses)
      .catch(() => setCourses([]))
      .finally(() => setLoading(false));
  }, []);

  const sectionHeaderStyle: React.CSSProperties = {
    color: "#6e7681",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.08em",
    marginBottom: 6,
    padding: "0 12px",
    textTransform: "uppercase",
  };

  if (loading) {
    return (
      <div style={{ padding: "0 12px 16px" }}>
        <div style={sectionHeaderStyle}>Courses</div>
        <div style={{ color: "#6e7681", fontSize: 13, padding: "4px 0" }}>
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div style={{ paddingBottom: 16 }}>
      <div style={sectionHeaderStyle}>Courses</div>

      {courses.length === 0 ? (
        <div
          style={{
            color: "#6e7681",
            fontSize: 12,
            fontStyle: "italic",
            lineHeight: 1.5,
            padding: "6px 12px",
          }}
        >
          No courses yet. Ask your instructor for an enrollment code.
        </div>
      ) : (
        <ul
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
          }}
        >
          {courses.map((course) => {
            const isActive = course.id === activeCourseId;
            return (
              <li key={course.id}>
                <button
                  onClick={() => onCourseSelect?.(course.id)}
                  style={{
                    background: isActive ? "#21262d" : "none",
                    border: "none",
                    borderRadius: 6,
                    color: isActive ? "#f0f6fc" : "#8b949e",
                    cursor: "pointer",
                    display: "block",
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    margin: "1px 8px",
                    padding: "6px 12px",
                    textAlign: "left",
                    transition: "background 0.1s, color 0.1s",
                    width: "calc(100% - 16px)",
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = "#161b22";
                      (e.currentTarget as HTMLButtonElement).style.color = "#c9d1d9";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = "none";
                      (e.currentTarget as HTMLButtonElement).style.color = "#8b949e";
                    }
                  }}
                >
                  <div style={{ fontWeight: isActive ? 600 : 500 }}>
                    {course.name}
                  </div>
                  {course.term && (
                    <div
                      style={{
                        color: "#6e7681",
                        fontSize: 11,
                        marginTop: 1,
                      }}
                    >
                      {course.term}
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
