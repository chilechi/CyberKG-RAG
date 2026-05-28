export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  description: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QaEvidence {
  source: string;
  entity_id: string;
  text: string;
  score: number;
}

export interface QaAnswer {
  question: string;
  mode: string;
  answer: string;
  graph_paths: string[][];
  text_evidence: QaEvidence[];
  confidence: number;
}
