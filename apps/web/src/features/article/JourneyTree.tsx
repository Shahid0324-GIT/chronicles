"use client";
import { useEffect } from "react";
import {
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  useStore,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { JourneyStep } from "@/features/narrative/contracts";
import {
  branchShape,
  journeyTree,
  stopId,
  STOP_GAP,
  treeHeight,
  type Stop,
} from "./journey";

type StopData = {
  mark: string;
  title: string;
  label: string;
  state: "chosen" | "reached" | "hidden";
  pick: () => void;
};
type MomentData = { order: number; title: string; pick: () => void };
type StopNode = Node<StopData, "stop">;
type MomentNode = Node<MomentData, "moment">;

function StopView({ data }: NodeProps<StopNode>) {
  return (
    <div className={`tree-stop ${data.state}`}>
      <Handle type="target" position={Position.Left} />
      <button
        type="button"
        aria-label={data.label}
        aria-current={data.state === "chosen" ? "step" : undefined}
      >
        {data.mark}
      </button>
      <span>{data.title}</span>
      <Handle type="source" position={Position.Right} id="on" />
      <Handle type="source" position={Position.Bottom} id="down" />
    </div>
  );
}

function MomentView({ data }: NodeProps<MomentNode>) {
  return (
    <div className="tree-moment">
      <Handle type="target" position={Position.Top} id="top" />
      <Handle type="target" position={Position.Left} id="side-in" />
      <button type="button">
        <b>{data.order}</b>
        <span>{data.title}</span>
      </button>
      <Handle type="source" position={Position.Bottom} id="down" />
      <Handle type="source" position={Position.Right} id="side-out" />
    </div>
  );
}

const nodeTypes = { stop: StopView, moment: MomentView };

interface TreeProps {
  stops: Stop[];
  moments: JourneyStep[];
  chosen: number;
  unit: string;
  causes: { source: string; target: string }[];
  onStop: (position: number) => void;
  onMoment: (eventNodeId: string) => void;
}

function Tree({
  stops,
  moments,
  chosen,
  unit,
  causes,
  onStop,
  onMoment,
}: TreeProps) {
  const flow = useReactFlow();
  const layout = journeyTree(stops, moments, chosen, causes);
  const nodes: (StopNode | MomentNode)[] = layout.nodes.map((node) => {
    const place = { id: node.id, position: { x: node.x, y: node.y } };
    if (node.kind === "stop") {
      const stop = stops.find((s) => stopId(s.position) === node.id)!;
      return {
        ...place,
        type: "stop",
        data: {
          mark: stop.hidden ? "?" : String(stop.position),
          title: stop.title,
          label: stop.hidden
            ? `Reveal the story up to ${unit} ${stop.position}`
            : `${unit} ${stop.position}: ${stop.title}`,
          state: stop.hidden
            ? "hidden"
            : stop.position === chosen
              ? "chosen"
              : "reached",
          pick: () => onStop(stop.position),
        },
      };
    }
    const order = moments.findIndex((m) => m.eventNodeId === node.id);
    return {
      ...place,
      type: "moment",
      data: {
        order: order + 1,
        title: moments[order].title,
        pick: () => onMoment(node.id),
      },
    };
  });
  const edges: Edge[] = layout.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    // The path runs sideways, branches grow downwards, causes cross between them.
    sourceHandle:
      edge.kind === "branch"
        ? "down"
        : edge.kind === "cause"
          ? "side-out"
          : "on",
    targetHandle:
      edge.kind === "branch" ? "top" : edge.kind === "cause" ? "side-in" : null,
    type: edge.kind === "branch" ? "smoothstep" : "default",
    animated: edge.kind === "cause",
    className: `tree-edge ${edge.kind}`,
  }));
  const index = stops.findIndex((s) => s.position === chosen);
  const count = moments.length;
  const width = useStore((s) => s.width),
    height = useStore((s) => s.height);
  // Bring the chosen stop to the middle, drawing back when its branches are too wide.
  useEffect(() => {
    if (index < 0) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const wide = branchShape(count).columns * 250 + 60;
    const zoom = Math.max(0.6, Math.min(1, width / wide));
    // The first stops stay near the left edge instead of leaving it empty.
    const x = Math.max(index * STOP_GAP + 48, width / zoom / 2 - 90);
    // Centred on the tree's own height, so its top stays in view.
    void flow.setCenter(x, height / zoom / 2 - 40, {
      zoom,
      duration: still ? 0 : 600,
    });
  }, [flow, index, count, width, height]);
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={(_, node) => (node.data as StopData | MomentData).pick()}
      defaultViewport={{ x: 40, y: 30, zoom: 1 }}
      minZoom={0.4}
      maxZoom={1.4}
      nodesDraggable={false}
      nodesConnectable={false}
      nodesFocusable={false}
      edgesFocusable={false}
      elementsSelectable={false}
      zoomOnScroll={false}
      preventScrolling={false}
    >
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export default function JourneyTree(props: TreeProps) {
  return (
    <div
      className="journey-tree"
      style={{ height: treeHeight(props.moments.length) }}
      role="region"
      aria-label="Journey map and story tree"
    >
      <ReactFlowProvider>
        <Tree {...props} />
      </ReactFlowProvider>
    </div>
  );
}
