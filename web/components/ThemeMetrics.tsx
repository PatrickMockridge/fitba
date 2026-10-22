import { BalancePanel } from "@/components/BalancePanel";
import { DepthChart } from "@/components/DepthChart";
import { FamilyBalanceChart } from "@/components/FamilyBalanceChart";
import { MissionPanel } from "@/components/MissionPanel";
import { ShapeSplitTable } from "@/components/ShapeSplitTable";
import type {
  ThemeBlock,
  ThemeDepthGroup,
  ThemeFamilyGroup,
  ThemeShapeGroup,
} from "@/lib/data";

export function ThemeMetrics({ theme }: { theme: ThemeBlock }) {
  if (theme.theme_id === "family_balance") {
    const metrics = theme.metrics as {
      groups?: ThemeFamilyGroup[];
      squad_provider_rating?: number | null;
    };
    return (
      <FamilyBalanceChart
        groups={metrics.groups ?? []}
        squadRating={metrics.squad_provider_rating ?? null}
      />
    );
  }
  if (theme.theme_id === "wing_back_tax") {
    const metrics = theme.metrics as { groups?: ThemeShapeGroup[] };
    return (
      <ShapeSplitTable
        groups={metrics.groups ?? []}
        players={theme.players}
      />
    );
  }
  if (theme.theme_id === "cover_question") {
    const metrics = theme.metrics as {
      groups?: ThemeDepthGroup[];
      curated_notes?: Array<Record<string, unknown>>;
    };
    return (
      <DepthChart
        groups={metrics.groups ?? []}
        curatedNotes={metrics.curated_notes ?? []}
      />
    );
  }
  if (theme.theme_id === "leaky_boat") {
    return (
      <BalancePanel
        metrics={
          theme.metrics as Parameters<typeof BalancePanel>[0]["metrics"]
        }
      />
    );
  }
  if (theme.theme_id === "mission_check") {
    return (
      <MissionPanel
        metrics={
          theme.metrics as Parameters<typeof MissionPanel>[0]["metrics"]
        }
      />
    );
  }
  return null;
}
