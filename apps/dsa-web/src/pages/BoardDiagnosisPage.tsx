/** ETF板块决策页：负责展示板块选择、综合结论和五维诊断细节。 */
import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Activity, Gauge, Landmark, RefreshCcw, TrendingUp } from 'lucide-react';
import { boardDiagnosisApi } from '../api/boardDiagnosis';
import {
  AppPage,
  Button,
  EmptyState,
  InlineAlert,
  Loading,
  PageHeader,
  ScoreGauge,
  SectionCard,
  StatCard,
} from '../components/common';
import type {
  BoardDefinitionSummary,
  BoardDiagnosisDimension,
  BoardDiagnosisResult,
  BoardDiagnosisSource,
  BoardSignalDataStatus,
} from '../types/boardDiagnosis';
import { createParsedApiError, isParsedApiError, parseApiError } from '../api/error';
import { cn } from '../utils/cn';

const STATUS_LABELS: Record<BoardSignalDataStatus, string> = {
  available: '可用',
  partial: '部分可用',
  estimated: '估算',
  missing: '缺失',
};

const STATUS_TONES: Record<BoardSignalDataStatus, string> = {
  available: 'text-success',
  partial: 'text-warning',
  estimated: 'text-cyan',
  missing: 'text-danger',
};

const ACTION_TONES: Record<BoardDiagnosisResult['action'], 'success' | 'primary' | 'warning' | 'danger'> = {
  buy: 'success',
  hold: 'primary',
  reduce: 'warning',
  exit: 'danger',
};

const METRIC_LABELS: Record<string, string> = {
  changePct: '涨跌幅',
  etfChangePct: 'ETF涨跌幅',
  indexChangePct: '指数涨跌幅',
  leaderChangePctAvg: '龙头平均涨幅',
  leaderStrengthRatio: '龙头走强占比',
  etfShareChangePct: 'ETF份额变动',
  leaderAmountPositive: '放量龙头数',
  leaderTurnoverPositive: '换手走强数',
  leaderVolumeRatioPositive: '量比走强数',
  sectorTurnoverAmount: '板块成交额',
  sectorTurnoverSharePct: '板块成交额占比',
  eventHitCount: '事件命中数',
  sentimentPositiveCount: '情绪正向数',
  sentimentNegativeCount: '情绪负向数',
};

function formatApiError(error: unknown) {
  const parsed = parseApiError(error);
  if (isParsedApiError(parsed)) {
    return parsed;
  }
  if (error instanceof Error) {
    return createParsedApiError({ title: '加载失败', message: error.message });
  }
  return createParsedApiError({ title: '加载失败', message: '请求失败，请稍后重试。' });
}

function formatMetricLabel(key: string): string {
  if (METRIC_LABELS[key]) {
    return METRIC_LABELS[key];
  }
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .trim();
}

function formatMetricValue(key: string, value: unknown): string {
  if (value == null || value === '' || Number.isNaN(Number(value))) {
    return '-';
  }
  const numeric = Number(value);
  if (key.toLowerCase().includes('pct') || key.toLowerCase().endsWith('ratio')) {
    return `${numeric.toFixed(2)}%`;
  }
  if (key.toLowerCase().includes('amount')) {
    return `${numeric.toFixed(2)} 亿元`;
  }
  if (
    key.toLowerCase().includes('count') ||
    key.toLowerCase().includes('positive') ||
    key.toLowerCase().includes('negative')
  ) {
    return `${Math.round(numeric)} 项`;
  }
  return numeric.toFixed(Math.abs(numeric) >= 100 ? 0 : 2);
}

function formatGeneratedAt(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  }).format(new Date(timestamp));
}

function formatCompactDate(value: string | null | undefined): string {
  if (!value) {
    return '-';
  }
  if (/^\d{8}$/.test(value)) {
    return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
  }
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  }).format(new Date(timestamp));
}

function buildSourceTimeLabel(source: BoardDiagnosisSource): string | null {
  if (source.rangeStart && source.rangeEnd) {
    return `${formatCompactDate(source.rangeStart)} -> ${formatCompactDate(source.rangeEnd)}`;
  }
  if (source.tradeDate) {
    return formatCompactDate(source.tradeDate);
  }
  return null;
}

const MetricPill: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-xl border border-subtle bg-surface/80 px-3 py-2">
    <div className="text-[11px] uppercase tracking-[0.2em] text-secondary-text">{label}</div>
    <div className="mt-1 text-sm font-medium text-foreground">{value}</div>
  </div>
);

const SourceCard: React.FC<{ source: BoardDiagnosisSource }> = ({ source }) => {
  const timeLabel = buildSourceTimeLabel(source);
  return (
    <div className="rounded-xl border border-subtle bg-surface/70 px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-foreground">{source.label}</div>
          {source.detail ? <div className="mt-1 text-xs text-secondary-text">{source.detail}</div> : null}
        </div>
        {source.provider ? (
          <span className="rounded-full bg-cyan/10 px-2.5 py-1 text-[11px] font-medium text-cyan">{source.provider}</span>
        ) : null}
      </div>
      {timeLabel ? <div className="mt-2 text-xs text-secondary-text">时间范围：{timeLabel}</div> : null}
    </div>
  );
};

const DimensionCard: React.FC<{ dimension: BoardDiagnosisDimension }> = ({ dimension }) => {
  const metricEntries = useMemo(
    () =>
      Object.entries(dimension.metrics)
        .filter(([, value]) => ['number', 'string'].includes(typeof value))
        .slice(0, 4),
    [dimension.metrics],
  );

  return (
    <div className="rounded-2xl border border-subtle bg-card/80 p-4 shadow-soft-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-foreground">{dimension.label}</div>
          <div className="mt-1 text-xs text-secondary-text">{dimension.summary}</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold text-foreground">
            {dimension.score}
            <span className="text-sm text-secondary-text"> / {dimension.maxScore}</span>
          </div>
          <div className={cn('mt-1 text-xs font-medium', STATUS_TONES[dimension.dataStatus])}>
            {STATUS_LABELS[dimension.dataStatus]}
          </div>
        </div>
      </div>

      {metricEntries.length > 0 ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {metricEntries.map(([key, value]) => (
            <MetricPill key={key} label={formatMetricLabel(key)} value={formatMetricValue(key, value)} />
          ))}
        </div>
      ) : null}

      {dimension.sources.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-secondary-text">数据来源</div>
          <div className="space-y-2">
            {dimension.sources.map((source, index) => (
              <SourceCard
                key={`${dimension.key}-${source.label}-${source.provider ?? 'unknown'}-${index}`}
                source={source}
              />
            ))}
          </div>
        </div>
      ) : null}

      {dimension.evidence.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-secondary-text">正向证据</div>
          <div className="space-y-2">
            {dimension.evidence.slice(0, 3).map((item) => (
              <div key={item} className="rounded-xl bg-success/10 px-3 py-2 text-sm text-foreground">
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {dimension.risks.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-secondary-text">风险提示</div>
          <div className="space-y-2">
            {dimension.risks.slice(0, 3).map((item) => (
              <div key={item} className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-foreground">
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {dimension.warnings.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-secondary-text">运行告警</div>
          <div className="space-y-2">
            {dimension.warnings.slice(0, 3).map((item) => (
              <div key={item} className="rounded-xl bg-warning/10 px-3 py-2 text-sm text-foreground">
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
};

const BoardDiagnosisPage: React.FC = () => {
  const [boards, setBoards] = useState<BoardDefinitionSummary[]>([]);
  const [selectedBoardKey, setSelectedBoardKey] = useState('');
  const [diagnosis, setDiagnosis] = useState<BoardDiagnosisResult | null>(null);
  const [boardsLoading, setBoardsLoading] = useState(true);
  const [diagnosisLoading, setDiagnosisLoading] = useState(false);
  const [boardsError, setBoardsError] = useState('');
  const [diagnosisError, setDiagnosisError] = useState('');

  const activeBoard = useMemo(
    () => boards.find((item) => item.boardKey === selectedBoardKey) ?? null,
    [boards, selectedBoardKey],
  );

  const diagnosisStatusSummary = useMemo(() => {
    if (!diagnosis) {
      return null;
    }
    const availableCount = diagnosis.dimensions.filter((item) => item.dataStatus === 'available').length;
    const degradedCount = diagnosis.dimensions.length - availableCount;
    return {
      availableCount,
      degradedCount,
      label: degradedCount === 0 ? '全部维度可用' : `${degradedCount} 个维度降级`,
      hint: `可用 ${availableCount}/${diagnosis.dimensions.length} · 降级 ${degradedCount}/${diagnosis.dimensions.length}`,
      tone: degradedCount === 0 ? ('success' as const) : ('warning' as const),
    };
  }, [diagnosis]);

  const loadDiagnosis = async (boardKey: string) => {
    setDiagnosisLoading(true);
    setDiagnosisError('');
    try {
      const result = await boardDiagnosisApi.getDiagnosis(boardKey);
      setDiagnosis(result);
    } catch (error) {
      const parsed = formatApiError(error);
      setDiagnosis(null);
      setDiagnosisError(parsed.message);
    } finally {
      setDiagnosisLoading(false);
    }
  };

  useEffect(() => {
    let active = true;

    const loadBoards = async () => {
      setBoardsLoading(true);
      setBoardsError('');
      try {
        const result = await boardDiagnosisApi.listBoards();
        if (!active) {
          return;
        }
        setBoards(result);
        if (result.length > 0) {
          const defaultBoardKey = result[0].boardKey;
          setSelectedBoardKey(defaultBoardKey);
          void loadDiagnosis(defaultBoardKey);
        }
      } catch (error) {
        if (!active) {
          return;
        }
        const parsed = formatApiError(error);
        setBoardsError(parsed.message);
      } finally {
        if (active) {
          setBoardsLoading(false);
        }
      }
    };

    void loadBoards();

    return () => {
      active = false;
    };
  }, []);

  const handleBoardChange = (boardKey: string) => {
    if (boardKey === selectedBoardKey) {
      return;
    }
    setSelectedBoardKey(boardKey);
    void loadDiagnosis(boardKey);
  };

  const handleRefresh = () => {
    if (selectedBoardKey) {
      void loadDiagnosis(selectedBoardKey);
    }
  };

  return (
    <AppPage className="space-y-6 pb-12 pt-6">
      <PageHeader
        eyebrow="ETF Board Diagnosis"
        title="ETF板块决策"
        description="基于指数、3只核心股、板块情绪、资金与事件催化，输出 ETF 的买入、持有、减仓或清仓建议。"
        actions={(
          <Button onClick={handleRefresh} disabled={!selectedBoardKey || diagnosisLoading} variant="secondary">
            <RefreshCcw className="mr-2 h-4 w-4" />
            刷新诊断
          </Button>
        )}
      />

      {boardsError ? <InlineAlert variant="danger" title="板块列表加载失败" message={boardsError} /> : null}
      {diagnosisError ? <InlineAlert variant="danger" title="诊断结果加载失败" message={diagnosisError} /> : null}

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <SectionCard
          title="板块选择"
          subtitle="Universe"
          className="xl:sticky xl:top-6 xl:self-start"
        >
          {boardsLoading ? <Loading label="正在读取可用板块..." className="px-0" /> : null}
          {!boardsLoading && boards.length === 0 ? (
            <EmptyState title="暂无板块配置" description="后端尚未返回可用板块，请先检查板块注册表。" />
          ) : null}
          {!boardsLoading && boards.length > 0 ? (
            <div className="space-y-3">
              {boards.map((board) => {
                const isActive = board.boardKey === selectedBoardKey;
                return (
                  <button
                    key={board.boardKey}
                    type="button"
                    onClick={() => handleBoardChange(board.boardKey)}
                    className={cn(
                      'w-full rounded-2xl border px-4 py-3 text-left transition-all',
                      isActive
                        ? 'border-cyan/40 bg-cyan/10 shadow-soft-card'
                        : 'border-subtle bg-card/70 hover:border-cyan/20 hover:bg-card',
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-foreground">{board.boardName}</div>
                        <div className="mt-1 text-xs text-secondary-text">
                          ETF {board.primaryEtf.code} · 指数 {board.benchmarkIndex.code}
                        </div>
                      </div>
                      <TrendingUp className={cn('h-4 w-4', isActive ? 'text-cyan' : 'text-secondary-text')} />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {board.leaders.map((leader) => (
                        <span key={leader.code} className="rounded-full bg-surface px-2.5 py-1 text-xs text-secondary-text">
                          {leader.name}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : null}
        </SectionCard>

        <div className="space-y-6">
          {diagnosisLoading && !diagnosis ? <Loading label="正在生成板块诊断..." /> : null}

          {!diagnosisLoading && !diagnosis && !boardsError ? (
            <EmptyState title="尚未生成诊断" description="请选择一个板块后查看结构化评分和决策建议。" />
          ) : null}

          {diagnosis ? (
            <>
              <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                <SectionCard title="ETF结论" subtitle="Decision">
                  <div className="flex flex-col items-center gap-4">
                    <ScoreGauge score={diagnosis.score} size="lg" />
                    <div className="text-center">
                      <div className="text-sm text-secondary-text">当前动作</div>
                      <div className="mt-1 text-3xl font-semibold text-foreground">{diagnosis.actionLabel}</div>
                      <div className="mt-2 text-sm text-secondary-text">置信度：{diagnosis.confidenceLabel}</div>
                    </div>
                  </div>
                </SectionCard>

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <StatCard
                    label="主ETF"
                    value={diagnosis.primaryEtf.name}
                    hint={diagnosis.primaryEtf.code}
                    icon={<Landmark className="h-5 w-5" />}
                  />
                  <StatCard
                    label="板块指数"
                    value={diagnosis.benchmarkIndex.name}
                    hint={diagnosis.benchmarkIndex.code}
                    icon={<Activity className="h-5 w-5" />}
                  />
                  <StatCard
                    label="综合动作"
                    value={diagnosis.actionLabel}
                    hint={diagnosis.summary}
                    tone={ACTION_TONES[diagnosis.action]}
                    icon={<Gauge className="h-5 w-5" />}
                  />
                  <StatCard
                    label="核心龙头"
                    value={diagnosis.leaders[0]?.name || '-'}
                    hint={diagnosis.leaders.map((item) => item.name).join(' / ')}
                    icon={<TrendingUp className="h-5 w-5" />}
                  />
                  <StatCard
                    label="生成时间"
                    value={formatGeneratedAt(diagnosis.generatedAt)}
                    hint="已按北京时间展示"
                    icon={<RefreshCcw className="h-5 w-5" />}
                  />
                  <StatCard
                    label="数据质量"
                    value={diagnosisStatusSummary?.label ?? '-'}
                    hint={diagnosisStatusSummary?.hint}
                    tone={diagnosisStatusSummary?.tone ?? 'default'}
                    icon={<Activity className="h-5 w-5" />}
                  />
                </div>
              </div>

              <SectionCard title="五维评分" subtitle="Dimensions">
                <div className="grid gap-4 xl:grid-cols-2">
                  {diagnosis.dimensions.map((dimension) => (
                    <DimensionCard key={dimension.key} dimension={dimension} />
                  ))}
                </div>
              </SectionCard>

              <div className="grid gap-6 xl:grid-cols-2">
                <SectionCard title="决策依据" subtitle="Reasons">
                  {diagnosis.reasons.length > 0 ? (
                    <div className="space-y-3">
                      {diagnosis.reasons.map((reason) => (
                        <div key={reason} className="rounded-xl bg-success/10 px-4 py-3 text-sm text-foreground">
                          {reason}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="暂无正向依据" description="当前诊断没有返回明确的正向证据。" />
                  )}
                </SectionCard>

                <SectionCard title="风险与告警" subtitle="Risks">
                  <div className="space-y-3">
                    {diagnosis.risks.map((risk) => (
                      <div key={risk} className="rounded-xl bg-danger/10 px-4 py-3 text-sm text-foreground">
                        {risk}
                      </div>
                    ))}
                    {diagnosis.warnings.map((warning) => (
                      <div key={warning} className="rounded-xl bg-warning/10 px-4 py-3 text-sm text-foreground">
                        {warning}
                      </div>
                    ))}
                    {diagnosis.risks.length === 0 && diagnosis.warnings.length === 0 ? (
                      <EmptyState title="暂无额外风险" description="当前诊断没有返回新增风险或运行告警。" />
                    ) : null}
                  </div>
                </SectionCard>
              </div>

              {activeBoard ? (
                <SectionCard title="板块映射" subtitle="Registry">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-2xl border border-subtle bg-card/70 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-secondary-text">主 ETF</div>
                      <div className="mt-2 text-lg font-semibold text-foreground">{activeBoard.primaryEtf.name}</div>
                      <div className="mt-1 text-sm text-secondary-text">{activeBoard.primaryEtf.code}</div>
                    </div>
                    <div className="rounded-2xl border border-subtle bg-card/70 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-secondary-text">指数</div>
                      <div className="mt-2 text-lg font-semibold text-foreground">{activeBoard.benchmarkIndex.name}</div>
                      <div className="mt-1 text-sm text-secondary-text">{activeBoard.benchmarkIndex.code}</div>
                    </div>
                    <div className="rounded-2xl border border-subtle bg-card/70 p-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-secondary-text">板块别名</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {activeBoard.sectorNames.map((name) => (
                          <span key={name} className="rounded-full bg-surface px-2.5 py-1 text-xs text-secondary-text">
                            {name}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </SectionCard>
              ) : null}
            </>
          ) : null}
        </div>
      </div>

      <InlineAlert
        variant="warning"
        title="交易提示"
        message="当前页面仅提供板块级 ETF 决策辅助，不构成投资建议；在真实交易前仍需结合你的持仓、仓位纪律和风险承受能力自行判断。"
      />
    </AppPage>
  );
};

export default BoardDiagnosisPage;
