import apiClient from './index';
import { toCamelCase } from './utils';
import type { BoardDefinitionSummary, BoardDiagnosisResult } from '../types/boardDiagnosis';

export const boardDiagnosisApi = {
  listBoards: async (): Promise<BoardDefinitionSummary[]> => {
    const response = await apiClient.get<Record<string, unknown>[] | Record<string, unknown>>(
      '/api/v1/board-diagnosis/boards',
    );
    return toCamelCase<BoardDefinitionSummary[]>(response.data);
  },

  getDiagnosis: async (boardKey: string): Promise<BoardDiagnosisResult> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/board-diagnosis/${boardKey}`);
    return toCamelCase<BoardDiagnosisResult>(response.data);
  },
};
