export interface HourData {
  timestamp_ms: number;
  hour_label: string;
  price_eur_mwh: number | null;
  price_ct_kwh: number | null;
  is_missing: boolean;
  is_dst_transition: boolean;
}

export interface DayData {
  date: string;
  hours: HourData[];
}

export interface ApiResponse {
  previous_day: DayData;
  selected_day: DayData;
  next_day: DayData;
}

export interface ChartDataPoint {
  time: string;
  previous: number | null;
  selected: number | null;
  next: number | null;
}
