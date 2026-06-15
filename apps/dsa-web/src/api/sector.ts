import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  SectorDashboardResponse,
  SectorHistoryResponse,
  SectorPoolItem,
} from '../types/sector';

export const sectorApi = {
  /**
   * 获取最新分析看板数据
   */
  getDashboard: async (tradeDate?: string): Promise<SectorDashboardResponse> => {
    const params: Record<string, string> = {};
    if (tradeDate) params.trade_date = tradeDate;
    const response = await apiClient.get<Record<string, unknown>>(
      '/api/v1/sector/dashboard',
      { params }
    );
    return toCamelCase<SectorDashboardResponse>(response.data);
  },

  /**
   * 获取单板块历史状态序列
   */
  getHistory: async (etfCode: string, limit: number = 60): Promise<SectorHistoryResponse> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/sector/${etfCode}/history`,
      { params: { limit } }
    );
    return toCamelCase<SectorHistoryResponse>(response.data);
  },

  /**
   * 手动触发板块拐点扫描
   */
  runScan: async (params: { tradeDate?: string; force?: boolean } = {}): Promise<any> => {
    const requestData: Record<string, unknown> = {};
    if (params.tradeDate) requestData.trade_date = params.tradeDate;
    if (params.force != null) requestData.force = params.force;
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/sector/scan',
      requestData
    );
    return toCamelCase<any>(response.data);
  },

  /**
   * 获取 ETF 板块池列表
   */
  getPool: async (): Promise<SectorPoolItem[]> => {
    const response = await apiClient.get<Record<string, unknown>[]>(
      '/api/v1/sector/pool'
    );
    return (response.data || []).map(item => toCamelCase<SectorPoolItem>(item));
  },

  /**
   * 添加或更新板块到 ETF 池
   */
  addOrUpdatePool: async (item: {
    etfCode: string;
    sectorName: string;
    category?: string;
    benchmarkIndex?: string;
    isActive?: boolean;
  }): Promise<SectorPoolItem> => {
    const requestData: Record<string, unknown> = {
      etf_code: item.etfCode,
      sector_name: item.sectorName,
      category: item.category || 'industry',
      benchmark_index: item.benchmarkIndex || null,
      is_active: item.isActive !== false,
    };
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/sector/pool',
      requestData
    );
    return toCamelCase<SectorPoolItem>(response.data);
  },

  /**
   * 从 ETF 池中删除板块
   */
  deleteFromPool: async (etfCode: string): Promise<{ status: string; message: string }> => {
    const response = await apiClient.delete<Record<string, unknown>>(
      `/api/v1/sector/pool/${etfCode}`
    );
    return toCamelCase<{ status: string; message: string }>(response.data);
  },
};
