"use client";

import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

type GraphNode = {
  id: string;
  label?: string;
  type?: string;
  risk?: number;
};

type GraphEdge = {
  id?: string;
  source: string;
  target: string;
  relation?: string;
  weight?: number;
  confidence?: number;
};

type GraphData = {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
};

export default function Graph({
  graph,
}: {
  graph?: GraphData | null;
}) {
  const { nodes, edges } = useMemo(() => {
    if (!graph) {
      return {
        nodes: [] as Node[],
        edges: [] as Edge[],
      };
    }

    const sourceNodes = Array.isArray(graph.nodes)
      ? graph.nodes
      : [];

    const validNodeIds = new Set(
      sourceNodes.map((node) => String(node.id))
    );

    const nodes: Node[] = sourceNodes.map((node, index) => ({
      id: String(node.id),
      position: {
        x: (index % 3) * 280 + 40,
        y: Math.floor(index / 3) * 155 + 40,
      },
      data: {
        label: (
          <div
            style={{
              minWidth: 170,
              textAlign: "center",
              padding: "4px",
            }}
          >
            <div
              style={{
                fontWeight: 700,
                fontSize: 14,
                marginBottom: 6,
              }}
            >
              {node.label || node.id}
            </div>

            <div
              style={{
                fontSize: 11,
                opacity: 0.8,
              }}
            >
              {node.type || "entity"}
              {" · "}
              risk {Number(node.risk ?? 0).toFixed(1)}
            </div>
          </div>
        ),
      },
      style: {
        background: "#101720",
        border: "1px solid #334155",
        borderRadius: 14,
        color: "#ffffff",
        width: 220,
        padding: 12,
      },
    }));

    const edges: Edge[] = (
      Array.isArray(graph.edges) ? graph.edges : []
    )
      .filter((edge) => {
        const source = String(edge.source);
        const target = String(edge.target);

        // Never render malformed graph edges.
        if (!source || !target) return false;

        // Never render self-loops.
        if (source === target) return false;

        // Only render edges whose endpoints actually exist.
        if (!validNodeIds.has(source)) return false;
        if (!validNodeIds.has(target)) return false;

        return true;
      })
      .map((edge, index) => ({
        id:
          edge.id ||
          `${String(edge.source)}-${String(edge.target)}-${index}`,
        source: String(edge.source),
        target: String(edge.target),
        type: "smoothstep",
        animated: false,
        label: edge.relation || "influences",
labelStyle: {
  fill: "#64748b",
  fontSize: 9,
},
labelBgStyle: {
  fill: "#ffffff",
  fillOpacity: 0.9,
},
labelBgPadding: [6, 3],
labelBgBorderRadius: 4,
      }));

    return { nodes, edges };
  }, [graph]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        minHeight: 500,
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{
          padding: 0.2,
        }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        zoomOnScroll
        panOnScroll
        attributionPosition="bottom-right"
      >
        <Background gap={24} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
}