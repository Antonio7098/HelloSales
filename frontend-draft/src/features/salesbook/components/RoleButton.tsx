export function RoleButton({
  selected, onClick, title, subtitle,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={`funnel-role ${selected ? "is-selected" : ""}`}
    >
      <span className="funnel-role-title">{title}</span>
      <span className="funnel-role-sub">{subtitle}</span>
    </button>
  );
}
