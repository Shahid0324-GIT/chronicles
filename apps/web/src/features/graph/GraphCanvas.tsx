"use client";
import { useEffect, useRef, useState } from "react";
import Sigma, { DEFAULT_STYLES } from "sigma";
import {
  extremityArrow,
  layerFill,
  pathCurved,
  pathLine,
  sdfCircle,
  sdfDiamond,
  sdfRectangle,
  sdfSquare,
  sdfTriangle,
} from "sigma/rendering";
import { layerImage } from "@sigma/node-image";
import type { UniverseGraph } from "@/lib/contracts";
import { useExplorationApi } from "@/stores/ExplorationProvider";
import { DEFAULT_CAMERA, type CameraCommand } from "@/stores/exploration";
import { CameraDirector } from "@/animations/CameraDirector";
import { reduceMotion } from "@/animations/useAtlasMotion";
import {
  adaptGraph,
  type AtlasNodeAttributes,
  type AtlasEdgeAttributes,
} from "./adapter";
import { filterGraph } from "./filter";
import { NODE_IDENTITIES, NODE_TYPES } from "./identity";
import type { Point } from "./layout";

export default function GraphCanvas({ data }: { data: UniverseGraph }) {
  const container = useRef<HTMLDivElement>(null),
    overlay = useRef<HTMLDivElement>(null);
  const store = useExplorationApi();
  const [failure, setFailure] = useState<string | null>(null);
  const [positions] = useState(() => new Map<string, Point>());
  useEffect(() => {
    if (!container.current) return;
    const model = adaptGraph(data, positions);
    model.positions.forEach((point, id) => positions.set(id, point));
    let selection = store.getState().selectedId,
      query = store.getState().query,
      emphasis = 1;
    let visible = new Set<string>(),
      neighbors = new Set<string>();
    const updateView = () => {
      const state = store.getState();
      visible = new Set(
        filterGraph(data, state.continuityId, state.types).nodes.map(
          (n) => n.id,
        ),
      );
      selection = state.selectedId;
      query = state.query.toLowerCase();
      neighbors = new Set(
        selection && model.graph.hasNode(selection)
          ? model.graph.neighbors(selection)
          : [],
      );
    };
    updateView();
    let compact = window.innerWidth <= 800;
    let revealing = new Set<string>(),
      revealAmount = 1;
    const active = (id: string) =>
      !selection || selection === id || neighbors.has(id);
    let renderer: Sigma<AtlasNodeAttributes, AtlasEdgeAttributes>;
    try {
      renderer = new Sigma<AtlasNodeAttributes, AtlasEdgeAttributes>(
        model.graph,
        container.current,
        {
          primitives: {
            nodes: {
              variables: { image: { type: "string", default: "" } },
              shapes: [
                sdfCircle(),
                sdfSquare(),
                sdfTriangle(),
                sdfDiamond(),
                sdfRectangle({ cornerRadius: 0.12 }),
              ],
              layers: [
                layerFill(),
                layerImage({
                  padding: 0.055,
                  textureManagerOptions: {
                    objectFit: "cover",
                    size: { mode: "max", value: 256 },
                  },
                }),
              ],
            },
            edges: {
              paths: [pathLine(), pathCurved({ curvature: 0.15 })],
              extremities: [extremityArrow({ lengthRatio: 4, widthRatio: 3 })],
            },
          },
          styles: {
            nodes: [
              DEFAULT_STYLES.nodes,
              {
                shape: { attribute: "shape" },
                labelPosition: "below",
                labelFont: "Georgia",
                labelSize: compact ? 11 : 13,
                labelColor: "#e0dfd0",
                labelVisibility: (attrs) =>
                  attrs.entity.id === selection
                    ? "visible"
                    : compact && attrs.entity.title.length > 17
                      ? "hidden"
                      : "auto",
                backdropVisibility: "hidden",
                opacity: (attrs) =>
                  (active(attrs.entity.id) ? 1 : 1 - 0.7 * emphasis) *
                  (revealing.has(attrs.entity.id) ? revealAmount : 1),
                visibility: (attrs) =>
                  visible.has(attrs.entity.id) ? "visible" : "hidden",
                size: (attrs) =>
                  attrs.size *
                  (compact ? 0.68 : 1) *
                  (attrs.entity.id === selection ? 1.2 : 1),
                labelBackgroundColor: "#0e1e23",
                labelBackgroundPadding: 4,
                color: { attribute: "color" },
              },
              {
                when: (attrs) =>
                  query.length > 0 &&
                  !(attrs.label + " " + attrs.entity.type)
                    .toLowerCase()
                    .includes(query),
                then: { opacity: 0.23 },
              },
            ],
            edges: [
              DEFAULT_STYLES.edges,
              {
                path: "curved",
                head: "arrow",
                labelColor: "#b4b5a0",
                labelFont: "Arial",
                labelSize: 9,
                labelBackgroundColor: "#102028",
                opacity: (attrs) =>
                  !selection
                    ? 0.5
                    : attrs.entity.source === selection ||
                        attrs.entity.target === selection
                      ? 0.5 + 0.5 * emphasis
                      : 0.12,
                visibility: (attrs) =>
                  visible.has(attrs.entity.source) &&
                  visible.has(attrs.entity.target)
                    ? "visible"
                    : "hidden",
                labelVisibility: (attrs) =>
                  selection &&
                  (attrs.entity.source === selection ||
                    attrs.entity.target === selection)
                    ? "visible"
                    : "hidden",
                size: (attrs) =>
                  attrs.size *
                  (selection &&
                  (attrs.entity.source === selection ||
                    attrs.entity.target === selection)
                    ? 1.6
                    : 1),
              },
            ],
            stage: { background: "transparent", cursor: "grab" },
          },
          settings: {
            itemSizesReference: "screen",
            stagePadding: compact ? 25 : 50,
            labelRenderedSizeThreshold: 0,
            renderEdgeLabels: true,
            enableEdgeEvents: true,
            enableCameraRotation: false,
            minCameraRatio: 0.25,
            maxCameraRatio: 3,
            zoomDuration: reduceMotion() ? 0 : 250,
            inertiaDuration: reduceMotion() ? 0 : 150,
            doubleClickZoomingDuration: reduceMotion() ? 0 : 250,
            allowInvalidContainer: true,
          },
        },
      );
    } catch {
      const frame = requestAnimationFrame(() =>
        setFailure(
          "This browser could not open the WebGL atlas. You can still find entries with search and follow their connections.",
        ),
      );
      return () => cancelAnimationFrame(frame);
    }
    const camera = renderer.getCamera();
    camera.setState(store.getState().camera);
    const director = new CameraDirector(camera);
    const project = () => {
      if (!overlay.current) return;
      for (const element of overlay.current.querySelectorAll<HTMLElement>(
        "[data-node-id]",
      )) {
        const id = element.dataset.nodeId!,
          point = model.positions.get(id);
        if (!point) continue;
        const p = renderer.graphToViewport(point),
          dimensions = renderer.getDimensions();
        element.hidden = !(
          visible.has(id) &&
          p.x > 0 &&
          p.x < dimensions.width &&
          p.y > 0 &&
          p.y < dimensions.height
        );
        element.style.transform =
          "translate(" + p.x + "px," + p.y + "px) translate(-50%,-50%)";
      }
      for (const element of overlay.current.querySelectorAll<HTMLElement>(
        "[data-cluster]",
      )) {
        const type = element.dataset.cluster as keyof typeof NODE_IDENTITIES;
        const [x, y] = NODE_IDENTITIES[type].center;
        const p = renderer.graphToViewport({
          x,
          y: y + (type === "CHARACTER" ? 245 : 85),
        });
        element.style.transform =
          "translate(" + p.x + "px," + p.y + "px) translate(-50%,-50%)";
      }
    };
    const onCamera = () => {
      store.getState().setCamera(camera.getState());
      project();
    };
    const command = () => {
      const state = store.getState(),
        current = camera.getState(),
        kind = state.cameraRequest.command;
      if (
        kind === "focus" &&
        state.selectedId &&
        model.graph.hasNode(state.selectedId)
      ) {
        const point = renderer.graphToFramedGraph(
          model.positions.get(state.selectedId)!,
        );
        director.move({
          ...point,
          x: point.x + (window.innerWidth > 800 ? 0.12 : 0),
          y: point.y + (window.innerWidth <= 800 ? -0.12 : 0),
          ratio: 0.7,
        });
        director.highlight((value) => {
          emphasis = value;
          renderer.refresh({ skipIndexation: true });
        });
      } else if (kind === "reset") director.move(DEFAULT_CAMERA);
      else if (kind === "zoom-in" || kind === "zoom-out")
        director.move({
          ratio: Math.max(
            0.25,
            Math.min(3, current.ratio * (kind === "zoom-in" ? 0.8 : 1.25)),
          ),
        });
      else if (kind.startsWith("pan-"))
        director.move({
          x:
            current.x +
            (kind === "pan-right" ? 0.12 : kind === "pan-left" ? -0.12 : 0) *
              current.ratio,
          y:
            current.y +
            (kind === "pan-up" ? 0.12 : kind === "pan-down" ? -0.12 : 0) *
              current.ratio,
        });
    };
    const unsubscribe = store.subscribe((state, before) => {
      if (
        state.selectedId !== before.selectedId ||
        state.continuityId !== before.continuityId ||
        state.types !== before.types ||
        state.query !== before.query ||
        state.journeyIndex !== before.journeyIndex
      ) {
        updateView();
        renderer.refresh({ skipIndexation: true });
        project();
      }
      if (state.cameraRequest.version !== before.cameraRequest.version)
        command();
      if (state.discoveredIds !== before.discoveredIds) {
        revealing = new Set(
          state.discoveredIds.filter(
            (id) => !before.discoveredIds.includes(id),
          ),
        );
        director.reveal((value) => {
          revealAmount = value;
          renderer.refresh({ skipIndexation: true });
        });
      }
    });
    renderer.on("clickNode", ({ node }) => store.getState().selectNode(node));
    renderer.on("clickEdge", ({ edge }) => {
      store.getState().selectEdge(edge);
    });
    renderer.on("clickStage", () => store.getState().clearSelection());
    renderer.on("afterRender", project);
    camera.on("updated", onCamera);
    const interrupt = () => director.interrupt(),
      host = container.current;
    host.addEventListener("pointerdown", interrupt);
    host.addEventListener("wheel", interrupt, { passive: true });
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const motionChange = () => {
      director.interrupt();
      renderer.setSettings({
        zoomDuration: reduced.matches ? 0 : 250,
        inertiaDuration: reduced.matches ? 0 : 150,
      });
    };
    reduced.addEventListener("change", motionChange);
    const breakpoint = window.matchMedia("(max-width: 800px)");
    const resizeVisuals = () => {
      compact = breakpoint.matches;
      renderer.setSetting("stagePadding", compact ? 25 : 50);
      renderer.refresh();
      project();
    };
    breakpoint.addEventListener("change", resizeVisuals);
    renderer.refresh();
    project();
    return () => {
      unsubscribe();
      director.dispose();
      camera.off("updated", onCamera);
      host.removeEventListener("pointerdown", interrupt);
      host.removeEventListener("wheel", interrupt);
      reduced.removeEventListener("change", motionChange);
      breakpoint.removeEventListener("change", resizeVisuals);
      renderer.kill();
    };
  }, [data, store, positions]);
  return (
    <div
      className="graph-region"
      role="region"
      aria-label="Interactive universe map"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        const keys: Record<string, CameraCommand> = {
          ArrowLeft: "pan-left",
          ArrowRight: "pan-right",
          ArrowUp: "pan-up",
          ArrowDown: "pan-down",
          "+": "zoom-in",
          "=": "zoom-in",
          "-": "zoom-out",
          Home: "reset",
        };
        if (keys[e.key]) {
          e.preventDefault();
          store.getState().requestCamera(keys[e.key]);
        }
      }}
    >
      <div
        ref={container}
        className="sigma-container"
        data-testid="sigma-canvas"
      />
      <div ref={overlay} className="graph-accessibility-overlay">
        {NODE_TYPES.filter((type) =>
          data.nodes.some((n) => n.type === type),
        ).map((type) => (
          <span
            key={type}
            data-cluster={type}
            className="cluster-label"
            aria-hidden="true"
          >
            {NODE_IDENTITIES[type].label}
          </span>
        ))}
        {data.nodes.map((node) => (
          <button
            key={node.id}
            data-node-id={node.id}
            hidden
            className="graph-hit-target"
            aria-label={"Explore " + node.title}
            onClick={() => store.getState().selectNode(node.id)}
            title={node.title}
          />
        ))}
      </div>
      {failure && (
        <p className="graph-failure" role="status">
          {failure}
        </p>
      )}
    </div>
  );
}
