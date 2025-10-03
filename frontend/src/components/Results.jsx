import React from "react";

export function Results({ results, onJump }) {
  if (!results || results.length === 0) {
    return <div className="text-gray-400">No results yet.</div>;
  }

  return (
    <div className="space-y-3">
      {results.map((r, i) => (
        <div
          key={i}
          className="border-b border-gray-700 pb-2 flex justify-between items-center"
        >
          <div>
            <p className="text-sm text-gray-300">{r.snippet}</p>
            <p className="text-xs text-gray-500">
              Score: {r.score?.toFixed(3)} | {Math.floor(r.t_start)}s -{" "}
              {Math.floor(r.t_end)}s
            </p>
          </div>
          <button
            onClick={() => onJump(r.t_start)}
            className="ml-4 bg-blue-600 px-3 py-1 rounded hover:bg-blue-500 text-sm"
          >
            Jump
          </button>
        </div>
      ))}
    </div>
  );
}

