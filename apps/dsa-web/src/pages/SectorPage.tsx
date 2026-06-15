import type React from 'react';
import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  Compass,
  Database,
  Flame,
  History,
  LineChart as LineChartIcon,
  Loader2,
  Plus,
  Play,
  Settings,
  Trash2,
  X,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { sectorApi } from '../api/sector';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import {
  ApiErrorAlert,
  Badge,
  Button,
  Card,
  Drawer,
  EmptyState,
  InlineAlert,
  Loading,
} from '../components/common';
import { useUiLanguage } from '../contexts/UiLanguageContext';

import type {
  SectorDashboardItem,
  SectorDashboardResponse,
  SectorHistoryItem,
  SectorPoolItem,
} from '../types/sector';

const SectorPage: React.FC = () => {
  const { t } = useUiLanguage();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'pool'>('dashboard');

  // Dashboard state
  const [dashboardData, setDashboardData] = useState<SectorDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResultNotice, setScanResultNotice] = useState<{
    status: 'success' | 'failed' | 'skipped';
    message: string;
  } | null>(null);
  const [error, setError] = useState<ParsedApiError | null>(null);

  // Pool state
  const [poolItems, setPoolItems] = useState<SectorPoolItem[]>([]);
  const [isLoadingPool, setIsLoadingPool] = useState(false);
  const [isPoolModalOpen, setIsPoolModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Partial<SectorPoolItem> | null>(null);

  // History state (for details drawer)
  const [selectedSector, setSelectedSector] = useState<SectorDashboardItem | null>(null);
  const [historyItems, setHistoryItems] = useState<SectorHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Load Dashboard Data
  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await sectorApi.getDashboard();
      setDashboardData(res);
    } catch (err: any) {
      setError(getParsedApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load Pool Data
  const loadPool = useCallback(async () => {
    setIsLoadingPool(true);
    try {
      const res = await sectorApi.getPool();
      setPoolItems(res);
    } catch (err) {
      console.error('Failed to load sector pool:', err);
    } finally {
      setIsLoadingPool(false);
    }
  }, []);

  useEffect(() => {
    document.title = `${t('layout.nav.sector')} - DSA`;
    void loadDashboard();
  }, [loadDashboard, t]);

  useEffect(() => {
    if (activeTab === 'pool') {
      void loadPool();
    }
  }, [activeTab, loadPool]);

  // Run Sector Scan
  const handleRunScan = async (force: boolean = false) => {
    setIsScanning(true);
    setError(null);
    setScanResultNotice(null);
    try {
      const res = await sectorApi.runScan({ force });
      setScanResultNotice({
        status: res.status,
        message: `扫描完成！大盘开关: ${res.marketRegime === 'risk_on' ? 'Risk ON' : 'Risk OFF'} | 状态转移: ${res.transitionsCount} 个板块`,
      });
      await loadDashboard();
    } catch (err: any) {
      setError(getParsedApiError(err));
    } finally {
      setIsScanning(false);
    }
  };

  // View Sector History
  const handleViewHistory = async (item: SectorDashboardItem) => {
    setSelectedSector(item);
    setIsLoadingHistory(true);
    try {
      const res = await sectorApi.getHistory(item.etfCode);
      // Reverse history list so it reads chronologically left-to-right on chart
      setHistoryItems([...res.history].reverse());
    } catch (err) {
      console.error('Failed to load sector history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Add or Update Pool Item
  const handleSavePoolItem = async () => {
    if (!editingItem?.etfCode || !editingItem?.sectorName) return;
    try {
      await sectorApi.addOrUpdatePool({
        etfCode: editingItem.etfCode.trim(),
        sectorName: editingItem.sectorName.trim(),
        category: editingItem.category || 'industry',
        benchmarkIndex: editingItem.benchmarkIndex?.trim() || undefined,
        isActive: editingItem.isActive !== false,
      });
      await loadPool();
      setIsPoolModalOpen(false);
      setEditingItem(null);
    } catch (err) {
      console.error('Failed to save pool item:', err);
    }
  };

  // Toggle Pool Item Status
  const handleTogglePoolStatus = async (item: SectorPoolItem) => {
    try {
      await sectorApi.addOrUpdatePool({
        etfCode: item.etfCode,
        sectorName: item.sectorName,
        category: item.category,
        benchmarkIndex: item.benchmarkIndex,
        isActive: !item.isActive,
      });
      await loadPool();
    } catch (err) {
      console.error('Failed to toggle status:', err);
    }
  };

  // Delete Pool Item
  const handleDeletePoolItem = async (etfCode: string) => {
    if (!window.confirm(`确认从板块池中删除 ETF [${etfCode}] 吗？这也会删除其历史状态记录。`)) return;
    try {
      await sectorApi.deleteFromPool(etfCode);
      await loadPool();
    } catch (err) {
      console.error('Failed to delete pool item:', err);
    }
  };

  const getStatusBadge = (state: string) => {
    switch (state) {
      case 'holding':
        return <Badge variant="success" glow>持有中 (HOLD)</Badge>;
      case 'alert':
        return <Badge variant="warning" glow>警戒中 (ALERT)</Badge>;
      case 'lurking':
        return <Badge variant="default" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">潜伏观察 (LURK)</Badge>;
      case 'scanning':
        return <Badge variant="default" className="bg-blue-500/10 text-blue-500 border-blue-500/20">等待扫描 (SCAN)</Badge>;
      case 'exited':
        return <Badge variant="danger" glow>已离场 (EXIT)</Badge>;
      default:
        return <Badge variant="default">{state.toUpperCase()}</Badge>;
    }
  };

  const getStatusColorClass = (state: string) => {
    switch (state) {
      case 'holding':
        return 'border-emerald-500/30 shadow-emerald-500/5 hover:border-emerald-500/50';
      case 'alert':
        return 'border-amber-500/30 shadow-amber-500/5 hover:border-amber-500/50';
      case 'lurking':
        return 'border-yellow-500/30 shadow-yellow-500/5 hover:border-yellow-500/50';
      case 'scanning':
        return 'border-blue-500/30 shadow-blue-500/5 hover:border-blue-500/50';
      case 'exited':
        return 'border-rose-500/30 shadow-rose-500/5 hover:border-rose-500/50';
      default:
        return 'border-border/60 hover:border-border';
    }
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-base p-6">
      {/* Header */}
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold text-foreground">板块拐点监测</h1>
          <p className="text-sm text-secondary-text">监测 A股 行业 ETF 拐点信号：在聪明钱先行与量价突破时进场，在拥挤顶背离时分批离场。</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Tab Selection */}
          <div className="flex rounded-xl border border-border bg-card p-1">
            <button
              type="button"
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 rounded-lg px-4 py-1.5 text-xs font-medium transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-secondary-text hover:text-foreground'
              }`}
            >
              <Compass className="h-3.5 w-3.5" />
              分析看板
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('pool')}
              className={`flex items-center gap-2 rounded-lg px-4 py-1.5 text-xs font-medium transition-all ${
                activeTab === 'pool'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-secondary-text hover:text-foreground'
              }`}
            >
              <Database className="h-3.5 w-3.5" />
              ETF 池配置
            </button>
          </div>

          {activeTab === 'dashboard' && (
            <Button
              type="button"
              className="flex items-center gap-2"
              onClick={() => void handleRunScan(false)}
              disabled={isScanning || isLoading}
            >
              {isScanning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4 fill-current" />
              )}
              立即扫描
            </Button>
          )}
        </div>
      </div>

      {error && <ApiErrorAlert error={error} className="mb-6" />}
      {scanResultNotice && (
        <InlineAlert
          variant={scanResultNotice.status === 'success' ? 'success' : 'warning'}
          title="板块扫描反馈"
          message={scanResultNotice.message}
          action={
            <button
              type="button"
              onClick={() => setScanResultNotice(null)}
              className="text-secondary-text hover:text-foreground transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          }
          className="mb-6"
        />
      )}

      {/* TABS CONTAINER */}
      {activeTab === 'dashboard' ? (
        // DASHBOARD TAB
        <div className="space-y-6">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loading />
            </div>
          ) : !dashboardData || dashboardData.items.length === 0 ? (
            <EmptyState
              title="暂无板块分析记录"
              description="尚未运行过板块拐点监测扫描。点击右上角“立即扫描”运行第一次分析。"
            />
          ) : (
            <>
              {/* Regime Switch Banner */}
              <div
                className={`flex flex-col gap-4 rounded-2xl border p-5 md:flex-row md:items-center md:justify-between shadow-sm transition-all ${
                  dashboardData.marketRegime === 'risk_on'
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-950 dark:text-emerald-50'
                    : 'bg-rose-500/5 border-rose-500/20 text-rose-950 dark:text-rose-50'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-inner ${
                      dashboardData.marketRegime === 'risk_on'
                        ? 'bg-emerald-500/20 text-emerald-500'
                        : 'bg-rose-500/20 text-rose-500'
                    }`}
                  >
                    <Activity className="h-5 w-5 animate-pulse" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold">
                      大盘总开关 (Market Regime):{' '}
                      <span
                        className={
                          dashboardData.marketRegime === 'risk_on'
                            ? 'text-emerald-500'
                            : 'text-rose-500'
                        }
                      >
                        {dashboardData.marketRegime === 'risk_on' ? '🟢 RISK ON' : '🔴 RISK OFF'}
                      </span>
                    </h2>
                    <p className="mt-1 text-sm opacity-80">
                      {dashboardData.marketRegime === 'risk_on'
                        ? '大盘处于上行趋势（沪深300指数站于200日均线之上）。板块启动信号被允许正常触发并进场。'
                        : '警告：大盘处于弱势下行趋势（沪深300指数低于200日均线）。一票否决所有板块的买入与启动信号，禁止新开仓！'}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2 text-xs font-mono opacity-80">
                  <span>数据交易日: {dashboardData.tradeDate}</span>
                </div>
              </div>

              {/* Grid of Sector Cards */}
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {dashboardData.items.map((item) => {
                  return (
                    <Card
                      key={item.etfCode}
                      className={`relative flex flex-col justify-between border bg-card p-5 shadow-sm transition-all hover:-translate-y-1 hover:shadow-md cursor-pointer ${getStatusColorClass(
                        item.state
                      )}`}
                      onClick={() => void handleViewHistory(item)}
                    >
                      {/* Card Top */}
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <h3 className="text-base font-bold text-foreground truncate">
                              {item.sectorName}
                            </h3>
                            <span className="text-xs font-mono text-secondary-text">
                              {item.etfCode}
                            </span>
                          </div>
                          {getStatusBadge(item.state)}
                        </div>

                        {/* Scores */}
                        <div className="mt-6 grid grid-cols-2 gap-4 border-y border-border/40 py-3.5">
                          <div className="flex flex-col items-center border-r border-border/30">
                            <span className="flex items-center gap-1 text-xs text-secondary-text">
                              <Flame className="h-3 w-3 text-blue-500 fill-current" />
                              启动评分
                            </span>
                            <span className="mt-1 text-xl font-bold text-foreground">
                              {item.ignitionScore}
                              <span className="text-xs font-normal text-muted-text">/100</span>
                            </span>
                          </div>

                          <div className="flex flex-col items-center">
                            <span className="flex items-center gap-1 text-xs text-secondary-text">
                              <AlertTriangle className="h-3 w-3 text-orange-500" />
                              见顶评分
                            </span>
                            <span className="mt-1 text-xl font-bold text-foreground">
                              {item.distributionScore}
                              <span className="text-xs font-normal text-muted-text">/100</span>
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Card Bottom */}
                      <div className="mt-4 space-y-2">
                        {item.stateEnteredDate && (
                          <div className="flex items-center justify-between text-xs text-secondary-text">
                            <span>当前状态已持续:</span>
                            <span className="font-semibold text-foreground">
                              {Math.max(
                                1,
                                Math.floor(
                                  (new Date(item.tradeDate).getTime() -
                                    new Date(item.stateEnteredDate).getTime()) /
                                    (1000 * 60 * 60 * 24)
                                ) + 1
                              )}{' '}
                              天
                            </span>
                          </div>
                        )}
                        {item.stateReason && (
                          <div className="rounded-lg bg-base px-2.5 py-1.5 text-[11px] text-secondary-text border border-border/30 italic line-clamp-2">
                            “ {item.stateReason} ”
                          </div>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </>
          )}
        </div>
      ) : (
        // POOL CONFIGURATION TAB
        <div className="space-y-6">
          <div className="flex items-center justify-between bg-card border border-border/60 p-4 rounded-xl">
            <span className="text-sm font-medium text-secondary-text">
              活跃板块 ETF 池中共有 <strong className="text-foreground">{poolItems.length}</strong> 个标的
            </span>
            <Button
              type="button"
              className="flex items-center gap-1 text-xs"
              onClick={() => {
                setEditingItem({
                  etfCode: '',
                  sectorName: '',
                  category: 'industry',
                  benchmarkIndex: '',
                  isActive: true,
                });
                setIsPoolModalOpen(true);
              }}
            >
              <Plus className="h-3.5 w-3.5" />
              新增板块
            </Button>
          </div>

          {isLoadingPool ? (
            <div className="flex h-48 items-center justify-center">
              <Loading />
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-border bg-card">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border/80 bg-base text-xs font-semibold text-secondary-text uppercase">
                    <th className="px-6 py-4">板块名称</th>
                    <th className="px-6 py-4">ETF 代码</th>
                    <th className="px-6 py-4">指数代码</th>
                    <th className="px-6 py-4">分类</th>
                    <th className="px-6 py-4">启用状态</th>
                    <th className="px-6 py-4 text-right">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-sm text-foreground">
                  {poolItems.map((item) => (
                    <tr key={item.etfCode} className="hover:bg-hover/30 transition-colors">
                      <td className="px-6 py-4 font-semibold">{item.sectorName}</td>
                      <td className="px-6 py-4 font-mono">{item.etfCode}</td>
                      <td className="px-6 py-4 font-mono">{item.benchmarkIndex || '--'}</td>
                      <td className="px-6 py-4">
                        {item.category === 'industry' && <Badge variant="default">行业</Badge>}
                        {item.category === 'theme' && <Badge variant="default" className="bg-purple-500/10 text-purple-500 border-purple-500/20">主题</Badge>}
                        {item.category === 'safe_haven' && <Badge variant="default" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">避险</Badge>}
                      </td>
                      <td className="px-6 py-4">
                        <button
                          type="button"
                          onClick={() => void handleTogglePoolStatus(item)}
                          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                            item.isActive ? 'bg-primary' : 'bg-border'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                              item.isActive ? 'translate-x-5' : 'translate-x-0'
                            }`}
                          />
                        </button>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingItem(item);
                              setIsPoolModalOpen(true);
                            }}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-card text-secondary-text hover:bg-hover hover:text-foreground transition-colors"
                          >
                            <Settings className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDeletePoolItem(item.etfCode)}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-rose-500/20 bg-rose-500/5 text-rose-500 hover:bg-rose-500/10 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* DETAIL DRAWER FOR HISTORICAL DETAILS */}
      <Drawer
        isOpen={selectedSector !== null}
        onClose={() => {
          setSelectedSector(null);
          setHistoryItems([]);
        }}
        title={selectedSector ? `${selectedSector.sectorName} (${selectedSector.etfCode}) 历史演变` : ''}
        width="max-w-3xl"
      >
        <div className="space-y-6 p-6 overflow-y-auto h-full">
          {isLoadingHistory ? (
            <div className="flex h-64 items-center justify-center">
              <Loading />
            </div>
          ) : (
            <>
              {/* Metric Breakdown Area */}
              {selectedSector && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Card className="border border-border/60 bg-base p-4">
                    <h4 className="flex items-center gap-1.5 text-xs font-semibold text-secondary-text uppercase">
                      <Flame className="h-3.5 w-3.5 text-blue-500 fill-current" />
                      启动评分细项 (Ignition Details)
                    </h4>
                    <div className="mt-3 space-y-2 text-sm text-foreground">
                      <div className="flex justify-between">
                        <span>聪明钱仓位贡献:</span>
                        <span className="font-semibold">{selectedSector.ignitionDetails?.smp ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>底部箱体结构:</span>
                        <span className="font-semibold">{selectedSector.ignitionDetails?.bottom_structure ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>放量突破强度:</span>
                        <span className="font-semibold">{selectedSector.ignitionDetails?.volume_breakout ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>相对强度趋势:</span>
                        <span className="font-semibold">{selectedSector.ignitionDetails?.rs_trend ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>成分股上涨广度:</span>
                        <span className="font-semibold">{selectedSector.ignitionDetails?.breadth ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between border-t border-border/40 pt-2 font-bold">
                        <span>综合评分:</span>
                        <span className="text-blue-500">{selectedSector.ignitionScore} / 100</span>
                      </div>
                    </div>
                  </Card>

                  <Card className="border border-border/60 bg-base p-4">
                    <h4 className="flex items-center gap-1.5 text-xs font-semibold text-secondary-text uppercase">
                      <AlertTriangle className="h-3.5 w-3.5 text-orange-500" />
                      见顶评分细项 (Distribution Details)
                    </h4>
                    <div className="mt-3 space-y-2 text-sm text-foreground">
                      <div className="flex justify-between">
                        <span>聪明钱离场倾向:</span>
                        <span className="font-semibold">{selectedSector.distributionDetails?.smp ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>指标顶背离强度:</span>
                        <span className="font-semibold">{selectedSector.distributionDetails?.divergence ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>量价背离/滞涨:</span>
                        <span className="font-semibold">{selectedSector.distributionDetails?.volume_price_divergence ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>广度衰竭恶化:</span>
                        <span className="font-semibold">{selectedSector.distributionDetails?.breadth_decay ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between">
                        <span>均线支撑破位:</span>
                        <span className="font-semibold">{selectedSector.distributionDetails?.ma_break ?? 0} 分</span>
                      </div>
                      <div className="flex justify-between border-t border-border/40 pt-2 font-bold">
                        <span>综合评分:</span>
                        <span className="text-orange-500">{selectedSector.distributionScore} / 100</span>
                      </div>
                    </div>
                  </Card>
                </div>
              )}

              {/* History Score Line Chart */}
              <div className="rounded-xl border border-border bg-card p-4 shadow-inner">
                <h4 className="mb-4 flex items-center gap-1.5 text-xs font-semibold text-secondary-text uppercase">
                  <LineChartIcon className="h-3.5 w-3.5 text-primary" />
                  历史评分走势图
                </h4>
                <div className="h-64 w-full">
                  {historyItems.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-xs text-secondary-text">
                      暂无历史走势数据
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={historyItems} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorIgnition" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="colorDistribution" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f97316" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border) / 0.3)" />
                        <XAxis dataKey="tradeDate" stroke="hsl(var(--secondary-text))" fontSize={10} tickLine={false} />
                        <YAxis domain={[0, 100]} stroke="hsl(var(--secondary-text))" fontSize={10} tickLine={false} />
                        <ChartTooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: 'hsl(var(--border))',
                            color: 'hsl(var(--foreground))',
                            borderRadius: '0.75rem',
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        <Area
                          type="monotone"
                          dataKey="ignitionScore"
                          name="启动评分"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorIgnition)"
                        />
                        <Area
                          type="monotone"
                          dataKey="distributionScore"
                          name="见顶评分"
                          stroke="#f97316"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorDistribution)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              {/* History Event Log */}
              <div className="space-y-3">
                <h4 className="flex items-center gap-1.5 text-xs font-semibold text-secondary-text uppercase">
                  <History className="h-3.5 w-3.5 text-primary" />
                  状态变更及扫描日志
                </h4>

                <div className="relative border-l-2 border-border/60 ml-2.5 pl-6 space-y-6">
                  {historyItems.slice().reverse().map((r, idx) => {
                    const isStateTransition = r.state !== r.prevState;
                    return (
                      <div key={idx} className="relative">
                        {/* Dot Indicator */}
                        <div
                          className={`absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full border-2 bg-card ${
                            isStateTransition
                              ? r.state === 'holding'
                                ? 'border-emerald-500 text-emerald-500'
                                : r.state === 'alert'
                                  ? 'border-amber-500 text-amber-500'
                                  : r.state === 'exited'
                                    ? 'border-rose-500 text-rose-500'
                                    : 'border-blue-500 text-blue-500'
                              : 'border-border/60'
                          }`}
                        >
                          <div className={`h-1.5 w-1.5 rounded-full ${
                            isStateTransition
                              ? r.state === 'holding'
                                ? 'bg-emerald-500'
                                : r.state === 'alert'
                                  ? 'bg-amber-500'
                                  : r.state === 'exited'
                                    ? 'bg-rose-500'
                                    : 'bg-blue-500'
                              : 'bg-border/60'
                          }`} />
                        </div>

                        {/* Event Content */}
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-mono text-secondary-text">{r.tradeDate}</span>
                            <span className="font-mono text-[10px] text-muted-text">
                              大盘: {r.marketRegime === 'risk_on' ? '🟢 ON' : '🔴 OFF'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {getStatusBadge(r.state)}
                            {isStateTransition && r.prevState && (
                              <span className="text-xs text-secondary-text">
                                (从 {r.prevState.toUpperCase()} 转移)
                              </span>
                            )}
                            <span className="text-xs text-secondary-text font-mono">
                              (启动: {r.ignitionScore} | 见顶: {r.distributionScore})
                            </span>
                          </div>
                          {r.stateReason && (
                            <p className="text-xs text-secondary-text italic bg-hover/20 rounded-lg p-2 mt-0.5 border border-border/20">
                              {r.stateReason}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </Drawer>

      {/* POOL CREATE/EDIT MODAL */}
      {isPoolModalOpen && editingItem && (
        <div className="fixed inset-0 z-100 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
          <Card className="w-full max-w-md border border-border/80 bg-card p-6 shadow-2xl animate-scale-in">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-lg font-bold text-foreground">
                {editingItem.id ? '编辑板块配置' : '新增板块配置'}
              </h3>
              <button
                type="button"
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-secondary-text hover:bg-hover hover:text-foreground transition-colors"
                onClick={() => {
                  setIsPoolModalOpen(false);
                  setEditingItem(null);
                }}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-secondary-text uppercase mb-1.5">
                  板块名称 *
                </label>
                <input
                  type="text"
                  placeholder="如：半导体 ETF"
                  value={editingItem.sectorName || ''}
                  onChange={(e) => setEditingItem({ ...editingItem, sectorName: e.target.value })}
                  className="w-full rounded-xl border border-border bg-base px-4 py-2.5 text-sm transition-all focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-secondary-text uppercase mb-1.5">
                  ETF 代码 *
                </label>
                <input
                  type="text"
                  placeholder="如：512480"
                  disabled={!!editingItem.id}
                  value={editingItem.etfCode || ''}
                  onChange={(e) => setEditingItem({ ...editingItem, etfCode: e.target.value })}
                  className="w-full rounded-xl border border-border bg-base px-4 py-2.5 text-sm transition-all focus:border-primary focus:outline-none disabled:opacity-60"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-secondary-text uppercase mb-1.5">
                  成分股指数代码 (选填)
                </label>
                <input
                  type="text"
                  placeholder="如：H30184 (用于计算广度等，留空使用 ETF 自身)"
                  value={editingItem.benchmarkIndex || ''}
                  onChange={(e) => setEditingItem({ ...editingItem, benchmarkIndex: e.target.value })}
                  className="w-full rounded-xl border border-border bg-base px-4 py-2.5 text-sm transition-all focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-secondary-text uppercase mb-1.5">
                  板块类别
                </label>
                <select
                  value={editingItem.category || 'industry'}
                  onChange={(e) => setEditingItem({ ...editingItem, category: e.target.value })}
                  className="w-full rounded-xl border border-border bg-base px-4 py-2.5 text-sm transition-all focus:border-primary focus:outline-none"
                >
                  <option value="industry">行业 (Industry)</option>
                  <option value="theme">主题 (Theme)</option>
                  <option value="safe_haven">避险停泊 (Safe Haven)</option>
                </select>
              </div>

              <div className="flex items-center gap-3 py-2">
                <input
                  type="checkbox"
                  id="isActive"
                  checked={editingItem.isActive !== false}
                  onChange={(e) => setEditingItem({ ...editingItem, isActive: e.target.checked })}
                  className="h-4.5 w-4.5 rounded border-border bg-base text-primary focus:ring-primary"
                />
                <label htmlFor="isActive" className="text-sm text-foreground select-none cursor-pointer">
                  是否启用并运行扫描
                </label>
              </div>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setIsPoolModalOpen(false);
                  setEditingItem(null);
                }}
              >
                取消
              </Button>
              <Button
                type="button"
                onClick={handleSavePoolItem}
                disabled={!editingItem.etfCode || !editingItem.sectorName}
              >
                保存
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SectorPage;
