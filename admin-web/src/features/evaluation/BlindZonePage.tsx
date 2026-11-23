import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useId, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { AuthImage } from "../../components/AuthImage";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import {
  photoPath,
  useCurrentRound,
  useSubmitOrder,
  useZoneCards,
  type BlindCard,
  type CurrentRound,
  type ZoneCards,
} from "./api";
import { BlindMap } from "./BlindMap";
import { cardLabel, serviceLabel } from "./labels";
import type { SubmittedState } from "./MyEvaluationsPage";
import { SortableCard } from "./SortableCard";
import { useDraftOrder } from "./useDraftOrder";
import "./evaluation.css";

const HOME = "/evaluacion";
const LOAD_PROBLEM = "No pudimos cargar la zona. Inténtalo de nuevo.";
const ALREADY_SENT = "Ya enviaste esta zona.";
const SUBMIT_PROBLEM = "No pudimos enviar el orden. Inténtalo de nuevo; tu orden sigue aquí.";

function submitProblem(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return SUBMIT_PROBLEM;
  }
  if (error.code === "EVALUATION_ORDER_ALREADY_SUBMITTED") {
    return ALREADY_SENT;
  }
  return error.code === "NETWORK_ERROR" || error.status === 422 ? error.message : SUBMIT_PROBLEM;
}

function positionSentence(label: string, position: number, total: number): string {
  return `${label}, ahora en la posición ${position} de ${total}`;
}

function MapPanel({ card, onClose }: { card: BlindCard; onClose: () => void }) {
  const titleId = useId();
  const label = cardLabel(card);
  return (
    <aside className="card blind-panel" aria-labelledby={titleId}>
      <div className="card__header">
        <h2 className="card__title" id={titleId}>
          {label}
        </h2>
        <button type="button" className="button button--secondary" onClick={onClose}>
          Cerrar el mapa
        </button>
      </div>
      <AuthImage
        src={photoPath(card.report_id, "full")}
        alt={`Foto ampliada del daño en ${label}`}
        className="blind-panel__photo"
      />
      <BlindMap card={card} />
      <div className="blind-panel__services">
        <p className="blind-panel__services-title">Servicios críticos cercanos (menos de 500 m)</p>
        {card.nearby_services.length > 0 ? (
          <ul>
            {card.nearby_services.map((service) => (
              <li key={`${service.location.latitude}:${service.location.longitude}`}>
                {serviceLabel(service)}
              </li>
            ))}
          </ul>
        ) : (
          <p>Ninguno a menos de 500 m.</p>
        )}
      </div>
    </aside>
  );
}

function ZoneOrdering({ round, data }: { round: CurrentRound["round"]; data: ZoneCards }) {
  const navigate = useNavigate();
  const confirmTitleId = useId();
  const initialIds = useMemo(() => data.cards.map((card) => card.report_id), [data]);
  const cards = useMemo(
    () => new Map(data.cards.map((card) => [card.report_id, card] as const)),
    [data],
  );
  const draft = useDraftOrder(round.id, data.zone.id, initialIds);
  const [announcement, setAnnouncement] = useState("");
  const [mapCardId, setMapCardId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const submit = useSubmitOrder(data.zone.id);
  const total = draft.ids.length;

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const labelOf = (id: string | number) => {
    const card = cards.get(String(id));
    return card ? cardLabel(card) : "Reporte";
  };
  const positionOf = (id: string | number) => draft.ids.indexOf(String(id)) + 1;
  const announcements: Announcements = {
    onDragStart: ({ active }) =>
      `Tomaste ${labelOf(active.id)}, en la posición ${positionOf(active.id)} de ${total}.`,
    onDragOver: ({ active, over }) =>
      over ? `${labelOf(active.id)} sobre la posición ${positionOf(over.id)} de ${total}.` : "",
    onDragEnd: ({ active, over }) =>
      over
        ? `Soltaste ${labelOf(active.id)} en la posición ${positionOf(over.id)} de ${total}.`
        : "",
    onDragCancel: ({ active }) => `Cancelaste el arrastre de ${labelOf(active.id)}.`,
  };

  function moveAndAnnounce(id: string, offset: number) {
    const from = draft.ids.indexOf(id);
    const to = from + offset;
    if (from === -1 || to < 0 || to >= total) {
      return;
    }
    draft.move(from, to);
    setAnnouncement(positionSentence(labelOf(id), to + 1, total));
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) {
      return;
    }
    const to = draft.ids.indexOf(String(over.id));
    draft.move(draft.ids.indexOf(String(active.id)), to);
    setAnnouncement(positionSentence(labelOf(active.id), to + 1, total));
  }

  function send() {
    if (submit.isPending) {
      return;
    }
    submit.mutate(draft.ids, {
      onSuccess: () => {
        draft.reset();
        navigate(HOME, { state: { submittedZone: data.zone.name } satisfies SubmittedState });
      },
    });
  }

  const mapCard = mapCardId === null ? undefined : cards.get(mapCardId);

  return (
    <div className="blind-layout">
      <div className="blind-main">
        <p className="blind-help">
          Ordena del más urgente (1) al menos urgente. Arrastra las tarjetas o usa los botones subir
          y bajar. Tu orden se guarda en este navegador hasta que lo envíes.
        </p>
        <p className="visually-hidden" role="status" aria-label="Cambios en el orden">
          {announcement}
        </p>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
          accessibility={{
            announcements,
            screenReaderInstructions: {
              draggable:
                "Para mover una tarjeta, pulsa espacio o Enter, muévela con las flechas y vuelve a pulsar espacio o Enter para soltarla. Escape cancela.",
            },
          }}
        >
          <SortableContext items={draft.ids} strategy={verticalListSortingStrategy}>
            <ol
              className="blind-list"
              aria-label="Reportes de la zona, del más urgente al menos urgente"
            >
              {draft.ids.map((id, index) => {
                const card = cards.get(id)!;
                return (
                  <SortableCard
                    key={id}
                    card={card}
                    position={index + 1}
                    total={total}
                    onMoveUp={() => moveAndAnnounce(id, -1)}
                    onMoveDown={() => moveAndAnnounce(id, 1)}
                    onShowMap={() => setMapCardId(id)}
                  />
                );
              })}
            </ol>
          </SortableContext>
        </DndContext>

        <div className="blind-submit">
          {confirming ? (
            <div className="close-confirm" role="group" aria-labelledby={confirmTitleId}>
              <p id={confirmTitleId} className="close-confirm__title">
                Confirmar el envío
              </p>
              <p>No podrás cambiarlo: se enviará el orden tal como lo ves.</p>
              {submit.isError ? (
                <div className="alert" role="alert">
                  <span className="alert__icon" aria-hidden="true">
                    !
                  </span>
                  <p>{submitProblem(submit.error)}</p>
                </div>
              ) : null}
              <div className="close-confirm__actions">
                <button type="button" className="button" disabled={submit.isPending} onClick={send}>
                  {submit.isPending ? "Enviando…" : "Sí, enviar"}
                </button>
                <button
                  type="button"
                  className="button button--secondary"
                  disabled={submit.isPending}
                  onClick={() => {
                    submit.reset();
                    setConfirming(false);
                  }}
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <button type="button" className="button" onClick={() => setConfirming(true)}>
              Enviar este orden
            </button>
          )}
        </div>
      </div>
      {mapCard ? <MapPanel card={mapCard} onClose={() => setMapCardId(null)} /> : null}
    </div>
  );
}

/** Vista a ciegas de una zona (objetivo 4): el evaluador ordena sin ver datos del motor. */
export function BlindZonePage() {
  const zoneId = Number(useParams().zoneId);
  const current = useCurrentRound();
  const zone = useZoneCards(zoneId);

  let title = "Ordenar la zona";
  let subtitle: string | null = null;
  let body;
  if (current.isPending || zone.isPending) {
    body = <LoadingView label="Cargando la zona…" />;
  } else if (current.isError || zone.isError) {
    const error = current.error ?? zone.error;
    body = (
      <ErrorView
        message={
          error instanceof ApiError && error.code === "NETWORK_ERROR" ? error.message : LOAD_PROBLEM
        }
        onRetry={() => {
          void current.refetch();
          void zone.refetch();
        }}
      />
    );
  } else if (current.data === null) {
    body = <EmptyView title="No hay una ronda de evaluación abierta" />;
  } else {
    title = `Zona ${zone.data.zone.name}`;
    subtitle = `Ronda «${current.data.round.name}» · ${zone.data.zone.n_reports} reportes`;
    body = zone.data.submitted ? (
      <EmptyView title="Ya enviaste el orden de esta zona." detail="Puedes seguir con las demás." />
    ) : (
      <ZoneOrdering round={current.data.round} data={zone.data} />
    );
  }

  return (
    <div className="page">
      <header>
        <Link to={HOME} className="blind-back">
          ← Mis evaluaciones
        </Link>
        <h1 className="page__title">{title}</h1>
        {subtitle ? <p className="page__subtitle">{subtitle}</p> : null}
      </header>
      {body}
    </div>
  );
}
