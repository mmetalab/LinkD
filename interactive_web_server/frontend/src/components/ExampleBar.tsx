interface ExampleBarProps {
  examples: { label: string; [key: string]: string }[];
  onSelect: (example: Record<string, string>) => void;
}

export default function ExampleBar({ examples, onSelect }: ExampleBarProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      <span className="text-xs font-semibold text-gray-500 self-center">Examples:</span>
      {examples.map((ex, i) => (
        <button
          key={i}
          onClick={() => onSelect(ex)}
          className="px-3 py-1 text-xs bg-white border border-gray-300 rounded-full hover:bg-[#2171B5] hover:text-white hover:border-[#2171B5] transition-colors"
        >
          {ex.label}
        </button>
      ))}
    </div>
  );
}
