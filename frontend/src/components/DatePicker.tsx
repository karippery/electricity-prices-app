import React from 'react';

interface DatePickerProps {
  selectedDate: string;
  onChange: (date: string) => void;
}

const DatePicker: React.FC<DatePickerProps> = ({ selectedDate, onChange }) => {
  return (
    <div className="flex flex-col items-center gap-3">
      <label
        htmlFor="date"
        className="text-sm font-medium text-slate-700"
      >
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
  );
};

export default DatePicker;
