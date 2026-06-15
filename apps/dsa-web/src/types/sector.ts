export interface SectorDashboardItem {
  etfCode: string;
  sectorName: string;
  tradeDate: string;
  ignitionScore: number;
  distributionScore: number;
  state: string;
  prevState?: string;
  stateReason?: string;
  stateEnteredDate?: string;
  marketRegime: string;
  ignitionDetails: Record<string, number>;
  distributionDetails: Record<string, number>;
}

export interface SectorDashboardResponse {
  tradeDate: string;
  marketRegime: string;
  items: SectorDashboardItem[];
}

export interface SectorHistoryItem {
  tradeDate: string;
  ignitionScore: number;
  distributionScore: number;
  state: string;
  prevState?: string;
  stateReason?: string;
  stateEnteredDate?: string;
  marketRegime: string;
}

export interface SectorHistoryResponse {
  etfCode: string;
  sectorName: string;
  history: SectorHistoryItem[];
}

export interface SectorPoolItem {
  id?: number;
  etfCode: string;
  sectorName: string;
  category?: string;
  benchmarkIndex?: string;
  isActive: boolean;
  createdAt?: string;
}
