import { useEffect, useState } from 'react';
import axios from 'axios';
import DatePicker from './components/DatePicker';
import PriceChart from './components/PriceChart';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import DaySummaryTable from './components/DaySummaryTable';
import { getToday } from './utils/dateUtils';
import type { ApiResponse, ChartDataPoint } from './types/api';

function App() {
  const [selectedDate, setSelectedDate] = useState(getToday());
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData(selectedDate);
  }, [selectedDate]);

  const fetchData = async (date: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get<ApiResponse>(
        `http://localhost:8000/api/prices/${date}?include_metadata=false`,
        { headers: { Accept: 'application/json' } }
      );
      setData(response.data);
    } catch {
      setError('Failed to load price data. Please try again.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const exportCsv = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/prices/${selectedDate}/export-csv`,
        {
          responseType: 'blob', // Important: expect binary data
          headers: {
            Accept: 'text/csv',
          },
        }
      );

      // Create a temporary link to trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `prices_${selectedDate}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export CSV. Please try again.');
    }
  };

  const prepareChartData = (): ChartDataPoint[] => {
    if (!data) return [];

    // Build lookup maps - use hour_label as key (not static 24-hour array)
    const selectedMap = new Map(
      data.selected_day.hours.map(h => [
        h.hour_label,  // Use backend's hour_label directly
        h.is_missing ? null : h.price_eur_mwh,
      ])
    );

    const prevMap = new Map(
      (data.previous_day?.hours || []).map(h => [
        h.hour_label,
        h.is_missing ? null : h.price_eur_mwh,
      ])
    );

    const nextMap = new Map(
      (data.next_day?.hours || []).map(h => [
        h.hour_label,
        h.is_missing ? null : h.price_eur_mwh,
      ])
    );

    // Get all unique hour labels from all three days
    const allHourLabels = Array.from(
      new Set([
        ...data.selected_day.hours.map(h => h.hour_label),
        ...(data.previous_day?.hours || []).map(h => h.hour_label),
        ...(data.next_day?.hours || []).map(h => h.hour_label),
      ])
    );

    // Sort labels chronologically (handles 2:00A, 2:00B correctly)
    const sortedLabels = allHourLabels.sort((a, b) => {
      // Helper to convert hour label to sortable number
      const labelToSortValue = (label: string) => {
        // Handle "02:00A" and "02:00B" for DST transition
        if (label.includes('A')) {
          return parseInt(label.replace('A', '')) + 0.1;
        }
        if (label.includes('B')) {
          return parseInt(label.replace('B', '')) + 0.2;
        }
        return parseInt(label);
      };
      return labelToSortValue(a) - labelToSortValue(b);
    });

    return sortedLabels.map(label => ({
      time: label,
      selected: selectedMap.get(label) ?? null,
      previous: prevMap.get(label) ?? null,
      next: nextMap.get(label) ?? null,
    }));
  };

  const chartData = prepareChartData();

  return (
    <div className="min-h-screen bg-slate-100">
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="rounded-lg bg-white shadow-sm p-6">
          <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-slate-900">
            Day-Ahead Electricity Prices
          </h1>
          <p className="mt-2 text-base text-slate-600">
            Austria, hourly price comparison
          </p>
        </header>

          <section className="mb-6 flex justify-center">
            <DatePicker
              selectedDate={selectedDate}
              onChange={setSelectedDate}
              onExportCsv={exportCsv}
            />
          </section>

          <section>
            {loading && (
              <div className="flex justify-center py-12">
                <LoadingSpinner />
              </div>
            )}

            {error && (
              <div className="mb-6">
                <ErrorMessage message={error} />
              </div>
            )}

            {!loading && !error && data && chartData.length > 0 && (
              <>
                <div className="mb-10">
                  <PriceChart chartData={chartData} />
                </div>

                <DaySummaryTable data={data} />
              </>
            )}

            {!loading && !error && !data && (
              <p className="py-12 text-center text-slate-500">
                No data available for the selected date.
              </p>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
