import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BoardDiagnosisPage from '../BoardDiagnosisPage';

const { listBoardsMock, getDiagnosisMock } = vi.hoisted(() => ({
  listBoardsMock: vi.fn(),
  getDiagnosisMock: vi.fn(),
}));

vi.mock('../../api/boardDiagnosis', () => ({
  boardDiagnosisApi: {
    listBoards: (...args: unknown[]) => listBoardsMock(...args),
    getDiagnosis: (...args: unknown[]) => getDiagnosisMock(...args),
  },
}));

const boardsResponse = [
  {
    boardKey: 'new_energy',
    boardName: '新能源',
    market: 'CN',
    primaryEtf: { code: '159755', name: '新能源车ETF', role: 'etf', market: 'CN' },
    benchmarkIndex: { code: '399808', name: '新能源车指数', role: 'index', market: 'CN' },
    sectorNames: ['新能源车', '电池'],
    leaders: [
      { code: '300750', name: '宁德时代', role: 'leader', market: 'CN' },
      { code: '002594', name: '比亚迪', role: 'core', market: 'CN' },
      { code: '300274', name: '阳光电源', role: 'core', market: 'CN' },
    ],
  },
  {
    boardKey: 'liquor',
    boardName: '白酒',
    market: 'CN',
    primaryEtf: { code: '512690', name: '酒ETF', role: 'etf', market: 'CN' },
    benchmarkIndex: { code: '399997', name: '中证白酒指数', role: 'index', market: 'CN' },
    sectorNames: ['酿酒行业', '白酒'],
    leaders: [
      { code: '600519', name: '贵州茅台', role: 'leader', market: 'CN' },
      { code: '000858', name: '五粮液', role: 'core', market: 'CN' },
      { code: '600809', name: '山西汾酒', role: 'core', market: 'CN' },
    ],
  },
];

const diagnosisResponse = {
  boardKey: 'new_energy',
  boardName: '新能源',
  market: 'CN',
  primaryEtf: boardsResponse[0].primaryEtf,
  benchmarkIndex: boardsResponse[0].benchmarkIndex,
  leaders: boardsResponse[0].leaders,
  score: 82,
  action: 'buy',
  actionLabel: '买入',
  confidence: 'medium_high',
  confidenceLabel: '中高',
  summary: '当前板块综合信号偏强，ETF 可考虑分批买入。',
  reasons: ['ETF 份额较前值增加 5.00%', '3/3 核心股成交额高于 5 日均值'],
  risks: ['事件维度暂未接入公告结构化解析'],
  warnings: ['未获取到板块成交额快照'],
  dimensionScores: { index: 20, leaders: 24, sentiment: 14, capital: 15, events: 9 },
  dimensions: [
    {
      key: 'capital',
      label: '资金状态',
      score: 15,
      maxScore: 15,
      dataStatus: 'available',
      summary: '资金评分优先使用 ETF 份额变化、龙头量能和板块成交额；缺失项会显式降级。',
      evidence: ['ETF 份额较前值增加 5.00%（20260602 -> 20260603）'],
      risks: [],
      warnings: ['板块成交额来自盘中快照，收盘后可能回补'],
      metrics: {
        etfShareChangePct: 5,
        leaderAmountPositive: 3,
        sectorTurnoverAmount: 860,
      },
      sources: [
        {
          label: 'ETF 份额变化',
          provider: 'tushare.fund_share',
          detail: '单位：万份',
          tradeDate: '20260603',
          rangeStart: '20260602',
          rangeEnd: '20260603',
        },
        {
          label: '板块成交额快照',
          provider: 'efinance.sector_realtime_quotes',
          detail: '匹配板块：新能源车',
          tradeDate: null,
          rangeStart: null,
          rangeEnd: null,
        },
      ],
    },
  ],
  generatedAt: '2026-06-03T12:35:00Z',
};

describe('BoardDiagnosisPage', () => {
  beforeEach(() => {
    listBoardsMock.mockReset();
    getDiagnosisMock.mockReset();
  });

  it('loads boards and renders the default diagnosis result', async () => {
    listBoardsMock.mockResolvedValue(boardsResponse);
    getDiagnosisMock.mockResolvedValue(diagnosisResponse);

    render(<BoardDiagnosisPage />);

    expect(await screen.findByText('ETF板块决策')).toBeInTheDocument();
    expect(await screen.findByText('新能源')).toBeInTheDocument();
    await waitFor(() => expect(getDiagnosisMock).toHaveBeenCalledWith('new_energy'));
    await waitFor(() => expect(screen.getAllByText('买入').length).toBeGreaterThan(0));
    expect(screen.getAllByText(/ETF 份额较前值增加 5\.00%/).length).toBeGreaterThan(0);
    expect(screen.getByText('ETF份额变动')).toBeInTheDocument();
    expect(screen.getByText('5.00%')).toBeInTheDocument();
    expect(screen.getByText('860.00 亿元')).toBeInTheDocument();
    expect(screen.getByText('全部维度可用')).toBeInTheDocument();
    expect(screen.getByText('可用 1/1 · 降级 0/1')).toBeInTheDocument();
    expect(screen.getByText('已按北京时间展示')).toBeInTheDocument();
    expect(screen.getByText('板块成交额来自盘中快照，收盘后可能回补')).toBeInTheDocument();
    expect(screen.getByText('数据来源')).toBeInTheDocument();
    expect(screen.getByText('tushare.fund_share')).toBeInTheDocument();
    expect(screen.getByText(/时间范围：2026-06-02 -> 2026-06-03/)).toBeInTheDocument();
    expect(screen.getByText('匹配板块：新能源车')).toBeInTheDocument();
  });

  it('switches board and refreshes diagnosis when another board is selected', async () => {
    listBoardsMock.mockResolvedValue(boardsResponse);
    getDiagnosisMock
      .mockResolvedValueOnce(diagnosisResponse)
      .mockResolvedValueOnce({
        ...diagnosisResponse,
        boardKey: 'liquor',
        boardName: '白酒',
        primaryEtf: boardsResponse[1].primaryEtf,
        benchmarkIndex: boardsResponse[1].benchmarkIndex,
        leaders: boardsResponse[1].leaders,
        action: 'hold',
        actionLabel: '持有',
      });

    render(<BoardDiagnosisPage />);

    await screen.findByText('新能源');
    fireEvent.click(screen.getByRole('button', { name: /白酒/ }));

    await waitFor(() => expect(getDiagnosisMock).toHaveBeenCalledWith('liquor'));
    await waitFor(() => expect(screen.getAllByText('持有').length).toBeGreaterThan(0));
    expect(screen.getAllByText('贵州茅台').length).toBeGreaterThan(0);
  });

  it('shows error alert when board list fails to load', async () => {
    listBoardsMock.mockRejectedValue(new Error('板块列表不可用'));

    render(<BoardDiagnosisPage />);

    expect(await screen.findByText('板块列表不可用')).toBeInTheDocument();
    expect(getDiagnosisMock).not.toHaveBeenCalled();
  });
});
