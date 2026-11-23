import { useId, useRef, useState, type KeyboardEvent } from "react";
import { EmptyView } from "../../components/StateViews";
import { RoundsPanel } from "./RoundsPanel";
import { ZonesMap } from "./ZonesMap";
import "./validation.css";

type TabKey = "zonas" | "rondas" | "resultados";

const TABS: ReadonlyArray<{ key: TabKey; label: string }> = [
  { key: "zonas", label: "Zonas" },
  { key: "rondas", label: "Rondas" },
  { key: "resultados", label: "Resultados" },
];

function TabContent({ tab }: { tab: TabKey }) {
  if (tab === "zonas") {
    return <ZonesMap />;
  }
  if (tab === "rondas") {
    return <RoundsPanel />;
  }
  // Las métricas de la ronda cerrada llegan con la tarea 13 del plan del objetivo 4.
  return (
    <EmptyView
      title="Resultados de la ronda"
      detail="Las métricas de una ronda se ven cuando la cierras."
    />
  );
}

/**
 * Comparación con el panel de referencia (objetivo 4, HU-09): zonas del estudio, rondas de
 * evaluación y sus resultados. Pestañas con el patrón de ARIA (flechas, Inicio y Fin).
 */
export function ComparisonPage() {
  const baseId = useId();
  const [selected, setSelected] = useState<TabKey>("zonas");
  const tabRefs = useRef<Partial<Record<TabKey, HTMLButtonElement | null>>>({});

  function select(index: number) {
    const tab = TABS[(index + TABS.length) % TABS.length]!;
    setSelected(tab.key);
    tabRefs.current[tab.key]?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const current = TABS.findIndex((tab) => tab.key === selected);
    const moves: Record<string, number> = {
      ArrowRight: current + 1,
      ArrowLeft: current - 1,
      Home: 0,
      End: TABS.length - 1,
    };
    const next = moves[event.key];
    if (next !== undefined) {
      event.preventDefault();
      select(next);
    }
  }

  return (
    <div className="page">
      <header>
        <h1 className="page__title">Comparación con el panel de referencia</h1>
        <p className="page__subtitle">
          Compara el ranking del motor con el orden que dan los evaluadores, a ciegas, en cada zona
          del estudio.
        </p>
      </header>

      <div className="tabs" role="tablist" aria-label="Secciones de la comparación">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            ref={(element) => {
              tabRefs.current[tab.key] = element;
            }}
            type="button"
            role="tab"
            id={`${baseId}-tab-${tab.key}`}
            aria-controls={`${baseId}-panel-${tab.key}`}
            aria-selected={selected === tab.key}
            tabIndex={selected === tab.key ? 0 : -1}
            className="tabs__tab"
            onClick={() => setSelected(tab.key)}
            onKeyDown={handleKeyDown}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`${baseId}-panel-${selected}`}
        aria-labelledby={`${baseId}-tab-${selected}`}
        tabIndex={0}
      >
        <TabContent tab={selected} />
      </div>
    </div>
  );
}
