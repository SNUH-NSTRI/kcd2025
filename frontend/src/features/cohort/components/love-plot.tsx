"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BalanceResult } from "@/remote";

interface LovePlotProps {
  balanceResults: BalanceResult[];
}

/**
 * Love Plot - Visualizes Standardized Mean Differences (SMD) for baseline balance
 *
 * Shows SMD for all variables with ±0.1 threshold lines.
 * Variables outside ±0.1 are considered imbalanced.
 */
export function LovePlot({ balanceResults }: LovePlotProps) {
  const continuousResults = useMemo(
    () =>
      balanceResults
        .filter((r) => r.type === "continuous")
        .sort((a, b) => {
          // Sort by absolute SMD descending
          const smdA = "smd" in a ? Math.abs(a.smd) : 0;
          const smdB = "smd" in b ? Math.abs(b.smd) : 0;
          return smdB - smdA;
        }),
    [balanceResults]
  );

  // Calculate max absolute SMD for scaling
  const maxAbsSMD = useMemo(() => {
    const smds = continuousResults
      .filter((r) => "smd" in r)
      .map((r) => Math.abs(r.smd));
    return Math.max(...smds, 0.5); // At least 0.5 for scale
  }, [continuousResults]);

  // Scale factor: convert SMD to percentage width
  const getWidth = (smd: number) => {
    return (Math.abs(smd) / maxAbsSMD) * 100;
  };

  const getColor = (smd: number) => {
    const absSMD = Math.abs(smd);
    if (absSMD < 0.1) return "bg-green-500";
    if (absSMD < 0.2) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getImbalanceLevel = (smd: number) => {
    const absSMD = Math.abs(smd);
    if (absSMD < 0.1) return "Balanced";
    if (absSMD < 0.2) return "Small imbalance";
    if (absSMD < 0.5) return "Moderate imbalance";
    return "Large imbalance";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Love Plot - Baseline Covariate Balance</CardTitle>
        <p className="text-sm text-muted-foreground">
          Standardized Mean Difference (SMD) for continuous variables. |SMD| &gt; 0.1 indicates
          meaningful imbalance between treatment and control groups.
        </p>
      </CardHeader>
      <CardContent>
        {/* Legend */}
        <div className="mb-6 flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-green-500" />
            <span>Balanced (&lt;0.1)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-yellow-500" />
            <span>Small (0.1-0.2)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-red-500" />
            <span>Large (≥0.2)</span>
          </div>
        </div>

        {/* SMD Chart */}
        <div className="space-y-4">
          {continuousResults.map((result) => {
            if (!("smd" in result)) return null;

            const smd = result.smd;
            const absSMD = Math.abs(smd);
            const width = getWidth(smd);
            const color = getColor(smd);
            const level = getImbalanceLevel(smd);

            return (
              <div key={result.variable} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{result.variable}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">{level}</span>
                    <span className="font-mono">SMD: {smd.toFixed(3)}</span>
                  </div>
                </div>

                {/* SMD Bar */}
                <div className="relative h-8 rounded-md bg-muted">
                  {/* Threshold lines */}
                  <div
                    className="absolute top-0 h-full w-px bg-border"
                    style={{ left: "50%" }}
                  />
                  <div
                    className="absolute top-0 h-full w-px bg-yellow-300"
                    style={{ left: `${50 - (0.1 / maxAbsSMD) * 50}%` }}
                  />
                  <div
                    className="absolute top-0 h-full w-px bg-yellow-300"
                    style={{ left: `${50 + (0.1 / maxAbsSMD) * 50}%` }}
                  />

                  {/* SMD Bar */}
                  <div
                    className={`absolute top-1 h-6 rounded transition-all ${color}`}
                    style={{
                      left: smd < 0 ? `${50 - width / 2}%` : "50%",
                      width: `${width / 2}%`,
                    }}
                  />
                </div>

                {/* Scale labels */}
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>−{maxAbsSMD.toFixed(1)}</span>
                  <span>0</span>
                  <span>+{maxAbsSMD.toFixed(1)}</span>
                </div>
              </div>
            );
          })}
        </div>

        {continuousResults.length === 0 && (
          <p className="text-center text-muted-foreground">
            No continuous variables to display
          </p>
        )}
      </CardContent>
    </Card>
  );
}
