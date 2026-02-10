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

    return data.selected_day.hours.map((hour, index) => ({
      time: hour.hour_label,
      previous: data.previous_day?.hours?.[index]?.is_missing
        ? null
        : data.previous_day?.hours?.[index]?.price_eur_mwh ?? null,
      selected: hour.is_missing ? null : hour.price_eur_mwh,
      next: data.next_day?.hours?.[index]?.is_missing
        ? null
        : data.next_day?.hours?.[index]?.price_eur_mwh ?? null,
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
