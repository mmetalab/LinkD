interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, totalPages, total, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
      <span>{total.toLocaleString()} total results</span>
      <div className="flex items-center gap-2">
        <button onClick={() => onPageChange(page - 1)} disabled={page <= 1}
          className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed">
          Prev
        </button>
        <span>Page {page} of {totalPages}</span>
        <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}
          className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed">
          Next
        </button>
      </div>
    </div>
  );
}
