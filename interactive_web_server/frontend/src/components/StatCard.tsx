interface StatCardProps {
  label: string;
  value: string | number;
  color: string;
}

export default function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow"
      style={{ borderLeft: `4px solid ${color}` }}
    >
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold" style={{ color }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  );
}
