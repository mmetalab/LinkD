interface DownloadBarProps {
  onCSV?: () => void;
  onPNG?: () => void;
  onPDF?: () => void;
}

export default function DownloadBar({ onCSV, onPNG, onPDF }: DownloadBarProps) {
  return (
    <div className="flex gap-2 mt-3">
      {onCSV && (
        <button onClick={onCSV} className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 transition-colors">
          Download CSV
        </button>
      )}
      {onPNG && (
        <button onClick={onPNG} className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 transition-colors">
          Download PNG
        </button>
      )}
      {onPDF && (
        <button onClick={onPDF} className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 transition-colors">
          Download PDF
        </button>
      )}
    </div>
  );
}
