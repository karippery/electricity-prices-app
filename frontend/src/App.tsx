import { useEffect, useState } from 'react';
import axios from 'axios';
import DatePicker from './components/DatePicker';
import PriceChart from './components/PriceChart';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import DaySummaryTable from './components/DaySummaryTable';
import { getToday } from './utils/dateUtils';
import type { ApiResponse, ChartDataPoint } from './types/api';

const API_BASE_URL = 'http://localhost:8000/api/prices';

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
        `${API_BASE_URL}/${date}`,
        { 
          params: { include_metadata: false },
          headers: { Accept: 'application/json' }
        }
      );
      setData(response.data);
    } catch {
      setError('Failed to load price data. Please try again.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/${selectedDate}/export-csv`,
        {
          responseType: 'blob',
          headers: { Accept: 'text/csv' },
        }
      );

      downloadFile(response.data, `prices_${selectedDate}.csv`);
    } catch {
      setError('Failed to export CSV. Please try again.');
    }
  };

  const downloadFile = (blobData: Blob, fileName: string) => {
    const url = window.URL.createObjectURL(new Blob([blobData]));
    const link = document.createElement('a');
    
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const prepareChartData = (): ChartDataPoint[] => {
    if (!data) return [];

    const selectedDayMap = createHourPriceMap(data.selected_day.hours);
    const previousDayMap = createHourPriceMap(data.previous_day?.hours || []);
    const nextDayMap = createHourPriceMap(data.next_day?.hours || []);

    const allHourLabels = getAllHourLabels(data);
    const sortedLabels = sortHourLabelsChronologically(allHourLabels);

    return sortedLabels.map(label => ({
      time: label,
      selected: selectedDayMap.get(label) ?? null,
      previous: previousDayMap.get(label) ?? null,
      next: nextDayMap.get(label) ?? null,
    }));
  };

  const createHourPriceMap = (hours: Array<{ hour_label: string; is_missing: boolean; price_eur_mwh: number | null }>) => {
    return new Map(
      hours.map(hour => [
        hour.hour_label,
        hour.is_missing ? null : hour.price_eur_mwh,
      ])
    );
  };

  const getAllHourLabels = (apiData: ApiResponse): string[] => {
    const hourLabels = new Set<string>();
    
    apiData.selected_day.hours.forEach(hour => hourLabels.add(hour.hour_label));
    apiData.previous_day?.hours?.forEach(hour => hourLabels.add(hour.hour_label));
    apiData.next_day?.hours?.forEach(hour => hourLabels.add(hour.hour_label));
    
    return Array.from(hourLabels);
  };

  const sortHourLabelsChronologically = (labels: string[]): string[] => {
    return [...labels].sort((a, b) => {
      const valueA = getSortableHourValue(a);
      const valueB = getSortableHourValue(b);
      return valueA - valueB;
    });
  };

  const getSortableHourValue = (hourLabel: string): number => {
    // Handle DST transition labels: "02:00A" and "02:00B"
    if (hourLabel.includes('A')) {
      return parseInt(hourLabel.replace('A', ''), 10) + 0.1;
    }
    if (hourLabel.includes('B')) {
      return parseInt(hourLabel.replace('B', ''), 10) + 0.2;
    }
    return parseInt(hourLabel, 10);
  };

  const chartData = prepareChartData();
  const showNoData = !loading && !error && !data;
  const showContent = !loading && !error && data && chartData.length > 0;

  return (
    <div className="min-h-screen bg-slate-100">
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="rounded-lg bg-white shadow-sm p-6">
          <Header />
          
          <section className="mb-6 flex justify-center">
            <DatePicker
              selectedDate={selectedDate}
              onChange={setSelectedDate}
              onExportCsv={handleExportCsv}
            />
          </section>

          <section>
            {loading && <LoadingState />}
            {error && <ErrorState message={error} />}
            {showContent && <Content data={data} chartData={chartData} />}
            {showNoData && <NoDataState />}
          </section>
        </div>
      </main>
    </div>
  );
}

const Header = () => (
  <header className="mb-8 text-center">
    <h1 className="text-3xl font-bold text-slate-900">
      Day-Ahead Electricity Prices
    </h1>
    <p className="mt-2 text-base text-slate-600">
      Austria, hourly price comparison
    </p>
  </header>
);

const LoadingState = () => (
  <div className="flex justify-center py-12">
    <LoadingSpinner />
  </div>
);

const ErrorState = ({ message }: { message: string }) => (
  <div className="mb-6">
    <ErrorMessage message={message} />
  </div>
);

const NoDataState = () => (
  <p className="py-12 text-center text-slate-500">
    No data available for the selected date.
  </p>
);

interface ContentProps {
  data: ApiResponse;
  chartData: ChartDataPoint[];
}

const Content = ({ data, chartData }: ContentProps) => (
  <>
    <div className="mb-10">
      <PriceChart chartData={chartData} />
    </div>
    <DaySummaryTable data={data} />
  </>
);

export default App;