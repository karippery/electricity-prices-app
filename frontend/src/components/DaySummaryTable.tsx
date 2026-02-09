import React from 'react';
import type { ApiResponse } from '../types/api';

interface DaySummaryTableProps {
  data: ApiResponse;
}

const DaySummaryTable: React.FC<DaySummaryTableProps> = ({ data }) => {
  const calculateStats = (dayData: { date: string; hours: any[] }) => {
    const prices = dayData.hours
      .filter(h => !h.is_missing && h.price_eur_mwh != null)
      .map(h => h.price_eur_mwh as number);

    return {
      avg: prices.length ? (prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : '—',
      min: prices.length ? Math.min(...prices).toFixed(2) : '—',
      max: prices.length ? Math.max(...prices).toFixed(2) : '—',
      missing: dayData.hours.filter(h => h.is_missing).length,
      dst: dayData.hours.some(h => h.is_dst_transition) ? 'Yes' : 'No',
    };
  };

  const rows = [
    { label: 'Previous Day', day: data.previous_day, stats: calculateStats(data.previous_day) },
    { label: 'Selected Day', day: data.selected_day, stats: calculateStats(data.selected_day), highlight: true },
    { label: 'Next Day', day: data.next_day, stats: calculateStats(data.next_day) },
  ];

  return (
    <div className="mt-8 overflow-x-auto">
      <table className="min-w-full border border-slate-200 rounded-lg overflow-hidden">
        <thead className="bg-slate-100">
          <tr>
            {['Day', 'Avg €/MWh', 'Min', 'Max', 'Missing', 'DST'].map(h => (
              <th
                key={h}
                className="px-4 py-3 text-left text-sm font-semibold text-slate-700"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map(row => (
            <tr
              key={row.label}
              className={`
                border-t
                ${row.highlight ? 'bg-blue-50 font-medium' : 'hover:bg-slate-50'}
              `}
            >
              <td className="px-4 py-3">
                {row.label}
                <div className="text-xs text-slate-500">{row.day.date}</div>
              </td>
              <td className="px-4 py-3">{row.stats.avg}</td>
              <td className="px-4 py-3">{row.stats.min}</td>
              <td className="px-4 py-3">{row.stats.max}</td>
              <td className="px-4 py-3">{row.stats.missing}</td>
              <td className="px-4 py-3">{row.stats.dst}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DaySummaryTable;
