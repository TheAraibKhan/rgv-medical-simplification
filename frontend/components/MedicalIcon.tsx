export type IconName =
  | "report"
  | "lungs"
  | "database"
  | "brain"
  | "shield"
  | "patient"
  | "clinician"
  | "arrow"
  | "search"
  | "spark"
  | "book"
  | "lock"
  | "menu"
  | "close"
  | "check"
  | "info"
  | "warning"
  | "x";

export function MedicalIcon({ name, size = 20 }: { name: IconName; size?: number }) {
  const shared = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.65,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  const paths: Record<IconName, React.ReactNode> = {
    report: <><path d="M6.75 3.5h7l4.5 4.5v12a.75.75 0 0 1-.75.75H6.5a.75.75 0 0 1-.75-.75v-15a.75.75 0 0 1 .75-.75Z" /><path d="M13.5 3.75v4.5h4.25M9 12h6M9 15.5h6" /></>,
    lungs: <><path d="M12 4v8M12 9c-1.8-2.1-3.1-2.8-4.3-2.1-1.2.7-1.5 2.7-2.5 5.2-1.1 2.7-.5 5.5 1.8 6.2 2.3.6 4.7-1.6 5-5.3M12 9c1.8-2.1 3.1-2.8 4.3-2.1 1.2.7 1.5 2.7 2.5 5.2 1.1 2.7.5 5.5-1.8 6.2-2.3.6-4.7-1.6-5-5.3" /></>,
    database: <><ellipse cx="12" cy="5" rx="7.5" ry="2.7" /><path d="M4.5 5v6c0 1.5 3.4 2.7 7.5 2.7s7.5-1.2 7.5-2.7V5M4.5 11v6c0 1.5 3.4 2.7 7.5 2.7s7.5-1.2 7.5-2.7v-6" /><path d="M8 8.2c1.2.5 2.6.7 4 .7" /></>,
    brain: <><rect x="5" y="5" width="14" height="14" rx="3" /><path d="M9 9h2v2H9zM14 13h2v2h-2zM11 10l3 3M12 5V3M7 5 6 3M17 5l1-2M12 19v2M7 19l-1 2M17 19l1 2M5 12H3M19 12h2" /></>,
    shield: <><path d="M12 3.5 19 6v5.4c0 4.2-2.8 7.5-7 9.1-4.2-1.6-7-4.9-7-9.1V6l7-2.5Z" /><path d="m8.7 12.1 2.1 2.1 4.6-4.8" /></>,
    patient: <><circle cx="9" cy="7" r="3" /><path d="M3.8 19.5v-1.2a5.2 5.2 0 0 1 5.2-5.2h.5a5.2 5.2 0 0 1 4.9 3.4M15 8h5M17.5 5.5v5M15.5 19.5h5M18 17v5" /></>,
    clinician: <><path d="M5 4.5h10l4 4v11H5z" /><path d="M14.5 4.8v4h4M8 12h7M8 15.5h4" /><path d="m16 17 1.4 1.4L20 16" /></>,
    arrow: <><path d="M4.5 12h14M13 6.5l5.5 5.5-5.5 5.5" /></>,
    search: <><circle cx="10.5" cy="10.5" r="6.2" /><path d="m15 15 4.5 4.5M10.5 7.5v6M7.5 10.5h6" /></>,
    spark: <><path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" /><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" /></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21V5.5Z" /><path d="M4 17a2.5 2.5 0 0 1 2.5-2.5H20M8 7h7" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3M12 14v3" /></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    check: <path d="m5 12.5 4.2 4.2L19 7" />,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
    warning: <><path d="M10.3 4.5 2.9 17.3A1.8 1.8 0 0 0 4.5 20h15a1.8 1.8 0 0 0 1.6-2.7L13.7 4.5a1.95 1.95 0 0 0-3.4 0Z" /><path d="M12 9v4M12 16.5h.01" /></>,
    x: <><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6m0-6-6 6" /></>,
  };

  return <svg {...shared}>{paths[name]}</svg>;
}
