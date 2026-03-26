import { COLORS } from '../styles/theme';

interface DataTableProps {
  data: Record<string, unknown>[];
  columns: string[];
  maxRows?: number;
}

function linkifyCell(col: string, val: unknown): string {
  const s = String(val ?? '');
  if ((col === 'drugId' || col === 'Drug') && s.startsWith('CHEMBL')) {
    return `<a href="https://www.ebi.ac.uk/chembl/compound_report_card/${s}" target="_blank" class="text-[${COLORS.primary}] hover:underline">${s}</a>`;
  }
  if (col === 'Gene' && s && s !== 'null' && s !== 'nan') {
    return `<a href="https://www.uniprot.org/uniprotkb?query=gene:${s}+AND+organism_id:9606" target="_blank" class="text-[${COLORS.primary}] hover:underline">${s}</a>`;
  }
  if ((col === 'ICD10' || col === 'icd_code') && s && s !== 'null') {
    return `<a href="https://icd.who.int/browse10/2019/en#/${s}" target="_blank" class="text-[${COLORS.primary}] hover:underline">${s}</a>`;
  }
  if (typeof val === 'number') return val.toFixed(4);
  return s.length > 60 ? s.slice(0, 57) + '...' : s;
}

export default function DataTable({ data, columns, maxRows = 100 }: DataTableProps) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400 italic text-sm">No data available.</p>;
  }

  const rows = data.slice(0, maxRows);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="max-h-[500px] overflow-auto">
        <table className="w-full text-xs border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-gray-100 border-b-2 border-gray-300">
              {columns.map(col => (
                <th key={col} className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={`border-b border-gray-100 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition-colors`}>
                {columns.map(col => (
                  <td
                    key={col}
                    className="px-3 py-1.5 text-gray-700 whitespace-nowrap"
                    dangerouslySetInnerHTML={{ __html: linkifyCell(col, row[col]) }}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length > maxRows && (
        <div className="px-3 py-1 text-xs text-gray-400 bg-gray-50 border-t">
          Showing {maxRows} of {data.length} rows
        </div>
      )}
    </div>
  );
}
