export type BoardAssetRole = 'etf' | 'index' | 'leader' | 'core';

export type BoardDecisionAction = 'buy' | 'hold' | 'reduce' | 'exit';

export type BoardDecisionConfidence = 'high' | 'medium_high' | 'medium' | 'low';

export type BoardSignalDataStatus = 'available' | 'partial' | 'estimated' | 'missing';

export interface BoardAssetRef {
  code: string;
  name: string;
  role: BoardAssetRole;
  market: string;
}

export interface BoardDefinitionSummary {
  boardKey: string;
  boardName: string;
  market: string;
  primaryEtf: BoardAssetRef;
  benchmarkIndex: BoardAssetRef;
  sectorNames: string[];
  leaders: BoardAssetRef[];
}

export interface BoardDiagnosisSource {
  label: string;
  provider: string | null;
  detail: string | null;
  tradeDate: string | null;
  rangeStart: string | null;
  rangeEnd: string | null;
}

export interface BoardDiagnosisDimension {
  key: string;
  label: string;
  score: number;
  maxScore: number;
  dataStatus: BoardSignalDataStatus;
  summary: string;
  evidence: string[];
  risks: string[];
  warnings: string[];
  metrics: Record<string, unknown>;
  sources: BoardDiagnosisSource[];
}

export interface BoardDiagnosisResult {
  boardKey: string;
  boardName: string;
  market: string;
  primaryEtf: BoardAssetRef;
  benchmarkIndex: BoardAssetRef;
  leaders: BoardAssetRef[];
  score: number;
  action: BoardDecisionAction;
  actionLabel: string;
  confidence: BoardDecisionConfidence;
  confidenceLabel: string;
  summary: string;
  reasons: string[];
  risks: string[];
  warnings: string[];
  dimensionScores: Record<string, number>;
  dimensions: BoardDiagnosisDimension[];
  generatedAt: string;
}
