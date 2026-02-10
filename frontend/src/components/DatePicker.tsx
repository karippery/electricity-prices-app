// src/components/DatePicker.tsx
import React from 'react';

interface DatePickerProps {
  selectedDate: string;
  onChange: (date: string) => void;
  onExportCsv?: () => void; // Optional export handler
}

const DatePicker: React.FC<DatePickerProps> = ({ selectedDate, onChange, onExportCsv }) => {
  return (
    <div className="flex items-center gap-3">
      {/* Date Picker */}
      <div className="flex flex-col">
        <label htmlFor="date" className="text-sm font-medium text-slate-700">
          Select date
        </label>
        <input
          id="date"
          type="date"
          value={selectedDate}
          onChange={(e) => onChange(e.target.value)}
          className="
            w-64
            rounded-lg
            border border-slate-300
            bg-white
            px-4 py-2.5
            text-base text-slate-800
            shadow-sm
            focus:border-blue-600
            focus:ring-2 focus:ring-blue-600
          "
        />
      </div>

      {/* Export Button */}
      {onExportCsv && (
        <button
          onClick={onExportCsv}
          className="
            self-end
            px-4 py-2.5
            bg-blue-600 text-white
            rounded-lg
            hover:bg-blue-700
            focus:outline-none focus:ring-2 focus:ring-blue-600
            transition-colors
            text-sm font-medium
          "
          aria-label="Export data as CSV"
        >
          Export CSV
        </button>
      )}
    </div>
  );
};

export default DatePicker;