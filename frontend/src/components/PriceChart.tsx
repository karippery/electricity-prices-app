import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ChartDataPoint } from '../types/api';

interface PriceChartProps {
  chartData: ChartDataPoint[];
}

const PriceChart: React.FC<PriceChartProps> = ({ chartData }) => {
  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart
        data={chartData}
        margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
      >
        <CartesianGrid strokeDasharray="3 3" />

        {/* X = time */}
        <XAxis
          dataKey="time"
          interval={0}
          tick={{ fontSize: 11 }}
          angle={-45}
          textAnchor="end"
          height={60}
          label={{
            value: 'Hour',
            position: 'insideBottom',
            offset: -5,
          }}
        />

        {/* Y = price */}
        <YAxis
          tick={{ fontSize: 12 }}
          label={{
            value: 'Price (€/MWh)',
            angle: -90,
            position: 'insideLeft',
          }}
        />

        <Tooltip
          formatter={(value) =>
            typeof value === 'number'
              ? `${value.toFixed(2)} €/MWh`
              : 'Missing'
          }
          labelFormatter={(label) => `Hour: ${label}`}
        />

        <Legend />

        <Line
          type="monotone"
          dataKey="previous"
          name="Previous Day"
          stroke="#6366f1"
          dot={{ r: 2 }}
          activeDot={{ r: 5 }}
          connectNulls={false}
        />

        <Line
          type="monotone"
          dataKey="selected"
          name="Selected Day"
          stroke="#10b981"
          dot={{ r: 2 }}
          activeDot={{ r: 5 }}
          connectNulls={false}
        />

        <Line
          type="monotone"
          dataKey="next"
          name="Next Day"
          stroke="#f59e0b"
          dot={{ r: 2 }}
          activeDot={{ r: 5 }}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default PriceChart;
