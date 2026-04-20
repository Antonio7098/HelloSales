type EntityBadgeProps = {
  label: string;
};

export function EntityBadge({ label }: EntityBadgeProps) {
  return <span className="entity-badge">{label}</span>;
}
