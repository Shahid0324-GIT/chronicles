// Transport contracts only; no database or ORM dependency.
export type NodeType =
  | "CHARACTER"
  | "EVENT"
  | "LOCATION"
  | "LORE"
  | "FACTION"
  | "OBJECT"
  | "STORY_ARC"
  | "MYSTERY";
export type RelationshipType =
  | "PARTICIPATED_IN"
  | "OCCURRED_AT"
  | "CAUSED"
  | "REVEALED"
  | "BELONGS_TO"
  | "CONNECTED_TO"
  | "FORESHADOWS"
  | "ALLIED_WITH"
  | "CONTRADICTS"
  | "OPPOSED"
  | "MEMBER_OF"
  | "RELATED_TO"
  | "PRECEDES"
  | "ENABLED";
export interface Universe {
  id: string;
  slug: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
}
export interface Continuity {
  id: string;
  universe_id: string;
  name: string;
  medium: string;
  description: string;
}
export interface GraphNode {
  id: string;
  universe_id: string;
  continuity_id: string | null;
  type: NodeType;
  title: string;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
export interface GraphEdge {
  id: string;
  universe_id: string;
  continuity_id: string | null;
  source: string;
  target: string;
  relationship_type: RelationshipType;
  description: string;
}
export interface UniverseGraph {
  universe: Universe;
  continuities: Continuity[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}
export interface NodeDetails {
  node: GraphNode;
  edges: GraphEdge[];
}
